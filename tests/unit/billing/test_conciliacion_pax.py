from aerohub_billing.domain import diferencia, puede_conciliar


def test_diferencia_cero_cuando_coinciden():
    assert diferencia(pax_reportado_aerolinea=180, pax_registrado_sistema=180) == 0


def test_diferencia_no_nula_cuando_no_coinciden():
    assert diferencia(pax_reportado_aerolinea=180, pax_registrado_sistema=175) == 5


def test_puede_conciliar_solo_si_diferencia_es_cero():
    assert puede_conciliar(pax_reportado_aerolinea=180, pax_registrado_sistema=180) is True
    assert puede_conciliar(pax_reportado_aerolinea=180, pax_registrado_sistema=179) is False
