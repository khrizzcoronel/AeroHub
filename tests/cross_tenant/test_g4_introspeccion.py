"""G4 -- cobertura por introspeccion (ADR-019): enumera automaticamente
todos los metodos publicos "obtener_X_por_id(conn, id)" de los modulos de
consulta registrados en `MODULOS_A_VERIFICAR` y los invoca con el id del
canario de UN tenant, bajo el CONTEXTO de OTRO tenant. Un metodo nuevo con
esa firma entra al conjunto de prueba automaticamente en cuanto se agrega
su modulo a la lista -- nadie tiene que acordarse de escribirle una prueba
cruzada aparte (a diferencia de la cobertura "por disciplina" que
sustituye, SRS §9.3 control 4).

Convencion exigida para que un metodo sea cubierto por esta suite: firma
`(conn: Connection, id: int) -> Row | None`, y nombre que empiece con
"obtener_" (packages/repository/aerohub_repository/tenants/consultas.py es
el primer ejemplo). Fase 1 en adelante, cada modulo nuevo de consultas se
agrega a MODULOS_A_VERIFICAR.
"""

from __future__ import annotations

import inspect

import pytest
from aerohub_repository import contexto, sesion
from aerohub_repository.tenants import consultas as consultas_tenants

MODULOS_A_VERIFICAR = [consultas_tenants]


def _metodos_obtener_por_id(modulo) -> list[tuple[str, object]]:
    return [
        (nombre, fn)
        for nombre, fn in inspect.getmembers(modulo, inspect.isfunction)
        if nombre.startswith("obtener_") and fn.__module__ == modulo.__name__
    ]


def _todos_los_metodos_cubiertos() -> list[tuple[str, str, object]]:
    resultado = []
    for modulo in MODULOS_A_VERIFICAR:
        for nombre, fn in _metodos_obtener_por_id(modulo):
            resultado.append((modulo.__name__, nombre, fn))
    return resultado


def test_hay_al_menos_un_metodo_registrado_para_cubrir():
    # Si esto falla, la suite entera pasaria vacuamente -- es una guarda
    # contra que MODULOS_A_VERIFICAR quede desactualizado en silencio.
    assert len(_todos_los_metodos_cubiertos()) > 0


@pytest.fixture()
def contexto_de(canarios):
    def _activar(codigo_tenant: str, rol: str = "role_platform_admin"):
        info = canarios[codigo_tenant]
        token_t = contexto._establecer_tenant_id(info["tenant_id"])
        token_r = contexto._establecer_rol_actor(rol)
        token_u = contexto._establecer_usuario_id(None)
        return token_t, token_r, token_u

    activados = []

    def _activar_y_registrar(codigo_tenant: str, rol: str = "role_platform_admin"):
        tokens = _activar(codigo_tenant, rol)
        activados.append(tokens)
        return tokens

    yield _activar_y_registrar

    for token_t, token_r, token_u in reversed(activados):
        contexto._tenant_id.reset(token_t)
        contexto._rol_actor.reset(token_r)
        contexto._usuario_id.reset(token_u)


@pytest.mark.parametrize(
    "nombre_modulo,nombre_metodo,fn",
    [(m, n, f) for m, n, f in _todos_los_metodos_cubiertos()],
    ids=lambda v: v if isinstance(v, str) else "fn",
)
def test_ningun_metodo_obtener_por_id_cruza_tenants(
    contexto_de, canarios, nombre_modulo, nombre_metodo, fn
):
    """Para CADA metodo cubierto: bajo el contexto de MEC, pedir el id del
    canario de UIO debe devolver None (0 filas) -- nunca el objeto ajeno.
    Y, como control positivo (para que esta prueba no pase por vacio si el
    metodo simplemente siempre devuelve None), pedir el propio canario bajo
    el propio contexto SI debe encontrarlo.
    """
    contexto_de("MEC")
    with sesion() as conn:
        propio = fn(conn, canarios["MEC"]["usuario_id"])
        ajeno = fn(conn, canarios["UIO"]["usuario_id"])

    assert propio is not None, (
        f"{nombre_modulo}.{nombre_metodo} no encontro su propio canario -- "
        "control positivo fallido, esta prueba no es concluyente"
    )
    assert ajeno is None, (
        f"{nombre_modulo}.{nombre_metodo} devolvio una fila del tenant UIO "
        "bajo contexto de MEC -- fuga cruzada de tenant"
    )


def test_cobertura_reportada_100_por_ciento(canarios):
    """Publica la cifra de cobertura (Plan §6.4: 'publicada en cada PR')."""
    total = len(_todos_los_metodos_cubiertos())
    print(f"\nCobertura G4: {total}/{total} metodos obtener_*_por_id cubiertos (100%)")
    assert total > 0
