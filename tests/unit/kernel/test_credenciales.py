import pytest
from aerohub_kernel.credenciales import (
    hash_credencial,
    requiere_rehash,
    verificar_credencial,
)


def test_hash_no_es_el_secreto_en_claro():
    h = hash_credencial("una-contrasena-de-prueba")
    assert h != "una-contrasena-de-prueba"
    assert h.startswith("$argon2id$")


def test_verificar_credencial_correcta():
    h = hash_credencial("correcta-123")
    assert verificar_credencial("correcta-123", h) is True


def test_verificar_credencial_incorrecta():
    h = hash_credencial("correcta-123")
    assert verificar_credencial("incorrecta-456", h) is False


def test_hash_es_distinto_cada_vez_mismo_secreto():
    # Argon2id incluye salt aleatorio -- dos hashes del mismo secreto no
    # deben coincidir nunca, aunque ambos verifiquen correctamente.
    a = hash_credencial("mismo-secreto")
    b = hash_credencial("mismo-secreto")
    assert a != b
    assert verificar_credencial("mismo-secreto", a)
    assert verificar_credencial("mismo-secreto", b)


def test_secreto_vacio_rechazado():
    with pytest.raises(ValueError):
        hash_credencial("")


def test_hash_reciente_no_requiere_rehash():
    h = hash_credencial("algo")
    assert requiere_rehash(h) is False
