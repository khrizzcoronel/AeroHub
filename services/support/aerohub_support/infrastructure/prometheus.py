"""Cliente HTTP minimo contra la API de consulta de Prometheus (Sprint S1.8,
CU-D6, RF-E03/RNF-R02; research.md Decision 1).

`servicio` ("aodb"/"fids") resuelve HOY al MISMO target de scrape: ambos
modulos se sirven desde el UNICO proceso de `services/gateway`
(`infra/prometheus/prometheus.yml`, job "aerohub_gateway") -- no existe
todavia un proceso o target por modulo de negocio. La metrica `up`, que
Prometheus genera automaticamente para cada target scrapeado sin
instrumentacion adicional, es el unico dato de disponibilidad disponible con
ese grano hoy (research.md Decision 1: "sin necesidad de nuevos agentes de
sondeo externos"). El dia que AODB/FIDS se separen en procesos propios, esta
funcion gana un segundo target sin cambiar su contrato.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

import httpx

SERVICIOS_VALIDOS = ("aodb", "fids")

_JOB_PROMETHEUS = "aerohub_gateway"


class ServicioInvalido(Exception):
    pass


class PrometheusInalcanzable(Exception):
    pass


def _url_base() -> str:
    return os.environ.get("AEROHUB_PROMETHEUS_URL", "http://localhost:9090")


def _segundos_desde_inicio_de_mes(ahora: datetime) -> int:
    inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return max(1, int((ahora - inicio_mes).total_seconds()))


def consultar_uptime_mensual(servicio: str, *, ahora: datetime | None = None) -> float:
    """Uptime (0-100) del mes calendario en curso, promediando `up` sobre la
    ventana transcurrida desde el 1ro del mes hasta `ahora`."""
    if servicio not in SERVICIOS_VALIDOS:
        raise ServicioInvalido(f"servicio invalido: {servicio!r}")

    ahora = ahora or datetime.now(UTC)
    ventana_s = _segundos_desde_inicio_de_mes(ahora)
    consulta = f'avg_over_time(up{{job="{_JOB_PROMETHEUS}"}}[{ventana_s}s]) * 100'

    try:
        respuesta = httpx.get(
            f"{_url_base()}/api/v1/query",
            params={"query": consulta, "time": ahora.timestamp()},
            timeout=5.0,
        )
        respuesta.raise_for_status()
        cuerpo = respuesta.json()
    except httpx.HTTPError as exc:
        raise PrometheusInalcanzable(f"no se pudo consultar Prometheus: {exc}") from exc

    resultados = cuerpo.get("data", {}).get("result", [])
    if not resultados:
        # Sin muestras aun en el mes en curso (p. ej. Prometheus recien
        # arrancado) -- se asume 100%: no hay evidencia de indisponibilidad.
        return 100.0

    _, valor = resultados[0]["value"]
    return float(valor)
