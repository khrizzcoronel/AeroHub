#!/usr/bin/env python3
"""Preflight de conmutacion hacia la replica de respaldo (Sprint S1.9,
ADR-018, C4; contracts/conmutacion-runbook.md de
specs/011-continuidad-rto-rpo/).

NO reinicia contenedores ni cambia configuracion -- solo verifica el
atraso pendiente y guia a la persona que decide conmutar hacia
docs/runbooks/continuidad_failover.md (research.md Decision 8: la
conmutacion real exige supervision humana explicita).

Uso:
    uv run python tools/continuidad_conmutar.py --standby monetdb-standby

Codigos de salida:
    0 -- atraso dentro de tolerancia (con o sin advertencia), pasos impresos
    1 -- atraso supera el umbral de alerta, conmutar ahora arriesga RPO
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from aerohub_continuidad.operaciones.shipper import (
    obtener_atraso_segundos,
    obtener_ultimo_lsn_aplicado,
)

_UMBRAL_ALERTA_SEGUNDOS = 120.0
_DSN_STANDBY_TEMPLATE = "monetdb://aerohub_app:aerohub_app_dev_password@{standby}:50000/aerohub"
_RUTA_RUNBOOK = "docs/runbooks/continuidad_failover.md"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--standby", required=True)
    args = parser.parse_args(argv)

    atraso_segundos = obtener_atraso_segundos()
    ultimo_lsn = obtener_ultimo_lsn_aplicado()
    print(
        f"atraso actual del standby {args.standby!r}: {atraso_segundos:.1f}s "
        f"(ultimo lsn aplicado: {ultimo_lsn})"
    )

    if atraso_segundos >= _UMBRAL_ALERTA_SEGUNDOS:
        print(
            f"ERROR -- el atraso ({atraso_segundos:.1f}s) supera el umbral de alerta "
            f"({_UMBRAL_ALERTA_SEGUNDOS:.0f}s). Conmutar ahora arriesga perder mas datos de los "
            f"tolerados (RPO <= 5 min, ADR-018). Esperar a que el shipper drene, o confirmar "
            f"explicitamente que la perdida es aceptable antes de continuar.",
            file=sys.stderr,
        )
        return 1

    if atraso_segundos > 0:
        print(
            f"ADVERTENCIA -- el standby tiene un atraso de {atraso_segundos:.1f}s "
            "(por debajo del umbral de alerta). Conmutar ahora perderia como maximo esa ventana."
        )
    else:
        print("OK -- el standby esta al dia, sin atraso pendiente.")

    dsn_sugerido = _DSN_STANDBY_TEMPLATE.format(standby=args.standby)
    print()
    print(f"DSN sugerido para AEROHUB_DB_DSN: {dsn_sugerido}")
    print(f"Seguir el procedimiento completo en {_RUTA_RUNBOOK} antes de aplicar el cambio.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
