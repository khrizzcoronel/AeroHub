from datetime import UTC, datetime

import pytest
from aerohub_fids.domain import PlantillaFids, PlantillaInvalida


def _plantilla(**overrides):
    base = dict(
        id=1,
        tenant_id=1,
        nombre="salidas-internacional",
        definicion_json={"filas": [{"texto": "vuelo"}]},
        version=1,
        vigente_desde=datetime(2026, 1, 1, tzinfo=UTC),
        creada_por_usuario_id=1,
    )
    base.update(overrides)
    return PlantillaFids(**base)


def test_plantilla_valida_se_construye():
    p = _plantilla()
    assert p.version == 1


def test_nombre_vacio_rechazado():
    with pytest.raises(PlantillaInvalida):
        _plantilla(nombre="   ")


def test_version_no_positiva_rechazada():
    with pytest.raises(PlantillaInvalida):
        _plantilla(version=0)


def test_definicion_json_no_dict_rechazada():
    with pytest.raises(PlantillaInvalida):
        _plantilla(definicion_json=["no", "es", "un", "objeto"])


@pytest.mark.parametrize(
    "clave", ["nombre_pasajero", "pasaporte", "email_pasajero", "asiento", "pnr"]
)
def test_pn11_campo_pii_en_raiz_rechazado(clave):
    with pytest.raises(PlantillaInvalida, match="PN-11"):
        _plantilla(definicion_json={clave: "x"})


def test_pn11_campo_pii_anidado_rechazado():
    definicion = {"filas": [{"columnas": [{"pnr": "ABC123"}]}]}
    with pytest.raises(PlantillaInvalida, match="PN-11"):
        _plantilla(definicion_json=definicion)


def test_definicion_json_sin_pii_se_acepta():
    definicion = {
        "filas": [
            {"tipo": "encabezado", "texto": "Salidas"},
            {"tipo": "vuelo", "campos": ["numero_vuelo", "destino", "estado"]},
        ]
    }
    p = _plantilla(definicion_json=definicion)
    assert p.definicion_json == definicion
