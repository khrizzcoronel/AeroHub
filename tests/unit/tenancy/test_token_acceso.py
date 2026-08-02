"""Pruebas de dominio: vigencia y un-solo-uso de token de acceso (Sprint
S1.10, US4, data-model.md)."""

from datetime import UTC, datetime, timedelta

from aerohub_tenancy.domain import token_canjeable

_AHORA = datetime(2026, 8, 2, 12, 0, tzinfo=UTC)


def test_token_no_consumido_y_no_vencido_es_canjeable():
    assert token_canjeable(
        consumido_en=None, expira_en=_AHORA + timedelta(minutes=1), ahora=_AHORA
    )


def test_token_consumido_no_es_canjeable():
    assert not token_canjeable(
        consumido_en=_AHORA - timedelta(minutes=1),
        expira_en=_AHORA + timedelta(minutes=1),
        ahora=_AHORA,
    )


def test_token_vencido_no_es_canjeable():
    assert not token_canjeable(
        consumido_en=None, expira_en=_AHORA - timedelta(minutes=1), ahora=_AHORA
    )


def test_token_consumido_y_vencido_no_es_canjeable():
    assert not token_canjeable(
        consumido_en=_AHORA - timedelta(minutes=5),
        expira_en=_AHORA - timedelta(minutes=1),
        ahora=_AHORA,
    )
