"""PN-15 -- ningun modulo fuera de packages/repository emite SQL hacia
MonetDB (P1, ADR-014, cierra el analisis estatico del job "arquitectura" de
CI). Analisis por AST del codigo fuente, no por expresion regular sobre
texto -- un comentario o una cadena que contenga "create_engine" no dispara
un falso positivo, y una llamada real no se puede esconder con formato.

No prohibe construir objetos SQLAlchemy Core (Table, select(), insert()...)
fuera del repositorio -- eso es legitimo en `infrastructure/` de cada
modulo (ADR-017 §5.4): construir una sentencia es manipular una estructura
de datos Python, no hablar con el motor. Lo que se prohibe es CONECTAR:
crear un Engine propio (`create_engine`) o importar el driver crudo
(`pymonetdb`) fuera de `packages/repository`, que es el unico lugar
autorizado a hacerlo (`packages/repository/base.py`).

No escanea tests/: las pruebas legitimamente abren conexiones de
diagnostico/fixture fuera del engine guardado (ver tests/negative/conftest.py,
tests/integration/*), y no son parte de la aplicacion en ejecucion.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
DIRECTORIOS_VIGILADOS = ("services", "pipelines", "ml")
MODULOS_PROHIBIDOS = ("pymonetdb", "sqlalchemy_monetdb")


def _archivos_a_revisar() -> list[Path]:
    archivos: list[Path] = []
    for nombre_dir in DIRECTORIOS_VIGILADOS:
        base = RAIZ / nombre_dir
        if base.exists():
            archivos.extend(base.rglob("*.py"))
    return archivos


def _revisar_archivo(ruta: Path) -> list[str]:
    codigo = ruta.read_text(encoding="utf-8")
    arbol = ast.parse(codigo, filename=str(ruta))
    hallazgos: list[str] = []
    relativa = ruta.relative_to(RAIZ)

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                if alias.name.split(".")[0] in MODULOS_PROHIBIDOS:
                    hallazgos.append(
                        f"{relativa}:{nodo.lineno}: import de '{alias.name}' -- "
                        "solo packages/repository puede importar el driver de MonetDB"
                    )
        elif isinstance(nodo, ast.ImportFrom):
            if nodo.module and nodo.module.split(".")[0] in MODULOS_PROHIBIDOS:
                hallazgos.append(
                    f"{relativa}:{nodo.lineno}: import de '{nodo.module}' -- "
                    "solo packages/repository puede importar el driver de MonetDB"
                )
        elif (
            isinstance(nodo, ast.Call)
            and isinstance(nodo.func, ast.Name)
            and nodo.func.id == "create_engine"
        ):
            hallazgos.append(
                f"{relativa}:{nodo.lineno}: create_engine() fuera de packages/repository -- "
                "usar aerohub_repository.sesion() (P1, ADR-014)"
            )

    return hallazgos


@pytest.mark.sin_bd
def test_pn15_ningun_modulo_fuera_del_repositorio_crea_su_propio_engine():
    hallazgos: list[str] = []
    for archivo in _archivos_a_revisar():
        hallazgos.extend(_revisar_archivo(archivo))
    assert hallazgos == [], "PN-15 violado:\n" + "\n".join(hallazgos)
