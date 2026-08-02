"""Ciclo de snapshot y catalogo (Sprint S1.9, ADR-018 C2;
contracts/snapshot-catalogo.md de specs/011-continuidad-rto-rpo/).

`tipo='programado'` usa `sys.hot_snapshot()` (formato interno del motor,
rapido). `tipo='volcado_diario'` es un volcado logico PROPIO via SQL
(`SELECT *` tabla por tabla, serializado a JSON-lines) -- deliberadamente
INDEPENDIENTE del formato interno de `hot_snapshot()` (ADR-018: "volcado
logico completo diario... independiente del formato interno del motor"),
sin depender de herramientas de cliente de MonetDB (`msqldump`) que no
estan instaladas en la imagen de `continuidad-agente`.
"""

from __future__ import annotations

import json
import os
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import datetime

from aerohub_kernel import ahora_utc, generar_id
from aerohub_repository import alcance_global, escribir_journal, registrar_auditoria, sesion
from sqlalchemy import insert, select, update

from ..domain.checksum import calcular_checksum_sha256, checksums_coinciden
from ..domain.identificador_sql import validar_identificador
from .conexiones import asegurar_bucket, cliente_minio, conexion_pymonetdb
from .config import conexion_primario, minio_bucket, ruta_snapshotstage
from .tablas import snapshot_base

_MOTIVO_ALCANCE_GLOBAL = "ciclo_snapshot_continuidad"
_ROL = "role_platform_admin"

_TABLAS_EXCLUIDAS_VOLCADO = frozenset({"journal_mutacion"})  # se replica por si sola (C1/C3)


class SnapshotFallido(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ResultadoSnapshot:
    snapshot_id: int
    estado: str


def _asegurar_directorio_escribible(ruta: str) -> None:
    """`continuidad-agente` corre como root (imagen `python:3.12-slim` sin
    `USER`) -- ajusta el permiso del volumen compartido en cada arranque
    para que `sys.hot_snapshot()` (que corre como uid 5000 dentro del
    contenedor `monetdb`) pueda escribir ahi, sin depender de un paso
    manual (docs/runbooks/monetdb.md, hallazgo empirico de S1.9). 0o777 es
    deliberado, no un descuido: es un volumen de STAGING efimero (los
    artefactos se suben a MinIO y se borran localmente de inmediato,
    `ejecutar_ciclo_snapshot`), compartido entre dos contenedores con uids
    distintos (`monetdb` corre como uid 5000, `continuidad-agente` como
    root) sin un grupo Unix compartido configurado -- una mascara mas
    estricta bloquearia la escritura legitima de `sys.hot_snapshot()`."""
    os.makedirs(ruta, exist_ok=True)
    os.chmod(ruta, 0o777)  # nosec B103 -- volumen de staging compartido, ver docstring


def _lsn_actual(conn) -> int:  # noqa: ANN001 -- pymonetdb.Connection
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(MAX(lsn), 0) FROM continuidad.journal_mutacion")
    return cur.fetchone()[0]


def _nombre_archivo(tipo: str, ahora: datetime) -> str:
    marca = ahora.strftime("%Y%m%dT%H%M%SZ")
    return f"{tipo}_{marca}.tar"


def _generar_hot_snapshot(conn, ruta_local: str) -> None:  # noqa: ANN001
    cur = conn.cursor()
    cur.execute(f"CALL sys.hot_snapshot('{ruta_local}')")


def _generar_volcado_logico(conn, ruta_local: str) -> None:  # noqa: ANN001
    """Volcado logico propio: enumera tablas de usuario, exporta cada una
    como JSON-lines dentro de un tar -- sin depender de `msqldump` ni del
    formato binario de `hot_snapshot()`."""
    cur = conn.cursor()
    cur.execute(
        "SELECT s.name, t.name FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.id "
        "WHERE t.system = FALSE AND t.type = 0 ORDER BY s.name, t.name"
    )
    tablas = [
        (esquema, tabla)
        for esquema, tabla in cur.fetchall()
        if tabla not in _TABLAS_EXCLUIDAS_VOLCADO
    ]

    with tempfile.TemporaryDirectory() as directorio_temporal, tarfile.open(ruta_local, "w") as tar:
        for esquema, tabla in tablas:
            # Defensa en profundidad -- ver domain/identificador_sql.py:
            # aunque esquema/tabla vienen del propio catalogo del motor
            # (sys.tables), no de entrada externa, se validan igual antes
            # de interpolar (ningun driver de MonetDB parametriza nombres).
            esquema_val = validar_identificador(esquema)
            tabla_val = validar_identificador(tabla)
            cur_tabla = conn.cursor()
            cur_tabla.execute(f'SELECT * FROM "{esquema_val}"."{tabla_val}"')  # nosec B608
            columnas = [d[0] for d in cur_tabla.description]
            ruta_tabla = os.path.join(directorio_temporal, f"{esquema}.{tabla}.jsonl")
            with open(ruta_tabla, "w", encoding="utf-8") as f:
                for fila in cur_tabla.fetchall():
                    valores = dict(zip(columnas, fila, strict=True))
                    f.write(json.dumps(valores, default=str) + "\n")
            tar.add(ruta_tabla, arcname=f"{esquema}.{tabla}.jsonl")


def ejecutar_ciclo_snapshot(*, tipo: str) -> ResultadoSnapshot:
    ruta_directorio = ruta_snapshotstage()
    _asegurar_directorio_escribible(ruta_directorio)

    ahora = ahora_utc()
    nombre_archivo = _nombre_archivo(tipo, ahora)
    ruta_local = os.path.join(ruta_directorio, nombre_archivo)

    conexion = conexion_primario()
    with conexion_pymonetdb(conexion) as conn:
        lsn_corte = _lsn_actual(conn)
        if tipo == "programado":
            _generar_hot_snapshot(conn, ruta_local)
        elif tipo == "volcado_diario":
            _generar_volcado_logico(conn, ruta_local)
        else:
            raise SnapshotFallido(f"tipo de snapshot invalido: {tipo!r}")

    if not os.path.exists(ruta_local):
        raise SnapshotFallido(f"el artefacto esperado no aparecio en {ruta_local!r}")

    with open(ruta_local, "rb") as f:
        contenido = f.read()
    checksum_local = calcular_checksum_sha256(contenido)

    clave_objeto = f"{tipo}/{nombre_archivo}"
    cliente = cliente_minio()
    asegurar_bucket(cliente)
    cliente.upload_file(ruta_local, minio_bucket(), clave_objeto)

    snapshot_id = generar_id()
    with alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL), sesion() as sesion_conn:
        sesion_conn.execute(
            insert(snapshot_base).values(
                id=snapshot_id,
                tipo=tipo,
                lsn_corte=lsn_corte,
                generado_en=ahora,
                ruta_artefacto=clave_objeto,
                hash_artefacto=checksum_local,
                estado="generado",
            )
        )
        escribir_journal(
            sesion_conn,
            esquema="continuidad",
            tabla="snapshot_base",
            operacion="INSERT",
            clave_primaria={"id": snapshot_id},
            payload={"id": snapshot_id, "tipo": tipo, "lsn_corte": lsn_corte},
        )

    # Verificacion: vuelve a descargar el objeto de MinIO y recalcula el
    # checksum -- confirma que lo que quedo persistido en el almacenamiento
    # de objetos es exactamente lo que se genero, no solo lo que se
    # calculo antes de subir (FR-004).
    objeto = cliente.get_object(Bucket=minio_bucket(), Key=clave_objeto)
    contenido_remoto = objeto["Body"].read()
    checksum_remoto = calcular_checksum_sha256(contenido_remoto)
    coincide = checksums_coinciden(checksum_remoto, checksum_local)
    estado_final = "verificado" if coincide else "corrupto"
    verificado_en = ahora_utc()

    with alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL), sesion() as sesion_conn:
        sesion_conn.execute(
            update(snapshot_base)
            .where(snapshot_base.c.id == snapshot_id)
            .values(estado=estado_final, verificado_en=verificado_en)
        )
        escribir_journal(
            sesion_conn,
            esquema="continuidad",
            tabla="snapshot_base",
            operacion="UPDATE",
            clave_primaria={"id": snapshot_id},
            payload={"id": snapshot_id, "estado": estado_final},
        )
        registrar_auditoria(
            sesion_conn,
            esquema="continuidad",
            tabla="snapshot_base",
            registro_id=snapshot_id,
            operacion="INSERT",
            valores_nuevos={"tipo": tipo, "lsn_corte": lsn_corte, "estado": estado_final},
        )

    os.remove(ruta_local)  # ya esta en MinIO -- no se conserva copia local
    return ResultadoSnapshot(snapshot_id=snapshot_id, estado=estado_final)


def _fila_a_dict(fila) -> dict:  # noqa: ANN001
    return {
        "id": fila.id,
        "tipo": fila.tipo,
        "lsn_corte": fila.lsn_corte,
        "generado_en": fila.generado_en,
        "ruta_artefacto": fila.ruta_artefacto,
        "hash_artefacto": fila.hash_artefacto,
    }


def obtener_ultimo_snapshot_verificado() -> dict | None:
    with alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL), sesion() as conn:
        fila = conn.execute(
            select(snapshot_base)
            .where(snapshot_base.c.estado == "verificado")
            .order_by(snapshot_base.c.generado_en.desc())
            .limit(1)
        ).first()
    return None if fila is None else _fila_a_dict(fila)


def obtener_ultimo_snapshot_verificado_de_tipo(tipo: str) -> dict | None:
    """Restauracion automatizada (US4) usa exclusivamente 'volcado_diario'
    -- es el unico formato restaurable por SQL/Python puro sin acceso al
    control del proceso mserver5 (research.md Decision 10 de
    specs/011-continuidad-rto-rpo/); 'programado' (hot_snapshot binario)
    quedaria disponible para una restauracion MANUAL con intervencion de
    infraestructura, fuera de alcance de este ciclo automatico."""
    with alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL), sesion() as conn:
        fila = conn.execute(
            select(snapshot_base)
            .where(snapshot_base.c.estado == "verificado", snapshot_base.c.tipo == tipo)
            .order_by(snapshot_base.c.generado_en.desc())
            .limit(1)
        ).first()
    return None if fila is None else _fila_a_dict(fila)
