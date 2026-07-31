"""Generador de identificadores BIGINT (estilo Snowflake), thread-safe.

Por que existe: SDD-DATA-001 §4 exige `id` como BIGINT "generado por
secuencia, nunca reutilizado". La implementacion obvia -- `GENERATED ALWAYS
AS IDENTITY` de MonetDB -- resulto incompatible con el modelo de privilegios
por rol de este proyecto: MonetDB deniega el acceso a la secuencia interna
de una columna IDENTITY (y a `NEXT VALUE FOR` sobre una secuencia explicita)
cuando la sesion opera bajo un rol activado con `SET ROLE`, incluso si ese
rol tiene privilegio pleno sobre la tabla y la sesion usa el mismo usuario
de conexion en ambos casos. Verificado empiricamente en S0.2 contra el
contenedor real (ver docs/runbooks/monetdb.md): un `INSERT` con `id`
explicito funciona bajo cualquier rol; el mismo `INSERT` dejando que el
motor genere el valor via IDENTITY o `NEXT VALUE FOR` falla con
"access denied ... to schema 'sys'" (o al esquema de la secuencia), para
CUALQUIER rol probado, incluido el mas privilegiado. Como `packages/repository`
siempre opera bajo un rol de negocio activado por sesion (P2, ADR-019), la
generacion de `id` debe ocurrir en la aplicacion, nunca en el motor.

Estructura del identificador (63 bits utiles, siempre positivo):

    | 41 bits: milisegundos desde EPOCA_AEROHUB | 10 bits: nodo | 12 bits: secuencia |

- 41 bits de milisegundos cubren ~69 anios desde EPOCA_AEROHUB sin desbordar.
- 10 bits de nodo (0-1023) permiten escalar a multiples instancias de la
  capa de repositorio sin colision, configurable via `AEROHUB_NODE_ID`.
- 12 bits de secuencia (0-4095) distinguen IDs generados en el mismo
  milisegundo por el mismo nodo; si se agota, el generador espera al
  milisegundo siguiente en vez de reiniciar la secuencia (evita reuso).

No es un `lsn` de orden total estricto multi-nodo: con un unico nodo (S0.2)
el orden de generacion coincide con el orden temporal real; con varios nodos
el orden es aproximado (por reloj), no garantizado -- aceptable para `id`
de fila, insuficiente si `continuidad.journal_mutacion.lsn` alguna vez
necesita orden total estricto entre multiples escritores concurrentes (seria
el momento de revisar esta decision, no antes: el journal es de escritor
unico mientras la capa de repositorio sea el unico emisor de SQL, P1).
"""

from __future__ import annotations

import threading
import time

EPOCA_AEROHUB_MS = 1_767_225_600_000  # 2026-01-01T00:00:00Z, en milisegundos

_BITS_NODO = 10
_BITS_SECUENCIA = 12
_MAX_NODO = (1 << _BITS_NODO) - 1
_MAX_SECUENCIA = (1 << _BITS_SECUENCIA) - 1


class GeneradorId:
    """Instanciar una vez por proceso (o por nodo, si hay varios). Thread-safe."""

    def __init__(self, nodo_id: int = 0) -> None:
        if not (0 <= nodo_id <= _MAX_NODO):
            raise ValueError(f"nodo_id debe estar entre 0 y {_MAX_NODO}: {nodo_id!r}")
        self._nodo_id = nodo_id
        self._lock = threading.Lock()
        self._ultimo_ms = -1
        self._secuencia = 0

    def siguiente(self) -> int:
        with self._lock:
            ahora_ms = self._ahora_ms()

            if ahora_ms < self._ultimo_ms:
                # Reloj retrocedio (ajuste NTP, etc.): esperar a alcanzar el
                # ultimo milisegundo conocido antes de continuar, para
                # preservar "nunca reutilizado".
                ahora_ms = self._esperar_hasta(self._ultimo_ms)

            if ahora_ms == self._ultimo_ms:
                self._secuencia = (self._secuencia + 1) & _MAX_SECUENCIA
                if self._secuencia == 0:
                    ahora_ms = self._esperar_hasta(ahora_ms + 1)
            else:
                self._secuencia = 0

            self._ultimo_ms = ahora_ms

            delta_ms = ahora_ms - EPOCA_AEROHUB_MS
            return (
                (delta_ms << (_BITS_NODO + _BITS_SECUENCIA))
                | (self._nodo_id << _BITS_SECUENCIA)
                | self._secuencia
            )

    @staticmethod
    def _ahora_ms() -> int:
        return time.time_ns() // 1_000_000

    def _esperar_hasta(self, objetivo_ms: int) -> int:
        ahora_ms = self._ahora_ms()
        while ahora_ms < objetivo_ms:
            time.sleep(0.0005)
            ahora_ms = self._ahora_ms()
        return ahora_ms


_generador_por_defecto = GeneradorId()


def generar_id() -> int:
    """Atajo sobre un generador de proceso unico con nodo_id=0.

    Para desplegar mas de una instancia de un mismo servicio en paralelo,
    instanciar `GeneradorId(nodo_id=N)` explicitamente por instancia en vez
    de usar este atajo (evita colisiones entre instancias).
    """
    return _generador_por_defecto.siguiente()
