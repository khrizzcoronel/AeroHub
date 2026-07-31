#!/usr/bin/env python3
"""Genera docs/api/openapi.yaml a partir de la app compuesta (Sprint S1.2,
Plan §8.2, RF-T02: "especificacion OpenAPI 3.1 generada desde Pydantic v2").

`services/gateway/main.py` se carga por ruta de archivo, no por import
normal, por el mismo motivo documentado en ese archivo (independencia de
modulos, .importlinter): es un script fuera de cualquier paquete `aerohub_*`.

Uso:
    uv run python tools/generar_openapi.py
    npx spectral lint docs/api/openapi.yaml
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import yaml

RUTA_MAIN = Path(__file__).resolve().parent.parent / "services" / "gateway" / "main.py"
RUTA_SALIDA = Path(__file__).resolve().parent.parent / "docs" / "api" / "openapi.yaml"


def main() -> None:
    spec = importlib.util.spec_from_file_location("_aerohub_gateway_main", RUTA_MAIN)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo
    spec.loader.exec_module(modulo)

    esquema_openapi = modulo.crear_app().openapi()
    RUTA_SALIDA.parent.mkdir(parents=True, exist_ok=True)
    with RUTA_SALIDA.open("w", encoding="utf-8") as f:
        yaml.safe_dump(esquema_openapi, f, sort_keys=False, allow_unicode=True)
    print(f"escrito {RUTA_SALIDA} (openapi {esquema_openapi['openapi']})")


if __name__ == "__main__":
    main()
