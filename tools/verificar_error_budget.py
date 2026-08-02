#!/usr/bin/env python3
"""Compuerta de bloqueo de despliegue por error budget (Sprint S1.8, CU-D6,
US3; RF-009/RF-010; contracts/error-budget-gate.md de
specs/010-support-observability/; research.md Decision 2).

Vive en `tools/`, fuera de `services/` (Principio II de la constitucion,
misma categoria que `tools/lint_ddl_nomenclature.py`): no es logica de
negocio de ningun modulo, es tooling de plataforma invocable desde CI/CD y
a mano -- no existe todavia un pipeline de CD real contra el cual conectarlo
(research.md Decision 2), asi que este script queda listo para ese dia sin
necesitar rediseno. Reutiliza
`aerohub_support.application.consultar_observabilidad` -- el mismo calculo
que expone `GET /support/observabilidad/uptime`, para que la compuerta y el
panel nunca diverjan.

Uso:
    uv run python tools/verificar_error_budget.py --servicio aodb
    uv run python tools/verificar_error_budget.py --servicio aodb \\
        --override --motivo "release critica aprobada por on-call, ver INC-123"

Codigos de salida (contracts/error-budget-gate.md):
    0 -- consumo < 80%, o override valido con motivo (auditado)
    1 -- consumo >= 80%, sin override
    2 -- --override sin --motivo (error de uso; no se despliega ni se audita)
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from aerohub_kernel import generar_id
from aerohub_repository import alcance_global, registrar_auditoria, sesion
from aerohub_support.application import obtener_uptime_y_error_budget
from aerohub_support.domain import UMBRAL_BLOQUEO_DESPLIEGUE_PCT

_MOTIVO_ALCANCE_GLOBAL = "verificacion_error_budget_ci"
_ROL_CI = "role_platform_admin"


def _auditar_override(*, servicio: str, consumo_pct: float, motivo: str) -> None:
    """Deja constancia del override en compliance.log_auditoria (esquema/
    tabla sinteticos 'observabilidad'/'bloqueo_despliegue', mismo patron de
    reutilizacion que la denegacion de licencia de S1.7) -- OBLIGATORIO
    antes de continuar, nunca un override silencioso."""
    with alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL_CI), sesion() as conn:
        registrar_auditoria(
            conn,
            esquema="observabilidad",
            tabla="bloqueo_despliegue",
            registro_id=generar_id(),
            operacion="UPDATE",
            valores_nuevos={"servicio": servicio, "consumo_pct": consumo_pct, "motivo": motivo},
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--servicio", required=True, choices=("aodb", "fids"))
    parser.add_argument("--override", action="store_true")
    parser.add_argument("--motivo", default=None)
    args = parser.parse_args(argv)

    if args.override and not args.motivo:
        print(
            "error: --override exige --motivo explicito (sin override silencioso)",
            file=sys.stderr,
        )
        return 2

    resultado = obtener_uptime_y_error_budget(args.servicio)
    consumo_pct = resultado.error_budget_consumido_pct
    print(
        f"servicio={args.servicio} uptime={resultado.uptime_pct:.4f}% "
        f"error_budget_consumido={consumo_pct:.2f}%"
    )

    if consumo_pct < UMBRAL_BLOQUEO_DESPLIEGUE_PCT:
        print("OK -- error budget dentro del umbral, despliegue permitido.")
        return 0

    if args.override:
        _auditar_override(servicio=args.servicio, consumo_pct=consumo_pct, motivo=args.motivo)
        print(f"BLOQUEO LEVANTADO por override auditado: {args.motivo!r}")
        return 0

    print(
        f"BLOQUEADO -- consumo de error budget ({consumo_pct:.2f}%) supera el umbral "
        f"({UMBRAL_BLOQUEO_DESPLIEGUE_PCT}%). Usar --override --motivo \"...\" para liberar.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
