"""Pruebas de dominio: politica minima de contrasena (Sprint S1.10, US1,
FR-013)."""

import pytest
from aerohub_tenancy.domain import PasswordInvalida, validar_password


def test_password_valida_no_lanza():
    validar_password("correcto123")


def test_password_corta_lanza_con_requisito_de_longitud():
    with pytest.raises(PasswordInvalida, match="al menos"):
        validar_password("abc1")


def test_password_sin_letra_lanza_con_requisito_de_letra():
    with pytest.raises(PasswordInvalida, match="letra"):
        validar_password("1234567890")


def test_password_sin_digito_lanza_con_requisito_de_digito():
    with pytest.raises(PasswordInvalida, match="digito"):
        validar_password("abcdefghij")


def test_password_vacia_lanza_por_longitud():
    with pytest.raises(PasswordInvalida, match="al menos"):
        validar_password("")
