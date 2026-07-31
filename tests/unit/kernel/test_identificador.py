import threading

import pytest
from aerohub_kernel.identificador import EPOCA_AEROHUB_MS, GeneradorId, generar_id


def test_ids_son_unicos_y_monotonos_secuenciales():
    gen = GeneradorId()
    ids = [gen.siguiente() for _ in range(5000)]
    assert len(set(ids)) == len(ids)
    assert ids == sorted(ids)


def test_ids_son_unicos_bajo_concurrencia():
    gen = GeneradorId()
    resultados: list[int] = []
    lock = threading.Lock()

    def worker():
        valor = gen.siguiente()
        with lock:
            resultados.append(valor)

    hilos = [threading.Thread(target=worker) for _ in range(200)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    assert len(set(resultados)) == len(resultados) == 200


def test_id_siempre_positivo_y_cabe_en_bigint():
    gen = GeneradorId(nodo_id=1023)
    valor = gen.siguiente()
    assert valor > 0
    assert valor < 2**63  # BIGINT con signo


def test_nodo_id_fuera_de_rango_rechazado():
    with pytest.raises(ValueError):
        GeneradorId(nodo_id=1024)
    with pytest.raises(ValueError):
        GeneradorId(nodo_id=-1)


def test_reloj_retrocede_no_reutiliza_id(monkeypatch):
    gen = GeneradorId()
    # call 1 -> 1000; call 2 -> 1000 (mismo ms, secuencia++);
    # call 3 -> lee 999 (retrocedio), entra a _esperar_hasta(1000), que
    # vuelve a leer el reloj y obtiene 1001.
    tiempos = iter([1000, 1000, 999, 1001])

    def _ahora_ms_falso():
        return next(tiempos)

    monkeypatch.setattr(gen, "_ahora_ms", _ahora_ms_falso)
    id_a = gen.siguiente()
    id_b = gen.siguiente()
    id_c = gen.siguiente()  # ve el reloj retroceder a 999
    assert id_b > id_a
    assert id_c > id_b


def test_atajo_generar_id_funciona():
    a = generar_id()
    b = generar_id()
    assert b > a


def test_epoca_es_2026_01_01_utc():
    from datetime import UTC, datetime

    esperado = datetime(2026, 1, 1, tzinfo=UTC)
    assert int(esperado.timestamp() * 1000) == EPOCA_AEROHUB_MS
