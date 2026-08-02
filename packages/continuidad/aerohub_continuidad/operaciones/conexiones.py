"""Conexiones administrativas directas (Sprint S1.9, research.md Decision
2/3 de specs/011-continuidad-rto-rpo/): `pymonetdb` sin pasar por
`aerohub_repository` -- son operaciones DBA de plataforma (snapshot,
replay generico cross-schema, restauracion) sobre motores que no son "el
primario que sirve peticiones de aplicacion", mismo trato que
`db/migrations/apply.py`/`db/seeds/generate.py` desde S0.2.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import boto3
import pymonetdb
from botocore.client import Config as BotoConfig

from .config import ConexionAdmin, minio_access_key, minio_bucket, minio_endpoint, minio_secret_key


@contextmanager
def conexion_pymonetdb(conexion: ConexionAdmin) -> Iterator[pymonetdb.Connection]:
    conn = pymonetdb.connect(
        hostname=conexion.host,
        port=conexion.port,
        database=conexion.database,
        username=conexion.username,
        password=conexion.password,
    )
    try:
        yield conn
    finally:
        conn.close()


def cliente_minio():  # noqa: ANN201 -- tipo de boto3, sin stub publico
    return boto3.client(
        "s3",
        endpoint_url=minio_endpoint(),
        aws_access_key_id=minio_access_key(),
        aws_secret_access_key=minio_secret_key(),
        config=BotoConfig(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def asegurar_bucket(cliente) -> None:  # noqa: ANN001
    """Idempotente -- MinIO no crea el bucket solo. `head_bucket` lanza si
    no existe; en ese caso se crea. No falla si ya existe (evita una
    carrera de "crear si no existe" mas compleja para un bucket que, en
    la practica, nunca se borra en desarrollo)."""
    try:
        cliente.head_bucket(Bucket=minio_bucket())
    except Exception:
        cliente.create_bucket(Bucket=minio_bucket())
