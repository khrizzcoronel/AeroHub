"""Prueba de restauracion semanal automatizada (Sprint S1.9, ADR-018 C4,
RF-O09). Restaura el ultimo snapshot verificado de tipo 'volcado_diario'
sobre `monetdb-restore-test` (research.md Decision 10 de
specs/011-continuidad-rto-rpo/: el unico formato restaurable por SQL/Python
puro, sin acceso al control del proceso mserver5) y mide RTO/RPO reales.
"""

from __future__ import annotations

import json
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path

from aerohub_kernel import ahora_utc, generar_id
from aerohub_repository import alcance_global, sesion
from sqlalchemy import insert, select

from ..domain.identificador_sql import validar_identificador
from ..domain.recuperacion import calcular_rpo_observado_segundos, calcular_rto_observado_segundos
from .conexiones import cliente_minio, conexion_pymonetdb
from .config import conexion_restore_test, minio_bucket
from .snapshot import obtener_ultimo_snapshot_verificado_de_tipo
from .tablas import prueba_restauracion

_MOTIVO_ALCANCE_GLOBAL = "prueba_restauracion_continuidad"
_ROL = "role_platform_admin"


@dataclass(frozen=True, slots=True)
class ResultadoPruebaRestauracion:
    resultado: str
    rto_observado_segundos: int | None
    rpo_observado_segundos: int | None
    detalle: str | None


class SinSnapshotParaRestaurar(Exception):
    """No hay ningun snapshot 'volcado_diario' verificado todavia --
    `prueba_restauracion.snapshot_id` es NOT NULL (FK real), asi que no
    corresponde insertar una fila de intento sin un snapshot que referenciar;
    el ciclo llamador se limita a registrar esta excepcion en su log."""


def _orden_topologico_tablas(conn) -> list[tuple[str, str]]:  # noqa: ANN001
    """Orden de insercion seguro (padres antes que hijos) derivado del
    grafo REAL de claves foraneas del motor (`sys.keys`) -- necesario
    porque el volcado logico agrupa archivos por nombre de esquema.tabla
    en orden alfabetico, que NO respeta dependencias entre esquemas (p.
    ej. `billing.cargo_aeronautico` depende de `tenants.tenant`, pero
    'billing' es alfabeticamente anterior a 'tenants')."""
    cur = conn.cursor()
    cur.execute(
        "SELECT s.name, t.name, t.id FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.id "
        "WHERE t.system = FALSE AND t.type = 0"
    )
    tablas_por_id: dict[int, tuple[str, str]] = {
        tid: (esquema, tabla) for esquema, tabla, tid in cur.fetchall()
    }

    cur.execute(
        "SELECT k.table_id, pk.table_id FROM sys.keys k "
        "JOIN sys.keys pk ON k.rkey = pk.id WHERE k.type = 2"
    )
    dependencias: dict[int, set[int]] = {tid: set() for tid in tablas_por_id}
    for hijo_id, padre_id in cur.fetchall():
        if hijo_id in dependencias and padre_id in dependencias and hijo_id != padre_id:
            dependencias[hijo_id].add(padre_id)

    orden: list[int] = []
    resueltos: set[int] = set()
    pendientes = set(tablas_por_id)
    while pendientes:
        listos = {tid for tid in pendientes if dependencias[tid] <= resueltos}
        if not listos:
            # Ciclo o dependencia no resuelta (no deberia ocurrir en este
            # esquema) -- se agregan el resto en cualquier orden en vez de
            # colgar indefinidamente (fail-soft, no fail-closed: esto es
            # una prueba de restauracion, no una escritura de negocio).
            listos = pendientes
        orden.extend(sorted(listos))
        resueltos |= listos
        pendientes -= listos

    return [tablas_por_id[tid] for tid in orden]


def _valor_para_bind(valor):  # noqa: ANN001, ANN202
    """`pymonetdb` deserializa columnas JSON a `dict`/`list` al LEER
    (mismo hallazgo que en `shipper.py`), pero no las vuelve a serializar
    al ESCRIBIR -- un `dict`/`list` crudo como parametro de `INSERT` falla
    con `ProgrammingError: type <class 'dict'> not supported as value`.
    Se re-serializa aqui antes de enlazarlo."""
    return json.dumps(valor) if isinstance(valor, (dict, list)) else valor


def _columnas_pk(conn, *, esquema: str, tabla: str) -> list[str]:  # noqa: ANN001
    """Nombres de columna de la PRIMARY KEY real de la tabla (soporta
    claves compuestas, p. ej. `support.articulo_kb_etiqueta`) -- una
    idempotencia basada solo en una columna `id` fallaria (PK violation)
    en cualquier tabla de asociacion sin columna `id` propia."""
    cur = conn.cursor()
    cur.execute(
        "SELECT o.name FROM sys.keys k "
        "JOIN sys.objects o ON o.id = k.id "
        "JOIN sys.tables t ON t.id = k.table_id "
        "JOIN sys.schemas s ON s.id = t.schema_id "
        "WHERE s.name = %s AND t.name = %s AND k.type = 0 "
        "ORDER BY o.nr",
        (esquema, tabla),
    )
    return [fila[0] for fila in cur.fetchall()]


def _restaurar_tabla(conn_restore_test, *, esquema: str, tabla: str, ruta_jsonl: Path) -> None:  # noqa: ANN001
    with open(ruta_jsonl, encoding="utf-8") as f:
        lineas = [json.loads(linea) for linea in f if linea.strip()]
    if not lineas:
        return

    # Defensa en profundidad (domain/identificador_sql.py) -- ningun driver
    # de MonetDB parametriza nombres de tabla/columna.
    esquema, tabla = validar_identificador(esquema), validar_identificador(tabla)
    cur = conn_restore_test.cursor()
    columnas = [validar_identificador(c) for c in lineas[0]]
    columnas_str = ", ".join(f'"{c}"' for c in columnas)
    columnas_pk_tabla = _columnas_pk(conn_restore_test, esquema=esquema, tabla=tabla)
    columnas_pk = [validar_identificador(c) for c in columnas_pk_tabla if c in columnas]
    where_pk = " AND ".join(f'"{c}" = %s' for c in columnas_pk) if columnas_pk else None

    for fila in lineas:
        valores = [_valor_para_bind(fila[c]) for c in columnas]
        if where_pk is not None:
            cur.execute(
                f'SELECT 1 FROM "{esquema}"."{tabla}" WHERE {where_pk}',  # nosec B608
                [_valor_para_bind(fila[c]) for c in columnas_pk],
            )
            if cur.fetchone() is not None:
                continue  # ya restaurada en una corrida anterior de la prueba -- idempotente
        placeholders = ", ".join(["%s"] * len(columnas))
        cur.execute(
            f'INSERT INTO "{esquema}"."{tabla}" ({columnas_str}) '  # nosec B608
            f"VALUES ({placeholders})",
            valores,
        )


def ejecutar_prueba_restauracion() -> ResultadoPruebaRestauracion:
    inicio = ahora_utc()
    snapshot = obtener_ultimo_snapshot_verificado_de_tipo("volcado_diario")
    if snapshot is None:
        raise SinSnapshotParaRestaurar(
            "no hay snapshot verificado de tipo 'volcado_diario' para restaurar"
        )

    cliente = cliente_minio()
    with tempfile.TemporaryDirectory() as directorio_temporal:
        ruta_local = Path(directorio_temporal) / "snapshot.tar"
        cliente.download_file(minio_bucket(), snapshot["ruta_artefacto"], str(ruta_local))

        with conexion_pymonetdb(conexion_restore_test()) as conn:
            with tarfile.open(ruta_local, "r") as tar:
                # nosec B202 -- artefacto propio, generado por este mismo sistema
                tar.extractall(directorio_temporal, filter="data")

            for esquema, tabla in _orden_topologico_tablas(conn):
                ruta_jsonl = Path(directorio_temporal) / f"{esquema}.{tabla}.jsonl"
                if ruta_jsonl.exists():
                    _restaurar_tabla(conn, esquema=esquema, tabla=tabla, ruta_jsonl=ruta_jsonl)
            conn.commit()

    fin = ahora_utc()
    rto = calcular_rto_observado_segundos(inicio, fin)
    rpo = calcular_rpo_observado_segundos(
        momento_snapshot=snapshot["generado_en"], momento_restauracion=fin
    )

    _registrar_resultado(
        snapshot_id=snapshot["id"], rto=rto, rpo=rpo, resultado="exitosa", detalle=None
    )
    return ResultadoPruebaRestauracion(
        resultado="exitosa", rto_observado_segundos=rto, rpo_observado_segundos=rpo, detalle=None
    )


def _registrar_resultado(
    *,
    snapshot_id: int | None,
    rto: int | None,
    rpo: int | None,
    resultado: str,
    detalle: str | None,
) -> None:
    with alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL), sesion() as conn:
        conn.execute(
            insert(prueba_restauracion).values(
                id=generar_id(),
                snapshot_id=snapshot_id,
                ejecutado_en=ahora_utc(),
                rto_observado_segundos=rto or 0,
                rpo_observado_segundos=rpo or 0,
                resultado=resultado,
                detalle=detalle,
            )
        )


def obtener_ultima_prueba_restauracion() -> dict | None:
    with alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL), sesion() as conn:
        fila = conn.execute(
            select(prueba_restauracion).order_by(prueba_restauracion.c.ejecutado_en.desc()).limit(1)
        ).first()
    if fila is None:
        return None
    return {
        "id": fila.id,
        "rto_observado_segundos": fila.rto_observado_segundos,
        "rpo_observado_segundos": fila.rpo_observado_segundos,
        "resultado": fila.resultado,
    }
