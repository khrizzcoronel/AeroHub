from sqlalchemy import delete, select, update
from sqlalchemy.engine import Connection

from .licencia import licencia
from .tablas import (
    api_key,
    intento_acceso,
    invitacion,
    sesion,
    tenant,
    token_acceso,
    usuario,
    usuario_rol,
)


def actualizar_tenant(
    conn: Connection, *, id: int, razon_social: str, plan_id: int, es_sandbox: bool
) -> None:
    conn.execute(
        update(tenant)
        .where(tenant.c.id == id)
        .values(razon_social=razon_social, plan_id=plan_id, es_sandbox=es_sandbox)
    )


def cambiar_estado_tenant(conn: Connection, *, id: int, estado_nuevo: str) -> None:
    conn.execute(update(tenant).where(tenant.c.id == id).values(estado=estado_nuevo))


def eliminar_tenant_y_relaciones_db(conn: Connection, tenant_id: int) -> bool:
    """Realiza la purga fisica permanente de un tenant y todas sus filas dependientes."""
    stmt_usuarios = select(usuario.c.id).where(usuario.c.tenant_id == tenant_id)
    usuario_ids = [row.id for row in conn.execute(stmt_usuarios).fetchall()]

    if usuario_ids:
        conn.execute(delete(usuario_rol).where(usuario_rol.c.usuario_id.in_(usuario_ids)))
        conn.execute(delete(token_acceso).where(token_acceso.c.usuario_id.in_(usuario_ids)))
        conn.execute(delete(sesion).where(sesion.c.usuario_id.in_(usuario_ids)))
        conn.execute(delete(intento_acceso).where(intento_acceso.c.usuario_id.in_(usuario_ids)))

    conn.execute(delete(invitacion).where(invitacion.c.tenant_id == tenant_id))
    conn.execute(delete(api_key).where(api_key.c.tenant_id == tenant_id))
    conn.execute(delete(licencia).where(licencia.c.tenant_id == tenant_id))

    if usuario_ids:
        conn.execute(delete(usuario).where(usuario.c.id.in_(usuario_ids)))

    res = conn.execute(delete(tenant).where(tenant.c.id == tenant_id))
    return res.rowcount > 0
