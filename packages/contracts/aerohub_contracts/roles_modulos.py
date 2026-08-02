"""Mapeo rol -> (modulos operables, scopes, ruta de frontend) (Sprint
S1.10, research.md Decision 4).

Vive aqui, no en una tabla de `tenants`, por la misma razon estructural
que `scopes.requiere_scope`: lo consumen DOS paquetes que el contrato de
independencia de modulos (.importlinter) no deja importarse entre si --
`aerohub_tenancy` para resolver los scopes del JWT y los modulos visibles
del perfil de acceso (`GET /auth/yo`), `aerohub_gateway` para razonar
sobre la identidad autenticada. Es dato de arquitectura de permisos, no
un valor operativo que un tenant configure: se versiona en codigo, igual
que los GRANT de `db/ddl/monetdb/92_grants_tenants.sql`.

Los 16 roles y sus 2 alcances ('plataforma'/'tenant') son los mismos
sembrados en `db/ddl/monetdb/02_tenants.sql`. Los 9 modulos M1-M9 son los
de `db/ddl/monetdb/01_catalogo.sql`. `ruta` es `None` para un modulo que
todavia no tiene vista en `apps/web` (M2 vive en `apps/fids-player`, M7/M8
no tienen panel Angular propio a la fecha de este sprint).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Modulo:
    codigo: str
    nombre: str
    ruta: str | None


MODULOS: dict[str, Modulo] = {
    "M1": Modulo("M1", "AODB", "/vuelos/tiempo-real"),
    "M2": Modulo("M2", "FIDS Management", None),
    "M3": Modulo("M3", "Terminal & Gate Manager", "/puertas/tablero"),
    "M4": Modulo("M4", "Ground Operations", "/rampa/turnaround"),
    "M5": Modulo("M5", "Revenue & Billing", "/billing/facturas"),
    "M6": Modulo("M6", "Passenger Experience", None),
    "M7": Modulo("M7", "ETL & Analytics", None),
    "M8": Modulo("M8", "Observability", None),
    "M9": Modulo("M9", "Compliance Hub", None),
}

# rol -> (modulos que puede operar, scopes que se emiten en su JWT)
_MAPEO: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    "role_platform_admin": (
        frozenset(MODULOS),
        frozenset(
            {
                "tenants:crear",
                "tenants:administrar",
                "api-keys:administrar",
            }
        ),
    ),
    "role_sre": (
        frozenset({"M7", "M8"}),
        frozenset({"support:leer", "support:escribir"}),
    ),
    "role_data_engineer": (
        frozenset({"M7"}),
        frozenset(),
    ),
    "role_ml_engineer": (
        frozenset({"M7"}),
        frozenset(),
    ),
    "role_implementation": (
        frozenset({"M1", "M3", "M4", "M5", "M6"}),
        frozenset({"tenants:crear"}),
    ),
    "role_support": (
        frozenset({"M8", "M9"}),
        frozenset({"support:leer", "support:escribir"}),
    ),
    "role_business_viewer": (
        frozenset({"M5", "M6", "M7"}),
        frozenset({"billing:leer"}),
    ),
    "role_people_viewer": (
        frozenset(),
        frozenset(),
    ),
    "role_elt_reader": (
        frozenset({"M7"}),
        frozenset(),
    ),
    "role_tenant_admin": (
        frozenset(MODULOS) - {"M7", "M8"},
        frozenset(
            {
                "vuelos:leer",
                "vuelos:escribir",
                "puertas:leer",
                "puertas:escribir",
                "rampa:leer",
                "rampa:escribir",
                "billing:leer",
                "billing:escribir",
                "passenger:leer",
                "compliance:leer",
                "compliance:escribir",
                "support:leer",
                "support:escribir",
                "api-keys:administrar",
            }
        ),
    ),
    "role_operations_controller": (
        frozenset({"M1", "M3", "M4"}),
        frozenset(
            {"vuelos:leer", "vuelos:escribir", "puertas:leer", "puertas:escribir", "rampa:leer"}
        ),
    ),
    "role_airline_coordinator": (
        frozenset({"M1", "M6"}),
        frozenset({"vuelos:leer", "passenger:leer"}),
    ),
    "role_ramp_agent": (
        frozenset({"M4"}),
        frozenset({"rampa:leer", "rampa:escribir"}),
    ),
    "role_billing_officer": (
        frozenset({"M5"}),
        frozenset({"billing:leer", "billing:escribir"}),
    ),
    "role_tenant_analyst": (
        frozenset({"M1", "M3", "M4", "M5", "M6"}),
        frozenset(
            {"vuelos:leer", "puertas:leer", "rampa:leer", "billing:leer", "passenger:leer"}
        ),
    ),
    "role_regulatory_auditor": (
        frozenset({"M9"}),
        frozenset({"compliance:leer"}),
    ),
}


def modulos_del_rol(rol_codigo: str) -> frozenset[str]:
    return _MAPEO.get(rol_codigo, (frozenset(), frozenset()))[0]


def scopes_del_rol(rol_codigo: str) -> frozenset[str]:
    return _MAPEO.get(rol_codigo, (frozenset(), frozenset()))[1]
