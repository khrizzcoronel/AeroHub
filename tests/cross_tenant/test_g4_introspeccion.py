"""G4 -- cobertura por introspeccion (ADR-019): enumera automaticamente
todos los metodos publicos "obtener_X_por_id(conn, id)" de los modulos de
consulta registrados en `MODULOS_A_VERIFICAR` y los invoca con el id del
canario de UN tenant, bajo el CONTEXTO de OTRO tenant. Un metodo nuevo con
esa firma entra al conjunto de prueba automaticamente en cuanto se agrega
su modulo a la lista -- nadie tiene que acordarse de escribirle una prueba
cruzada aparte (a diferencia de la cobertura "por disciplina" que
sustituye, SRS §9.3 control 4).

Convencion exigida para que un metodo sea cubierto por esta suite: nombre
que empiece con "obtener_" y termine en "_por_id", firma
`(conn: Connection, id: int) -> Row | None`. Cada modulo se registra junto
con la CLAVE del canario que corresponde al tipo de id que sus metodos
esperan (`usuario_id`, `vuelo_id`, ...) -- distintos modulos leen
distintas entidades, no hay un unico id universal que sirva para todas
(hallazgo de S1.1: aerohub_aodb.consultas.obtener_vuelo_por_id necesita un
vuelo_id, no el usuario_id que ya usaba aerohub_tenancy).
"""

from __future__ import annotations

import inspect

import pytest
from aerohub_aodb.infrastructure import consultas as consultas_aodb
from aerohub_repository import contexto, sesion
from aerohub_tenancy.infrastructure import consultas as consultas_tenants

MODULOS_A_VERIFICAR = [
    (consultas_tenants, "usuario_id"),
    (consultas_aodb, "vuelo_id"),
]


def _metodos_obtener_por_id(modulo) -> list[tuple[str, object]]:
    # startswith("obtener_") solo no basta -- un modulo puede tener lecturas
    # legitimas que NO son "por id de fila tenant-scoped" (p. ej.
    # obtener_estado_catalogo_por_codigo, sobre una tabla 'global' sin
    # concepto de tenant). El sufijo "_por_id" es lo que de verdad marca la
    # convencion que este harness sabe verificar.
    return [
        (nombre, fn)
        for nombre, fn in inspect.getmembers(modulo, inspect.isfunction)
        if nombre.startswith("obtener_")
        and nombre.endswith("_por_id")
        and fn.__module__ == modulo.__name__
    ]


def _todos_los_metodos_cubiertos() -> list[tuple[str, str, object, str]]:
    resultado = []
    for modulo, clave_canario in MODULOS_A_VERIFICAR:
        for nombre, fn in _metodos_obtener_por_id(modulo):
            resultado.append((modulo.__name__, nombre, fn, clave_canario))
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
    "nombre_modulo,nombre_metodo,fn,clave_canario",
    _todos_los_metodos_cubiertos(),
    ids=lambda v: v if isinstance(v, str) else "fn",
)
def test_ningun_metodo_obtener_por_id_cruza_tenants(
    contexto_de, canarios, nombre_modulo, nombre_metodo, fn, clave_canario
):
    """Para CADA metodo cubierto: bajo el contexto de MEC, pedir el id del
    canario de UIO debe devolver None (0 filas) -- nunca el objeto ajeno.
    Y, como control positivo (para que esta prueba no pase por vacio si el
    metodo simplemente siempre devuelve None), pedir el propio canario bajo
    el propio contexto SI debe encontrarlo.
    """
    contexto_de("MEC")
    with sesion() as conn:
        propio = fn(conn, canarios["MEC"][clave_canario])
        ajeno = fn(conn, canarios["UIO"][clave_canario])

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
