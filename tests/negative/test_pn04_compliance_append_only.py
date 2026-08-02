"""PN-04 reforzada (Sprint S1.7, Plan Sec8.7): ninguna funcion de
UPDATE/DELETE existe en `aerohub_compliance.infrastructure.comandos` para
las tablas append-only (`tipo_incidente`, `incidente_seguridad`,
`tipo_reporte_regulatorio`, `reporte_dgac`, `acceso_auditor`,
`control_soc2`, `evidencia_soc2`) -- solo `post_mortem`/
`post_mortem_accion` tienen la excepcion de mutabilidad (ADR-009).

Analisis por AST del codigo fuente, mismo patron que
test_pn15_sql_fuera_del_repositorio.py: "ausencia de metodo expuesto" no
se puede probar invocando algo que no existe -- solo verificando
estaticamente que el codigo fuente nunca lo define.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
ARCHIVO_COMANDOS = (
    RAIZ / "services" / "compliance" / "aerohub_compliance" / "infrastructure" / "comandos.py"
)

TABLAS_APPEND_ONLY = (
    "tipo_incidente",
    "incidente_seguridad",
    "tipo_reporte_regulatorio",
    "reporte_dgac",
    "acceso_auditor",
    "control_soc2",
    "evidencia_soc2",
)


def _nombres_de_funciones_de_mutacion(prefijos: tuple[str, ...]) -> list[str]:
    codigo = ARCHIVO_COMANDOS.read_text(encoding="utf-8")
    arbol = ast.parse(codigo, filename=str(ARCHIVO_COMANDOS))
    nombres: list[str] = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.FunctionDef) and nodo.name.startswith(prefijos):
            nombres.append(nodo.name)
    return nombres


@pytest.mark.sin_bd
def test_pn04_sin_actualizar_ni_eliminar_para_tablas_append_only():
    nombres_mutacion = _nombres_de_funciones_de_mutacion(("actualizar_", "eliminar_"))
    permitidas = ("actualizar_causa_raiz_post_mortem", "publicar_post_mortem")
    hallazgos = [n for n in nombres_mutacion if n not in permitidas]
    assert hallazgos == [], (
        "PN-04 reforzada violada -- funcion(es) de mutacion inesperada en "
        f"aerohub_compliance.infrastructure.comandos: {hallazgos}"
    )


@pytest.mark.sin_bd
def test_pn04_cada_tabla_append_only_solo_tiene_insertar():
    codigo = ARCHIVO_COMANDOS.read_text(encoding="utf-8")
    for tabla in TABLAS_APPEND_ONLY:
        assert f"def insertar_{tabla}" in codigo or f"insert({tabla})" in codigo, (
            f"PN-04: no se encontro una funcion de insercion para {tabla!r}"
        )
        assert f"def actualizar_{tabla}" not in codigo, (
            f"PN-04 violada: existe actualizar_{tabla} para una tabla append-only"
        )
        assert f"def eliminar_{tabla}" not in codigo, (
            f"PN-04 violada: existe eliminar_{tabla} para una tabla append-only"
        )
