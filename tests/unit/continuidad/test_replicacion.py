from aerohub_continuidad.domain.replicacion import debe_procesar


def test_lsn_mayor_al_ultimo_aplicado_debe_procesarse():
    assert debe_procesar(lsn=10, ultimo_lsn_aplicado=5) is True


def test_lsn_igual_al_ultimo_aplicado_no_debe_reprocesarse():
    assert debe_procesar(lsn=5, ultimo_lsn_aplicado=5) is False


def test_lsn_menor_al_ultimo_aplicado_no_debe_reprocesarse():
    assert debe_procesar(lsn=3, ultimo_lsn_aplicado=5) is False
