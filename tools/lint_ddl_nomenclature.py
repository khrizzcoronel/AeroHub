#!/usr/bin/env python3
"""Verifica la convencion de nomenclatura de DDL (Plan §6.1, cierra SDD-DATA-001 M-10).

    CHECK        chk_<tabla>_<columna>
    UNIQUE       uq_<tabla>_<columnas>
    INDEX        idx_<tabla>_<columnas>
    FOREIGN KEY  fk_<tabla>_<destino>

Se ejecuta sobre todo archivo .sql bajo db/ddl/. Un nombre de restriccion que no
seye estos patrones hace fallar el paso "Convenciones" de CI (Sprint S0.1).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

DDL_ROOT = Path("db/ddl")

PATRONES = {
    "CONSTRAINT.*CHECK": re.compile(r"CONSTRAINT\s+(chk_\w+)\s", re.IGNORECASE),
    "CONSTRAINT.*UNIQUE": re.compile(r"CONSTRAINT\s+(uq_\w+)\s", re.IGNORECASE),
    "CONSTRAINT.*FOREIGN KEY": re.compile(r"CONSTRAINT\s+(fk_\w+)\s", re.IGNORECASE),
    "CREATE INDEX": re.compile(r"CREATE\s+INDEX\s+(idx_\w+)\s", re.IGNORECASE),
}

# Nombres de restriccion con CONSTRAINT explicito, cualquier prefijo permitido
# distinto del correcto, para detectar el error mas comun (constraint sin
# prefijo o con prefijo equivocado).
DECLARACION_CONSTRAINT = re.compile(
    r"CONSTRAINT\s+(\w+)\s+(CHECK|UNIQUE|FOREIGN KEY)", re.IGNORECASE
)
DECLARACION_INDICE = re.compile(r"CREATE\s+INDEX\s+(\w+)\s+ON", re.IGNORECASE)

PREFIJO_ESPERADO = {
    "CHECK": "chk_",
    "UNIQUE": "uq_",
    "FOREIGN KEY": "fk_",
}


def revisar_archivo(ruta: Path) -> list[str]:
    errores: list[str] = []
    texto = ruta.read_text(encoding="utf-8")

    for nombre, tipo in DECLARACION_CONSTRAINT.findall(texto):
        prefijo = PREFIJO_ESPERADO[tipo.upper()]
        if not nombre.lower().startswith(prefijo):
            errores.append(
                f"{ruta}: restriccion {tipo} '{nombre}' no sigue la convencion "
                f"'{prefijo}<tabla>_<columnas>' (Plan §6.1)"
            )

    for nombre in DECLARACION_INDICE.findall(texto):
        if not nombre.lower().startswith("idx_"):
            errores.append(
                f"{ruta}: indice '{nombre}' no sigue la convencion "
                f"'idx_<tabla>_<columnas>' (Plan §6.1)"
            )

    return errores


def main() -> int:
    if not DDL_ROOT.exists():
        print(f"{DDL_ROOT} no existe todavia (esperado antes de S0.2) — nada que revisar.")
        return 0

    archivos = sorted(DDL_ROOT.rglob("*.sql"))
    if not archivos:
        print(f"Sin archivos .sql bajo {DDL_ROOT} todavia — nada que revisar.")
        return 0

    errores: list[str] = []
    for archivo in archivos:
        errores.extend(revisar_archivo(archivo))

    if errores:
        print(f"Nomenclatura DDL: {len(errores)} violacion(es) de convencion.\n")
        for error in errores:
            print(f"  - {error}")
        return 1

    print(f"Nomenclatura DDL: {len(archivos)} archivo(s) conformes (Plan §6.1).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
