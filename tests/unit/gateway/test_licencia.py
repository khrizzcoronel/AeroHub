from aerohub_gateway.domain.licencia import PREFIJO_A_CODIGO_MODULO, resolver_modulo_de_ruta


def test_resuelve_cada_prefijo_conocido():
    assert resolver_modulo_de_ruta("/billing/facturas") == "M5"
    assert resolver_modulo_de_ruta("/rampa/turnarounds") == "M4"
    assert resolver_modulo_de_ruta("/puertas/tablero") == "M3"
    assert resolver_modulo_de_ruta("/fids/plantillas") == "M2"
    assert resolver_modulo_de_ruta("/vuelos") == "M1"
    assert resolver_modulo_de_ruta("/passenger/tiempos-espera") == "M6"


def test_ruta_no_licenciable_devuelve_none():
    assert resolver_modulo_de_ruta("/tenants/nuevo") is None
    assert resolver_modulo_de_ruta("/metrics") is None
    assert resolver_modulo_de_ruta("/") is None


def test_diccionario_no_tiene_codigos_de_mas_de_cuatro_caracteres():
    assert all(len(codigo) <= 4 for codigo in PREFIJO_A_CODIGO_MODULO.values())
