from aerohub_continuidad.domain.checksum import calcular_checksum_sha256, checksums_coinciden


def test_checksum_es_determinista():
    contenido = b"contenido de prueba"
    assert calcular_checksum_sha256(contenido) == calcular_checksum_sha256(contenido)


def test_checksum_distinto_para_contenido_distinto():
    assert calcular_checksum_sha256(b"a") != calcular_checksum_sha256(b"b")


def test_checksums_coinciden_es_insensible_a_mayusculas():
    a = calcular_checksum_sha256(b"x")
    assert checksums_coinciden(a.upper(), a.lower()) is True


def test_checksums_no_coinciden_detecta_corrupcion():
    a = calcular_checksum_sha256(b"contenido original")
    b = calcular_checksum_sha256(b"contenido corrupto")
    assert checksums_coinciden(a, b) is False
