"""Monitor de senal de pantallas FIDS (Sprint S1.3, Plan §8.3, RF-O07,
RNF-R04: "pantalla sin senal genera alerta en < 60 s").

Escanea TODAS las pantallas de TODOS los tenants -- es un proceso de
PLATAFORMA, sin tenant propio, igual que CU-O18 (aprovisionar_tenant) o la
autenticacion de API Key (S1.2): corre bajo `alcance_global()` (ADR-019
G3), auditado como excepcion nominal, no como bypass silencioso.

El intervalo entre ciclos (no el umbral) es lo que determina la latencia
de deteccion real -- con umbral=60s e intervalo=10s, una pantalla que deja
de emitir se detecta, en el peor caso, a los 70s de su ultimo heartbeat.
Para que RNF-R04 (< 60s) se cumpla con margen, el intervalo debe ser
sensiblemente menor al umbral (ver services/gateway/main.py, donde se fija
el intervalo real del ciclo periodico).
"""

from __future__ import annotations

from dataclasses import dataclass

from aerohub_kernel import ahora_utc

from ..domain import PantallaFids
from ..infrastructure import (
    alcance_global,
    listar_pantallas_para_monitoreo,
    marcar_pantalla_sin_senal,
    sesion,
)

UMBRAL_SEGUNDOS_POR_DEFECTO = 60
_MOTIVO_ALCANCE_GLOBAL = "monitor_senal_fids"
_ROL_MONITOR = "role_platform_admin"


@dataclass(frozen=True, slots=True)
class ResultadoCicloMonitoreo:
    evaluadas: int
    marcadas_sin_senal: tuple[int, ...]


def ejecutar_ciclo_monitoreo(
    *, umbral_segundos: int = UMBRAL_SEGUNDOS_POR_DEFECTO
) -> ResultadoCicloMonitoreo:
    ahora = ahora_utc()
    marcadas: list[int] = []
    with alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL_MONITOR), sesion() as conn:
        filas = listar_pantallas_para_monitoreo(conn)
        for fila in filas:
            if fila.estado == "mantenimiento":
                continue
            pantalla = PantallaFids(
                id=fila.id,
                tenant_id=fila.tenant_id,
                terminal_id=fila.terminal_id,
                codigo=fila.codigo,
                plantilla_id=fila.plantilla_id,
                estado=fila.estado,
                ultima_senal_en=fila.ultima_senal_en,
            )
            if pantalla.esta_sin_senal(ahora, umbral_segundos) and fila.estado != "sin_senal":
                marcar_pantalla_sin_senal(conn, id=fila.id)
                marcadas.append(fila.id)
    return ResultadoCicloMonitoreo(evaluadas=len(filas), marcadas_sin_senal=tuple(marcadas))
