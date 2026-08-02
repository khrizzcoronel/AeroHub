#!/usr/bin/env python3
"""Agente de continuidad operacional (Sprint S1.9, ADR-018).

Proceso continuo (research.md Decision 4 de specs/011-continuidad-rto-rpo/):
corre los ciclos de snapshot programado (C2), *shipper* (C3) y prueba de
restauracion semanal (C4) como tareas asincronas concurrentes dentro del
mismo proceso, y expone `/metrics` para Prometheus -- mismo patron que el
monitor de senal FIDS en `services/gateway/main.py` (S1.3).

Sin argumentos: arranca el proceso continuo (los 3 ciclos + /metrics), tal
como corre dentro del contenedor `continuidad-agente`. Con
`--forzar-snapshot`/`--forzar-prueba-restauracion`: ejecuta UNA sola vez la
accion indicada y termina, sin arrancar el proceso continuo -- uso manual
de verificacion (quickstart.md Escenarios 1 y 4).

Uso:
    uv run python tools/continuidad_agente.py
    uv run python tools/continuidad_agente.py --forzar-snapshot programado
    uv run python tools/continuidad_agente.py --forzar-prueba-restauracion
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from collections.abc import Sequence

from aerohub_continuidad.metricas import (
    observar_atraso_standby,
    observar_edad_snapshot,
    observar_prueba_restauracion,
)
from aerohub_continuidad.operaciones.config import puerto_metricas
from aerohub_continuidad.operaciones.purga import purgar_journal_confirmado
from aerohub_continuidad.operaciones.restauracion import (
    SinSnapshotParaRestaurar,
    ejecutar_prueba_restauracion,
    obtener_ultima_prueba_restauracion,
)
from aerohub_continuidad.operaciones.shipper import ejecutar_ciclo_shipper, obtener_atraso_segundos
from aerohub_continuidad.operaciones.snapshot import (
    ejecutar_ciclo_snapshot,
    obtener_ultimo_snapshot_verificado,
)
from aerohub_kernel import ahora_utc
from prometheus_client import start_http_server

_registro = logging.getLogger("aerohub.continuidad_agente")

_INTERVALO_SNAPSHOT_PROGRAMADO_S = 6 * 60 * 60
_INTERVALO_VOLCADO_DIARIO_S = 24 * 60 * 60
_INTERVALO_PUBLICAR_METRICAS_S = 60
_INTERVALO_SHIPPER_S = 5
_INTERVALO_PRUEBA_RESTAURACION_S = 7 * 24 * 60 * 60
_INTERVALO_PURGA_S = 60 * 60


async def _ciclo_snapshot_programado() -> None:
    while True:
        try:
            resultado = ejecutar_ciclo_snapshot(tipo="programado")
            _registro.info("snapshot programado: %s", resultado)
        except Exception:
            _registro.exception("fallo el ciclo de snapshot programado")
        await asyncio.sleep(_INTERVALO_SNAPSHOT_PROGRAMADO_S)


async def _ciclo_volcado_diario() -> None:
    while True:
        await asyncio.sleep(_INTERVALO_VOLCADO_DIARIO_S)
        try:
            resultado = ejecutar_ciclo_snapshot(tipo="volcado_diario")
            _registro.info("volcado diario: %s", resultado)
        except Exception:
            _registro.exception("fallo el ciclo de volcado logico diario")


async def _ciclo_shipper() -> None:
    while True:
        try:
            resultado = ejecutar_ciclo_shipper()
            if resultado.aplicadas:
                _registro.info("shipper: %s", resultado)
        except Exception:
            _registro.exception("fallo el ciclo del shipper")
        await asyncio.sleep(_INTERVALO_SHIPPER_S)


async def _ciclo_prueba_restauracion() -> None:
    while True:
        await asyncio.sleep(_INTERVALO_PRUEBA_RESTAURACION_S)
        try:
            resultado = ejecutar_prueba_restauracion()
            _registro.info("prueba de restauracion: %s", resultado)
        except SinSnapshotParaRestaurar:
            _registro.warning(
                "prueba de restauracion omitida: aun no hay snapshot 'volcado_diario' verificado"
            )
        except Exception:
            _registro.exception("fallo la prueba de restauracion semanal")


async def _ciclo_purga() -> None:
    while True:
        try:
            purgadas = purgar_journal_confirmado()
            if purgadas:
                _registro.info("purga del journal: %d entradas eliminadas", purgadas)
        except Exception:
            _registro.exception("fallo el ciclo de purga del journal")
        await asyncio.sleep(_INTERVALO_PURGA_S)


async def _ciclo_publicar_metricas() -> None:
    """Publica la antiguedad del ultimo snapshot verificado, el atraso
    del standby y el resultado de la ultima prueba de restauracion de
    forma continua (contracts/shipper-metrica.md) -- separado de los
    ciclos que GENERAN/APLICAN cambios para que las metricas no queden
    desactualizadas entre un ciclo y el siguiente."""
    while True:
        try:
            ultimo = obtener_ultimo_snapshot_verificado()
            if ultimo is not None:
                edad_segundos = (ahora_utc() - ultimo["generado_en"]).total_seconds()
                observar_edad_snapshot(edad_segundos)
            observar_atraso_standby(obtener_atraso_segundos())
            ultima_prueba = obtener_ultima_prueba_restauracion()
            if ultima_prueba is not None:
                observar_prueba_restauracion(
                    rto_segundos=ultima_prueba["rto_observado_segundos"],
                    rpo_segundos=ultima_prueba["rpo_observado_segundos"],
                )
        except Exception:
            _registro.exception("fallo al publicar metricas de continuidad")
        await asyncio.sleep(_INTERVALO_PUBLICAR_METRICAS_S)


async def _correr_agente() -> None:
    start_http_server(puerto_metricas())
    await asyncio.gather(
        _ciclo_snapshot_programado(),
        _ciclo_volcado_diario(),
        _ciclo_shipper(),
        _ciclo_prueba_restauracion(),
        _ciclo_purga(),
        _ciclo_publicar_metricas(),
    )


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--forzar-snapshot", choices=("programado", "volcado_diario"), default=None)
    parser.add_argument("--forzar-prueba-restauracion", action="store_true")
    args = parser.parse_args(argv)

    if args.forzar_snapshot:
        resultado = ejecutar_ciclo_snapshot(tipo=args.forzar_snapshot)
        print(
            f"snapshot {args.forzar_snapshot}: "
            f"id={resultado.snapshot_id} estado={resultado.estado}"
        )
        return 0 if resultado.estado == "verificado" else 1

    if args.forzar_prueba_restauracion:
        try:
            resultado_restauracion = ejecutar_prueba_restauracion()
        except SinSnapshotParaRestaurar as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(
            f"prueba de restauracion: resultado={resultado_restauracion.resultado} "
            f"rto={resultado_restauracion.rto_observado_segundos}s "
            f"rpo={resultado_restauracion.rpo_observado_segundos}s"
        )
        return 0 if resultado_restauracion.resultado == "exitosa" else 1

    asyncio.run(_correr_agente())
    return 0


if __name__ == "__main__":
    sys.exit(main())
