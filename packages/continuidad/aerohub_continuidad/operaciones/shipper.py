"""*Shipper* de continuidad (Sprint S1.9, ADR-018 C3).

Drena `continuidad.journal_mutacion` del primario y replica cada entrada
sobre el standby. `payload` del journal es ABREVIADO (research.md
Decision 9 de specs/011-continuidad-rto-rpo/: hallazgo empirico -- ningun
modulo de negocio, desde S1.1, escribe la fila completa ahi, solo un
subconjunto para trazabilidad forense) -- por eso el *shipper* NUNCA
construye el `INSERT`/`UPDATE` desde `payload`. En su lugar, usa
`clave_primaria` para re-consultar la fila COMPLETA en el PRIMARIO y la
aplica como *UPSERT* generico sobre el standby -- idempotente por
construccion, sin importar cuantas veces se reprocese la misma entrada.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from aerohub_kernel import ahora_utc, generar_id
from aerohub_repository import alcance_global, sesion
from sqlalchemy import insert, select, update

from ..domain.identificador_sql import validar_identificador
from ..domain.replicacion import debe_procesar
from .conexiones import conexion_pymonetdb
from .config import conexion_primario, conexion_standby, nombre_standby
from .tablas import journal_mutacion, shipper_checkpoint

_MOTIVO_ALCANCE_GLOBAL = "shipper_continuidad"
_ROL = "role_platform_admin"

_OPERACIONES_REPLICABLES = frozenset({"INSERT", "UPDATE", "DELETE_LOGICO"})


def _como_dict(valor: dict | str) -> dict:
    """El dialecto `sqlalchemy-monetdb` ya deserializa columnas JSON a
    dict/list de Python (hallazgo empirico de S1.9) -- pero se maneja
    tambien el caso `str` de forma defensiva, sin asumir un unico
    comportamiento del driver."""
    return valor if isinstance(valor, dict) else json.loads(valor)


@dataclass(frozen=True, slots=True)
class ResultadoShipper:
    aplicadas: int
    ultimo_lsn_aplicado: int


def _obtener_checkpoint(conn) -> int:  # noqa: ANN001 -- Connection de aerohub_repository
    fila = conn.execute(
        select(shipper_checkpoint.c.ultimo_lsn_aplicado).where(
            shipper_checkpoint.c.standby_nombre == nombre_standby()
        )
    ).first()
    return fila.ultimo_lsn_aplicado if fila is not None else 0


def _actualizar_checkpoint(conn, *, ultimo_lsn: int) -> None:  # noqa: ANN001
    """No se journaliza (escribir_journal) -- shipper_checkpoint es
    metainformacion del propio mecanismo de continuidad, no una tabla de
    negocio replicable; journalizarla crearia una entrada que el shipper
    luego intentaria re-aplicarse a si mismo."""
    existe = conn.execute(
        select(shipper_checkpoint.c.id).where(
            shipper_checkpoint.c.standby_nombre == nombre_standby()
        )
    ).first()
    ahora = ahora_utc()
    if existe is None:
        conn.execute(
            insert(shipper_checkpoint).values(
                id=generar_id(),
                standby_nombre=nombre_standby(),
                ultimo_lsn_aplicado=ultimo_lsn,
                actualizado_en=ahora,
            )
        )
    else:
        conn.execute(
            update(shipper_checkpoint)
            .where(shipper_checkpoint.c.standby_nombre == nombre_standby())
            .values(ultimo_lsn_aplicado=ultimo_lsn, actualizado_en=ahora)
        )


def _fila_actual(  # noqa: ANN001
    conn_primario, *, esquema: str, tabla: str, clave_primaria: dict
) -> tuple[list[str], tuple] | None:
    # Ningun driver de MonetDB permite parametrizar un nombre de tabla/columna
    # -- validar_identificador() es la unica defensa posible antes de
    # interpolar (domain/identificador_sql.py, defensa en profundidad).
    esquema, tabla = validar_identificador(esquema), validar_identificador(tabla)
    columnas_pk = [validar_identificador(c) for c in clave_primaria]

    cur = conn_primario.cursor()
    where_clause = " AND ".join(f'"{c}" = %s' for c in columnas_pk)
    cur.execute(
        f'SELECT * FROM "{esquema}"."{tabla}" WHERE {where_clause}',  # nosec B608
        list(clave_primaria.values()),
    )
    fila = cur.fetchone()
    if fila is None:
        return None
    columnas = [d[0] for d in cur.description]
    return columnas, fila


def _aplicar_upsert(  # noqa: ANN001
    conn_standby,
    *,
    esquema: str,
    tabla: str,
    columnas: list[str],
    fila: tuple,
    clave_primaria: dict,
) -> None:
    # Defensa en profundidad (ver _fila_actual): ningun nombre de
    # esquema/tabla/columna se interpola sin validar primero.
    esquema, tabla = validar_identificador(esquema), validar_identificador(tabla)
    columnas = [validar_identificador(c) for c in columnas]

    valores = dict(zip(columnas, fila, strict=True))
    columnas_pk = [validar_identificador(c) for c in clave_primaria]
    columnas_no_pk = [c for c in columnas if c not in columnas_pk]

    cur = conn_standby.cursor()
    filas_afectadas = 0
    if columnas_no_pk:
        set_clause = ", ".join(f'"{c}" = %s' for c in columnas_no_pk)
        where_clause = " AND ".join(f'"{c}" = %s' for c in columnas_pk)
        valores_set = [valores[c] for c in columnas_no_pk]
        valores_where = [valores[c] for c in columnas_pk]
        cur.execute(
            f'UPDATE "{esquema}"."{tabla}" SET {set_clause} WHERE {where_clause}',  # nosec B608
            valores_set + valores_where,
        )
        filas_afectadas = cur.rowcount

    if filas_afectadas in (0, -1):
        # -1: algunos drivers no reportan rowcount de forma fiable en UPDATE
        # -- se verifica con un SELECT antes de decidir insertar, en vez de
        # asumir que 0 siempre significa "no existe".
        where_clause = " AND ".join(f'"{c}" = %s' for c in columnas_pk)
        cur.execute(
            f'SELECT 1 FROM "{esquema}"."{tabla}" WHERE {where_clause}',  # nosec B608
            [valores[c] for c in columnas_pk],
        )
        if cur.fetchone() is not None:
            return  # ya existe y ya se actualizo arriba
        columnas_str = ", ".join(f'"{c}"' for c in columnas)
        placeholders = ", ".join(["%s"] * len(columnas))
        cur.execute(
            f'INSERT INTO "{esquema}"."{tabla}" ({columnas_str}) VALUES ({placeholders})',  # nosec B608
            [valores[c] for c in columnas],
        )


def ejecutar_ciclo_shipper() -> ResultadoShipper:
    with alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL), sesion() as conn_lectura:
        ultimo_lsn_aplicado = _obtener_checkpoint(conn_lectura)
        entradas = list(
            conn_lectura.execute(
                select(journal_mutacion)
                .where(journal_mutacion.c.lsn > ultimo_lsn_aplicado)
                .order_by(journal_mutacion.c.lsn)
            )
        )

    entradas = [e for e in entradas if debe_procesar(e.lsn, ultimo_lsn_aplicado)]
    if not entradas:
        return ResultadoShipper(aplicadas=0, ultimo_lsn_aplicado=ultimo_lsn_aplicado)

    aplicadas = 0
    with (
        conexion_pymonetdb(conexion_primario()) as conn_primario,
        conexion_pymonetdb(conexion_standby()) as conn_standby,
    ):
        for entrada in entradas:
            if entrada.operacion not in _OPERACIONES_REPLICABLES:
                # 'DDL': se aplica por el pipeline de migraciones
                # versionado (FR-017), nunca por el shipper.
                ultimo_lsn_aplicado = entrada.lsn
                continue

            clave_primaria = _como_dict(entrada.clave_primaria)
            resultado_fila = _fila_actual(
                conn_primario,
                esquema=entrada.esquema,
                tabla=entrada.tabla,
                clave_primaria=clave_primaria,
            )
            if resultado_fila is not None:
                columnas, fila = resultado_fila
                _aplicar_upsert(
                    conn_standby,
                    esquema=entrada.esquema,
                    tabla=entrada.tabla,
                    columnas=columnas,
                    fila=fila,
                    clave_primaria=clave_primaria,
                )
                conn_standby.commit()
            aplicadas += 1
            ultimo_lsn_aplicado = entrada.lsn

    with alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL), sesion() as conn_escritura:
        _actualizar_checkpoint(conn_escritura, ultimo_lsn=ultimo_lsn_aplicado)

    return ResultadoShipper(aplicadas=aplicadas, ultimo_lsn_aplicado=ultimo_lsn_aplicado)


def obtener_atraso_segundos() -> float:
    """Atraso actual (contracts/shipper-metrica.md): diferencia entre
    `ahora` y `ocurrido_en` de la entrada mas antigua aun NO aplicada. `0`
    si no hay entradas pendientes."""
    with alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL), sesion() as conn:
        ultimo_lsn_aplicado = _obtener_checkpoint(conn)
        pendiente = conn.execute(
            select(journal_mutacion.c.ocurrido_en)
            .where(journal_mutacion.c.lsn > ultimo_lsn_aplicado)
            .order_by(journal_mutacion.c.lsn)
            .limit(1)
        ).first()
    if pendiente is None:
        return 0.0
    return max(0.0, (ahora_utc() - pendiente.ocurrido_en).total_seconds())


def obtener_ultimo_lsn_aplicado() -> int:
    with alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL), sesion() as conn:
        return _obtener_checkpoint(conn)
