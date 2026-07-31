import aerohub_repository.guard as guard_module
import pytest
from aerohub_repository import contexto
from aerohub_repository.guard import (
    AlcanceNoDeclarado,
    TenantScopeViolation,
    alcance_de,
    registrar_alcance,
    verificar_sentencia,
)
from sqlalchemy import (
    BigInteger,
    Column,
    MetaData,
    String,
    Table,
    bindparam,
    delete,
    insert,
    select,
    update,
)

md = MetaData()

usuario = Table(
    "usuario",
    md,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("email", String),
    schema="tenants",
)

vuelo = Table(
    "vuelo",
    md,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    schema="ops",
)

turnaround = Table(
    "turnaround",
    md,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("vuelo_id", BigInteger),
    schema="rampa",
)

pais = Table(
    "pais",
    md,
    Column("id", BigInteger, primary_key=True),
    Column("nombre", String),
    schema="catalogo",
)

@pytest.fixture(scope="module", autouse=True)
def _registro_g1_aislado():
    """guard._registro es un diccionario global de proceso -- registrar
    aqui a nivel de modulo (como se hacia antes) contaminaba
    permanentemente el registro real para el resto de la suite (hallazgo
    de S0.2: tests/integration/test_g1_conformidad.py, corrido junto con
    esta suite, encontraba 'ops.vuelo' registrada como 'tenant' sin la
    tabla existir todavia en el motor -- exactamente esta fuga). Se guarda
    una copia y se restaura al terminar el modulo.
    """
    original = dict(guard_module._registro)
    registrar_alcance("tenants", "usuario", "tenant")
    registrar_alcance("ops", "vuelo", "tenant")
    registrar_alcance("rampa", "turnaround", "tenant")
    registrar_alcance("catalogo", "pais", "global")
    yield
    guard_module._registro.clear()
    guard_module._registro.update(original)


@pytest.fixture(autouse=True)
def _tenant_42():
    token = contexto._establecer_tenant_id(42)
    yield
    contexto._tenant_id.reset(token)


def test_g1_tabla_no_declarada_lanza():
    with pytest.raises(AlcanceNoDeclarado):
        alcance_de("ops", "tabla_inexistente")


def test_insert_con_tenant_id_correcto_pasa():
    stmt = insert(usuario).values(id=1, tenant_id=42, email="a@b.com")
    verificar_sentencia(stmt, (), {})  # no lanza


def test_insert_con_tenant_id_de_otro_tenant_se_rechaza():
    stmt = insert(usuario).values(id=1, tenant_id=999, email="a@b.com")
    with pytest.raises(TenantScopeViolation):
        verificar_sentencia(stmt, (), {})


def test_insert_sin_tenant_id_se_rechaza():
    stmt = insert(usuario).values(id=1, email="a@b.com")
    with pytest.raises(TenantScopeViolation):
        verificar_sentencia(stmt, (), {})


def test_insert_via_params_de_execute_tambien_se_verifica():
    stmt = insert(usuario)
    verificar_sentencia(stmt, (), {"id": 1, "tenant_id": 42, "email": "a@b.com"})
    with pytest.raises(TenantScopeViolation):
        verificar_sentencia(stmt, (), {"id": 1, "tenant_id": 999, "email": "a@b.com"})


def test_insert_executemany_exige_tenant_id_correcto_en_todas_las_filas():
    stmt = insert(usuario)
    filas_ok = [{"id": 1, "tenant_id": 42}, {"id": 2, "tenant_id": 42}]
    verificar_sentencia(stmt, filas_ok, {})
    filas_mixtas = [{"id": 1, "tenant_id": 42}, {"id": 2, "tenant_id": 999}]
    with pytest.raises(TenantScopeViolation):
        verificar_sentencia(stmt, filas_mixtas, {})


def test_select_con_filtro_de_tenant_correcto_pasa():
    stmt = select(usuario).where(usuario.c.tenant_id == 42)
    verificar_sentencia(stmt, (), {})


def test_select_con_filtro_de_otro_tenant_se_rechaza():
    stmt = select(usuario).where(usuario.c.tenant_id == 999)
    with pytest.raises(TenantScopeViolation):
        verificar_sentencia(stmt, (), {})


def test_select_sin_where_alguno_se_rechaza():
    stmt = select(usuario)
    with pytest.raises(TenantScopeViolation):
        verificar_sentencia(stmt, (), {})


def test_select_con_where_de_otra_columna_pero_sin_tenant_se_rechaza():
    stmt = select(usuario).where(usuario.c.email == "a@b.com")
    with pytest.raises(TenantScopeViolation):
        verificar_sentencia(stmt, (), {})


def test_select_con_bindparam_nombrado_resuelto_en_execute_time_pasa():
    stmt = select(usuario).where(usuario.c.tenant_id == bindparam("tid"))
    verificar_sentencia(stmt, (), {"tid": 42})
    with pytest.raises(TenantScopeViolation):
        verificar_sentencia(stmt, (), {"tid": 999})


def test_select_sobre_tabla_global_no_exige_filtro_de_tenant():
    stmt = select(pais)
    verificar_sentencia(stmt, (), {})  # catalogo.pais es 'global', no lanza


def test_update_con_filtro_de_tenant_pasa():
    stmt = (
        update(usuario)
        .where(usuario.c.tenant_id == 42, usuario.c.id == 1)
        .values(email="x@y.com")
    )
    verificar_sentencia(stmt, (), {})


def test_update_sin_filtro_de_tenant_se_rechaza():
    stmt = update(usuario).where(usuario.c.id == 1).values(email="x@y.com")
    with pytest.raises(TenantScopeViolation):
        verificar_sentencia(stmt, (), {})


def test_delete_con_filtro_de_tenant_pasa():
    stmt = delete(usuario).where(usuario.c.tenant_id == 42)
    verificar_sentencia(stmt, (), {})


def test_delete_sin_filtro_de_tenant_se_rechaza():
    stmt = delete(usuario).where(usuario.c.id == 1)
    with pytest.raises(TenantScopeViolation):
        verificar_sentencia(stmt, (), {})


def test_join_de_dos_tablas_tenant_exige_filtro_en_ambas():
    # Caso adversarial: un JOIN correlaciona vuelo.tenant_id con
    # turnaround.tenant_id entre si, pero eso NO es un filtro contra el
    # tenant del contexto -- ninguna de las dos declara su propio filtro
    # de contexto, asi que debe rechazarse.
    stmt = (
        select(vuelo, turnaround)
        .select_from(vuelo.join(turnaround, turnaround.c.vuelo_id == vuelo.c.id))
        .where(vuelo.c.tenant_id == turnaround.c.tenant_id)
    )
    with pytest.raises(TenantScopeViolation):
        verificar_sentencia(stmt, (), {})


def test_join_de_dos_tablas_tenant_con_ambos_filtros_pasa():
    stmt = (
        select(vuelo, turnaround)
        .select_from(vuelo.join(turnaround, turnaround.c.vuelo_id == vuelo.c.id))
        .where(vuelo.c.tenant_id == 42, turnaround.c.tenant_id == 42)
    )
    verificar_sentencia(stmt, (), {})


def test_join_no_confunde_el_tenant_id_de_una_tabla_con_el_de_otra():
    # Solo turnaround.tenant_id tiene el filtro; vuelo.tenant_id no --
    # el guardian no debe aceptar el filtro de turnaround como si cubriera
    # tambien a vuelo (columna con el mismo nombre, tabla distinta).
    stmt = (
        select(vuelo, turnaround)
        .select_from(vuelo.join(turnaround, turnaround.c.vuelo_id == vuelo.c.id))
        .where(turnaround.c.tenant_id == 42)
    )
    with pytest.raises(TenantScopeViolation):
        verificar_sentencia(stmt, (), {})


def test_sql_crudo_texto_se_rechaza_siempre():
    from sqlalchemy import text

    with pytest.raises(TenantScopeViolation):
        verificar_sentencia(text("SELECT 1"), (), {})


def test_alcance_global_omite_la_verificacion():
    stmt = select(usuario)  # sin filtro -- normalmente se rechazaria
    with contexto.alcance_global(motivo="extraccion_bronce", rol="role_elt_reader"):
        verificar_sentencia(stmt, (), {})  # no lanza
