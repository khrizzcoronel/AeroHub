"""Pruebas de dominio de articulo de base de conocimientos (Sprint S1.8,
US4): invariantes y transiciones de estado (data-model.md, FR-012/FR-013)."""

import pytest
from aerohub_support.domain import (
    ArticuloKB,
    ArticuloKBInvalido,
    transicion_valida_articulo_kb,
)


def _articulo(**overrides):
    base = dict(
        id=1,
        titulo="Como reportar un incidente de AODB",
        cuerpo="Pasos para reportar...",
        version=1,
        estado="borrador",
        autor_usuario_id=1,
    )
    base.update(overrides)
    return ArticuloKB(**base)


def test_articulo_valido_se_construye():
    a = _articulo()
    assert a.version == 1


def test_titulo_vacio_rechazado():
    with pytest.raises(ArticuloKBInvalido):
        _articulo(titulo="   ")


def test_cuerpo_vacio_rechazado():
    with pytest.raises(ArticuloKBInvalido):
        _articulo(cuerpo="")


def test_version_no_positiva_rechazada():
    with pytest.raises(ArticuloKBInvalido):
        _articulo(version=0)


def test_estado_invalido_rechazado():
    with pytest.raises(ArticuloKBInvalido):
        _articulo(estado="revision")


@pytest.mark.parametrize(
    ("actual", "nuevo", "esperado"),
    [
        ("borrador", "publicado", True),
        ("borrador", "archivado", False),
        ("publicado", "archivado", True),
        ("publicado", "borrador", False),
        ("archivado", "publicado", False),
        ("archivado", "borrador", False),
    ],
)
def test_transicion_valida_articulo_kb(actual, nuevo, esperado):
    assert transicion_valida_articulo_kb(actual, nuevo) is esperado
