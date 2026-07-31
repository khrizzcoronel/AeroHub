from datetime import UTC, datetime, timedelta, timezone

from aerohub_kernel import ahora_utc, es_utc


def test_ahora_utc_es_utc():
    assert es_utc(ahora_utc())


def test_es_utc_rechaza_naive():
    assert not es_utc(datetime(2026, 1, 1))


def test_es_utc_rechaza_otro_huso():
    assert not es_utc(datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=-5))))


def test_es_utc_acepta_utc_explicito():
    assert es_utc(datetime(2026, 1, 1, tzinfo=UTC))
