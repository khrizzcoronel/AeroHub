"""PN-04 reforzada (Sprint S1.9): la purga del journal de continuidad
SIEMPRE condiciona el DELETE a ambas restricciones a la vez -- antiguedad Y
avance confirmado del shipper (research.md Decision 7 de
specs/011-continuidad-rto-rpo/). Analisis de codigo fuente, mismo patron
que test_pn04_compliance_append_only.py: una purga que solo mirara la
antiguedad podria destruir una entrada que el shipper todavia no replico.
"""

from __future__ import annotations

from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
ARCHIVO_PURGA = (
    RAIZ / "packages" / "continuidad" / "aerohub_continuidad" / "operaciones" / "purga.py"
)


@pytest.mark.sin_bd
def test_purga_condiciona_a_antiguedad_y_avance_del_shipper():
    codigo = ARCHIVO_PURGA.read_text(encoding="utf-8")

    inicio = codigo.index("def purgar_journal_confirmado")
    cuerpo_funcion = codigo[inicio:]

    assert "delete(journal_mutacion)" in cuerpo_funcion, (
        "purgar_journal_confirmado debe operar sobre journal_mutacion via delete()"
    )
    assert "ocurrido_en" in cuerpo_funcion, (
        "PN-04 reforzada: falta la condicion de antiguedad (ocurrido_en) en la purga"
    )
    assert "lsn_minimo_confirmado" in cuerpo_funcion, (
        "PN-04 reforzada: falta la condicion de avance confirmado del shipper en la purga -- "
        "una purga solo por antiguedad arriesgaria borrar una entrada aun no replicada"
    )


@pytest.mark.sin_bd
def test_purga_no_asume_confirmacion_sin_checkpoint_registrado():
    codigo = ARCHIVO_PURGA.read_text(encoding="utf-8")
    assert "lsn_minimo_confirmado is None" in codigo, (
        "PN-04 reforzada: sin ninguna replica registrada en shipper_checkpoint, "
        "la purga debe fallar cerrado (no purgar nada), nunca asumir que todo esta confirmado"
    )
