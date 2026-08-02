"""Configuracion por variables de entorno (Sprint S1.9). Mismo patron que
`aerohub_repository.base._dsn()`: valores por defecto razonables para
desarrollo local, sobreescribibles por Docker Compose
(`infra/docker-compose.yml`, servicio `continuidad-agente`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConexionAdmin:
    host: str
    port: int
    database: str
    username: str
    password: str


def _conexion(prefijo: str, *, host_defecto: str, port_defecto: int = 50000) -> ConexionAdmin:
    return ConexionAdmin(
        host=os.environ.get(f"{prefijo}_HOST", host_defecto),
        port=int(os.environ.get(f"{prefijo}_PORT", str(port_defecto))),
        database=os.environ.get(f"{prefijo}_DATABASE", "aerohub"),
        username=os.environ.get(f"{prefijo}_USERNAME", "monetdb"),
        password=os.environ.get(f"{prefijo}_PASSWORD", "aerohub"),
    )


def conexion_primario() -> ConexionAdmin:
    return _conexion("AEROHUB_PRIMARY", host_defecto="localhost")


def conexion_standby() -> ConexionAdmin:
    return _conexion("AEROHUB_STANDBY", host_defecto="localhost", port_defecto=50001)


def conexion_restore_test() -> ConexionAdmin:
    return _conexion("AEROHUB_RESTORE_TEST", host_defecto="localhost", port_defecto=50002)


def ruta_snapshotstage() -> str:
    return os.environ.get("AEROHUB_SNAPSHOT_PATH", "/snapshotstage")


def minio_endpoint() -> str:
    return os.environ.get("AEROHUB_MINIO_ENDPOINT", "http://localhost:9002")


def minio_access_key() -> str:
    return os.environ.get("AEROHUB_MINIO_ACCESS_KEY", "aerohub")


def minio_secret_key() -> str:
    return os.environ.get("AEROHUB_MINIO_SECRET_KEY", "aerohub123")


def minio_bucket() -> str:
    return os.environ.get("AEROHUB_MINIO_BUCKET", "aerohub-continuidad")


def puerto_metricas() -> int:
    return int(os.environ.get("AEROHUB_METRICS_PORT", "9101"))


def nombre_standby() -> str:
    """Identificador logico del standby en `continuidad.shipper_checkpoint`
    -- hoy solo hay uno, pero la tabla ya soporta mas de una fila."""
    return os.environ.get("AEROHUB_STANDBY_NOMBRE", "monetdb-standby")
