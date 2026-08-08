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
    # S1.16 -- antes sin vista en apps/web
    "M2": Modulo("M2", "Administración de FIDS", "/fids/pantallas"),
    "M3": Modulo("M3", "Gestión de Terminales y Puertas", "/puertas/tablero"),
    "M4": Modulo("M4", "Operaciones de Rampa", "/rampa/turnaround"),
    "M5": Modulo("M5", "Facturación e Ingresos", "/billing/facturas"),
    "M6": Modulo("M6", "Experiencia del Pasajero", None),
    "M7": Modulo("M7", "ETL y Analítica", None),
    "M8": Modulo("M8", "Observabilidad", None),
    "M9": Modulo("M9", "Centro de Cumplimiento", "/compliance/panel"),
}

# rol -> (modulos que puede operar, scopes que se emiten en su JWT)
_MAPEO: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    # Sin modulos operativos visibles: role_platform_admin no tiene
    # tenant propio (tenant_id NULL) ni scopes de negocio (vuelos:*,
    # billing:*, etc.) -- listarlo con acceso a M1-M9 producia un menu
    # que ofrecia pantallas que el rol no puede realmente operar
    # (403 "scope insuficiente" al primer clic). Su superficie real es
    # administrar tenants/API Keys, no operar el dia a dia de uno.
    "role_platform_admin": (
        frozenset(),
        frozenset(
            {
                "tenants:crear",
                "tenants:administrar",
                "api-keys:administrar",
                "usuarios:administrar",
                # Sprint S1.20 -- hallazgo empirico: publicar_changelog()
                # (gestionar_changelog.py) exige exactamente
                # role_platform_admin (_ROL_AUTORIZADO), pero este rol no
                # tenia ningun scope support:* -- POST /support/changelog
                # era inalcanzable por CUALQUIER rol del sistema desde que
                # se construyo en S1.8 (mismo patron que el hallazgo de
                # compliance:* en role_sre, S1.19). support:leer se agrega
                # junto a escribir para que quien publica tambien pueda
                # ver el listado resultante.
                "support:leer",
                "support:escribir",
            }
        ),
    ),
    "role_sre": (
        frozenset({"M7", "M8", "M9"}),
        frozenset(
            {
                "support:leer",
                "support:escribir",
                # Sprint S1.19 -- hallazgo empirico: _exigir_role_sre()
                # (gestionar_post_mortem.py, S1.7/ADR-009) exige
                # exactamente role_sre para post-mortems, pero este rol
                # no tenia ningun scope compliance:* -- los 2 endpoints
                # de post-mortem eran inalcanzables por el unico rol que
                # el dominio autoriza (mismo patron que el hallazgo de
                # fids:* en S1.16).
                "compliance:leer",
                "compliance:escribir",
            }
        ),
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
                # Sprint S1.20-iteracion (2026-08-06, D1(a) de
                # docs/diseno/PLAN_CORRECCION_MODULOS.md) -- hallazgo
                # empirico: role_tenant_admin tenia vuelos:escribir/
                # puertas:escribir/rampa:escribir/billing:escribir a
                # nivel de scope de aplicacion, pero el GRANT de motor
                # (db/ddl/monetdb/9*_grants_*.sql) nunca le dio INSERT
                # sobre ops.vuelo/ops.vuelo_estado/ops.asignacion_puerta
                # ni ningun privilegio de escritura sobre rampa.*/
                # billing.* -- la matriz de roles del Analisis v6.0
                # SS4.3.1 los reserva a role_operations_controller/
                # role_airline_coordinator/role_ramp_agent/
                # role_billing_officer (role_tenant_admin es
                # "configuracion", no "operacion"). El scope de
                # aplicacion pasaba el middleware y moria en el motor
                # con un 500 opaco (o 403 desde S1.20-iteracion, ver
                # services/gateway/main.py::_manejador_acceso_denegado_motor)
                # -- se retiran los 4 scopes para que la capa de
                # aplicacion deje de ofrecer una accion que el motor
                # nunca iba a aceptar.
                #
                # Sprint S1.16 -- hallazgo empirico: M2 ya estaba en el
                # conjunto de modulos de este rol (arriba), pero ningun
                # scope fids:* existia en NINGUN rol del sistema. Los 3
                # endpoints de escritura de S1.3 eran inalcanzables por
                # cualquier sesion humana desde que se construyeron
                # (apps/fids-player nunca lo necesito: no autentica como
                # rol humano, pega un JWT a mano).
                "fids:leer",
                "fids:administrar",
                "puertas:leer",
                "rampa:leer",
                "billing:leer",
                "passenger:leer",
                "compliance:leer",
                "compliance:escribir",
                "support:leer",
                "support:escribir",
                "api-keys:administrar",
                "usuarios:administrar",
            }
        ),
    ),
    "role_operations_controller": (
        frozenset({"M1", "M3", "M4"}),
        frozenset(
            {
                "vuelos:leer",
                "vuelos:escribir",
                "puertas:leer",
                "puertas:escribir",
                "rampa:leer",
                # 2026-08-08, hallazgo 1 de la auditoria de la capa
                # operativa: passenger:escribir no lo tenia NINGUN rol --
                # POST /passenger/tiempos-espera/recalcular (CU-O19,
                # RF-O17) era inalcanzable por cualquier sesion humana
                # desde S1.6 (cuarto caso de la familia fids:* S1.16 /
                # compliance:* S1.19 / support:* S1.20). Este rol es el
                # destinatario natural: 98_grants_billing.sql:19,54 ya le
                # otorga S,I,Up sobre billing.tiempo_espera_agregado
                # justamente porque el "Sistema" que ejecuta el recalculo
                # de CU-O19 corre bajo este rol -- el GRANT de motor
                # existia desde S1.6, solo faltaba el scope de aplicacion
                # que lo hiciera invocable (causa raiz A invertida).
                "passenger:leer",
                "passenger:escribir",
            }
        ),
    ),
    "role_airline_coordinator": (
        frozenset({"M1", "M6"}),
        frozenset(
            {
                "vuelos:leer",
                # 2026-08-08, hallazgo 2 de la auditoria de la capa
                # operativa: la matriz 4.3.1 le asigna U,S,I,Up sobre
                # `ops` ("solo sus itinerarios") y 96_grants_ops.sql:97-103
                # ya le otorga INSERT/UPDATE sobre ops.vuelo/vuelo_estado
                # desde S1.4 -- pero sin este scope el rol no podia crear
                # ni modificar un solo vuelo: motor abierto, aplicacion
                # cerrada. Su superficie usable era UNA vista de solo
                # lectura. Verificado antes de agregarlo que la ruta de
                # escritura completa esta aprovisionada (INSERT sobre
                # continuidad.journal_mutacion y compliance.log_auditoria),
                # asi que no hace falta ningun GRANT nuevo.
                #
                # NO se agrega puertas:* aunque el motor tambien le otorgue
                # asignacion_puerta: la columna `ops` de la matriz es de
                # granularidad de esquema, y la asignacion de modulos
                # (M1, M6) es la autoridad mas fina sobre lo que este rol
                # realmente opera -- M3 es de role_operations_controller.
                "vuelos:escribir",
                "passenger:leer",
            }
        ),
    ),
    "role_ramp_agent": (
        # M1 NO se agrega aqui a proposito -- vuelos:leer abajo es solo
        # para poblar el <select> del formulario de turnaround, no para
        # que este rol vea el workpanel completo de AODB en su menu
        # (mismo criterio que role_billing_officer, que tampoco gano M1).
        frozenset({"M4"}),
        frozenset(
            {
                "rampa:leer",
                "rampa:escribir",
                # 2026-08-08 -- hallazgo/pedido directo del usuario: el
                # formulario "Crear turnaround" pedia vuelo_llegada_id/
                # vuelo_salida_id a mano, sin ningun select (mismo patron
                # ya corregido para role_billing_officer + vuelos:leer en
                # Fase 5 de PLAN_CORRECCION_MODULOS.md). role_ramp_agent
                # es, junto a role_operations_controller (que ya tenia
                # vuelos:leer), el otro rol real que crea turnarounds.
                "vuelos:leer",
            }
        ),
    ),
    "role_billing_officer": (
        frozenset({"M5"}),
        frozenset(
            {
                "billing:leer",
                "billing:escribir",
                # Fase 5 de docs/diseno/PLAN_CORRECCION_MODULOS.md
                # (2026-08-07, item 15): quien concilia pax necesita ver
                # que vuelos existen para elegirlos de un selector real
                # en vez de pegar un id de 18 digitos a mano -- ops.vuelo
                # ya es de solo lectura para todos los roles con acceso
                # (SELECT), sin GRANT de motor nuevo.
                "vuelos:leer",
            }
        ),
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
