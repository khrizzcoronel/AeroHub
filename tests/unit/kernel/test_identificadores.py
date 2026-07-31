import pytest
from aerohub_kernel import CodigoIATA, CodigoICAO


@pytest.mark.parametrize("valor", ["AA", "UIO", "mx"])
def test_iata_valido_2_o_3_letras(valor):
    assert str(CodigoIATA(valor)) == valor.upper()


@pytest.mark.parametrize("valor", ["9W", "6E", "3M"])
def test_iata_acepta_digito_mas_letra(valor):
    """Codigos IATA reales usan digito+letra (9W Jet Airways, 6E IndiGo)."""
    assert str(CodigoIATA(valor)) == valor.upper()


@pytest.mark.parametrize("valor", ["A", "ABCD", "A!"])
def test_iata_invalido(valor):
    with pytest.raises(ValueError):
        CodigoIATA(valor)


@pytest.mark.parametrize("valor", ["AAL", "SEMX", "B738"])
def test_icao_valido_3_o_4_caracteres(valor):
    assert str(CodigoICAO(valor)) == valor.upper()


@pytest.mark.parametrize("valor", ["AA", "ABCDE"])
def test_icao_invalido(valor):
    with pytest.raises(ValueError):
        CodigoICAO(valor)
