"""Guardian de tenant fail-closed (ADR-019, componentes G1 y G2).

G1 -- registro declarativo de alcance por tabla ('tenant' / 'global' /
'interno'). Toda tabla debe declararse antes de usarse; sin declaracion, se
lanza AlcanceNoDeclarado en vez de asumir un valor por defecto permisivo.

G2 -- verificacion en antes-de-ejecutar (`packages/repository/base.py`
registra `verificar_sentencia` en el evento `before_execute` del motor,
S0.2). Recorre el ARBOL de la sentencia SQLAlchemy Core -- nunca el texto
SQL compilado -- por lo que un comentario, un alias o una concatenacion no
lo engana. Si alguna tabla involucrada tiene alcance 'tenant' y la sentencia
no trae un predicado de igualdad vinculado al `tenant_id` del contexto de la
peticion, la sentencia se ABORTA antes de llegar al motor.

No sustituye a PN-15 (analisis estatico de que ningun modulo fuera de este
paquete emita SQL): ese es un control de tiempo de build sobre TEXTO fuente.
Este guardian es un control de tiempo de ejecucion sobre la SENTENCIA ya
construida. Ambos son necesarios; por eso una `TextClause` (SQL crudo) se
rechaza aqui tambien, sin excepcion -- este guardian no puede verificar el
alcance de tenant de un texto opaco, y el diseno es fail-closed ante lo que
no puede verificar, no fail-open.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import Delete, Insert, Select, Update
from sqlalchemy.sql.elements import BinaryExpression, BindParameter, ColumnClause, TextClause
from sqlalchemy.sql.operators import eq
from sqlalchemy.sql.schema import Table as SATable
from sqlalchemy.sql.selectable import Join

from .contexto import alcance_global_activo, contexto_tenant_id

# clauseelement/multiparams/params provienen del evento before_execute de
# SQLAlchemy, cuya propia firma publica no los tipa mas alla de Any -- este
# modulo narrowea con isinstance() en tiempo de ejecucion (ver _tablas_de,
# _tabla_dml_o_none), no con anotaciones que fingirian una precision que la
# libreria misma no ofrece.

Alcance = Literal["tenant", "global", "interno"]

_SIN_VALOR = object()


@dataclass(frozen=True, slots=True)
class RegistroAlcance:
    esquema: str
    tabla: str
    alcance: Alcance
    columna_tenant: str = "tenant_id"


class AlcanceNoDeclarado(Exception):
    """G1: se uso una tabla en una sentencia sin haber declarado su alcance
    via registrar_alcance(). El build (o, en runtime, la propia consulta)
    debe fallar -- nunca se asume un alcance por defecto.
    """


class TenantScopeViolation(Exception):
    """G2: sentencia sobre tabla de alcance 'tenant' sin predicado de
    igualdad valido sobre tenant_id, vinculado al contexto de la peticion.
    Se registra como incidente en compliance.log_auditoria por quien la
    captura (packages/repository/base.py), no por esta funcion.
    """


_registro: dict[tuple[str, str], RegistroAlcance] = {}


def registrar_alcance(
    esquema: str, tabla: str, alcance: Alcance, *, columna_tenant: str = "tenant_id"
) -> None:
    _registro[(esquema, tabla)] = RegistroAlcance(esquema, tabla, alcance, columna_tenant)


def alcance_de(esquema: str, tabla: str) -> RegistroAlcance:
    clave = (esquema, tabla)
    if clave not in _registro:
        raise AlcanceNoDeclarado(
            f"{esquema}.{tabla} no declaro su alcance via registrar_alcance() "
            "antes de usarse en una consulta (ADR-019 G1)."
        )
    return _registro[clave]


def tablas_registradas() -> tuple[RegistroAlcance, ...]:
    """Usado por el test de conformidad G1: toda tabla con alcance='tenant'
    debe tener `columna_tenant` como columna NOT NULL en el motor real.
    """
    return tuple(_registro.values())


def _tablas_en(from_obj: Any) -> list[SATable]:
    if isinstance(from_obj, SATable):
        return [from_obj]
    if isinstance(from_obj, Join):
        return _tablas_en(from_obj.left) + _tablas_en(from_obj.right)
    return []  # subqueries/CTE: fuera de alcance de S0.2 (ver riesgo R-11 del Plan)


def _tabla_dml_o_none(clauseelement: Insert | Update | Delete) -> SATable | None:
    """Insert/Update/Delete.table esta tipado por SQLAlchemy como
    TableClause | Alias | Join (para soportar destinos exoticos que este
    proyecto no usa); todo el codigo aguas abajo necesita un Table real
    (con .schema). None si algun dia aparece un DML contra un Join/Alias --
    entonces no hay tabla que registrar en G1 y la sentencia se trata como
    sin tablas de alcance tenant (fail-closed la alcanza igual si de verdad
    tocaba una tabla tenant, vía el resto de la logica de verificar_sentencia).
    """
    tabla = clauseelement.table
    return tabla if isinstance(tabla, SATable) else None


def _tablas_de(clauseelement: Any) -> list[SATable]:
    if isinstance(clauseelement, Insert | Update | Delete):
        tabla = _tabla_dml_o_none(clauseelement)
        return [tabla] if tabla is not None else []
    if isinstance(clauseelement, Select):
        tablas: list[SATable] = []
        for from_ in clauseelement.get_final_froms():
            tablas.extend(_tablas_en(from_))
        return tablas
    return []


def _valor_bind(nodo: BindParameter, params: dict[str, Any], multiparams: Any) -> Any:
    if nodo.value is not None:
        return nodo.value
    if nodo.key in params:
        return params[nodo.key]
    for fila in multiparams or ():
        if isinstance(fila, dict) and nodo.key in fila:
            return fila[nodo.key]
    return _SIN_VALOR


def _valores_insert(clause: Insert, multiparams: Any, params: dict[str, Any]) -> list[dict]:
    if params:
        return [dict(params)]
    if multiparams:
        filas = list(multiparams)
        if filas and isinstance(filas[0], dict):
            return list(filas)
    try:
        compiled_params = clause.compile().params
    except Exception:
        return []
    if any(v is not None for v in compiled_params.values()):
        return [compiled_params]
    return []


def _tiene_filtro_tenant(
    whereclause: Any,
    tabla: SATable,
    columna_tenant: str,
    tenant_id_esperado: int,
    params: dict[str, Any],
    multiparams: Any,
) -> bool:
    if whereclause is None:
        return False

    encontrados: list[Any] = []

    def _es_columna_tenant_de_la_tabla(nodo: Any) -> bool:
        return (
            isinstance(nodo, ColumnClause)
            and nodo.name == columna_tenant
            and getattr(nodo, "table", None) is tabla
        )

    def _recorrer(nodo: Any) -> None:
        if isinstance(nodo, BinaryExpression) and nodo.operator is eq:
            izq, der = nodo.left, nodo.right
            if _es_columna_tenant_de_la_tabla(izq) and isinstance(der, BindParameter):
                encontrados.append(_valor_bind(der, params, multiparams))
            elif _es_columna_tenant_de_la_tabla(der) and isinstance(izq, BindParameter):
                encontrados.append(_valor_bind(izq, params, multiparams))
        for hijo in nodo.get_children():
            _recorrer(hijo)

    _recorrer(whereclause)
    return any(v == tenant_id_esperado for v in encontrados if v is not _SIN_VALOR)


def _alcance_de_tabla(tabla: SATable) -> RegistroAlcance:
    if tabla.schema is None:
        raise AlcanceNoDeclarado(
            f"Tabla '{tabla.name}' sin esquema explicito -- toda tabla de este "
            "proyecto se declara con schema=... (ADR-019 G1)."
        )
    return alcance_de(tabla.schema, tabla.name)


def verificar_sentencia(clauseelement: Any, multiparams: Any, params: dict[str, Any]) -> None:
    """Registrado por base.py en el evento `before_execute` del engine."""
    if alcance_global_activo() is not None:
        return  # G3: excepcion nominal, ya auditada por separado (contexto.py)

    if isinstance(clauseelement, TextClause):
        # SQL crudo: este guardian no puede verificar su alcance de tenant.
        # Fail-closed -- ver docstring del modulo.
        raise TenantScopeViolation(
            "SQL de texto crudo (TextClause) rechazado por el guardian: no "
            "verificable. Usar construcciones de SQLAlchemy Core (P1)."
        )

    tablas = _tablas_de(clauseelement)
    tablas_tenant = [t for t in tablas if _alcance_de_tabla(t).alcance == "tenant"]
    if not tablas_tenant:
        return

    tenant_id_esperado = contexto_tenant_id()

    if isinstance(clauseelement, Insert):
        tabla = _tabla_dml_o_none(clauseelement)
        if tabla is None:
            raise TenantScopeViolation(
                "INSERT sin tabla resoluble (Join/Alias como destino) sobre una "
                "sentencia que involucra tabla(s) de alcance tenant; rechazada (fail-closed)."
            )
        columna_tenant = _alcance_de_tabla(tabla).columna_tenant
        filas = _valores_insert(clauseelement, multiparams, params)
        if not filas or not all(fila.get(columna_tenant) == tenant_id_esperado for fila in filas):
            raise TenantScopeViolation(
                f"INSERT sobre {tabla.schema}.{tabla.name} sin "
                f"{columna_tenant} == tenant_id del contexto ({tenant_id_esperado})."
            )
        return

    if isinstance(clauseelement, Update | Delete):
        tabla = _tabla_dml_o_none(clauseelement)
        if tabla is None:
            raise TenantScopeViolation(
                f"{type(clauseelement).__name__} sin tabla resoluble (Join/Alias como "
                "destino) sobre una sentencia que involucra tabla(s) de alcance tenant; "
                "rechazada (fail-closed)."
            )
        columna_tenant = _alcance_de_tabla(tabla).columna_tenant
        if not _tiene_filtro_tenant(
            clauseelement.whereclause,
            tabla,
            columna_tenant,
            tenant_id_esperado,
            params,
            multiparams,
        ):
            raise TenantScopeViolation(
                f"{type(clauseelement).__name__} sobre {tabla.schema}.{tabla.name} sin "
                f"filtro WHERE {columna_tenant} == tenant_id del contexto."
            )
        return

    if isinstance(clauseelement, Select):
        for tabla in tablas_tenant:
            columna_tenant = _alcance_de_tabla(tabla).columna_tenant
            if not _tiene_filtro_tenant(
                clauseelement.whereclause,
                tabla,
                columna_tenant,
                tenant_id_esperado,
                params,
                multiparams,
            ):
                raise TenantScopeViolation(
                    f"SELECT sobre {tabla.schema}.{tabla.name} sin filtro WHERE "
                    f"{columna_tenant} == tenant_id del contexto."
                )
        return

    raise TenantScopeViolation(
        f"Sentencia de tipo {type(clauseelement).__name__} no reconocida por el "
        "guardian sobre tabla(s) de alcance tenant; rechazada por diseno (fail-closed)."
    )
