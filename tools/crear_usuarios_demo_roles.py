"""Script ad-hoc (pedido directo del usuario, 2026-08-05) -- crea un
usuario de demo por cada rol tenant-scoped en el tenant canario MEC,
para poder iniciar sesion y probar la aplicacion con cualquier rol sin
tener que pasar por el flujo de invitacion por correo. No forma parte
de ningun sprint ni de db/seeds/generate.py -- es una utilidad de
sesion, se puede volver a correr sin duplicar (idempotente por email).
"""

from __future__ import annotations

import argparse

import pymonetdb
from aerohub_kernel import generar_id, hash_credencial

# tenants.rol codigo=10..16, alcance='tenant' (db/ddl/monetdb/02_tenants.sql).
# role_tenant_admin se omite: ya existe como canario@mec.aerohub.test
# desde db/seeds/generate.py.
ROLES_TENANT_SCOPED = [
    ("role_operations_controller", "controlador"),
    ("role_airline_coordinator", "aerolinea"),
    ("role_ramp_agent", "rampa"),
    ("role_billing_officer", "facturacion"),
    ("role_tenant_analyst", "analista"),
    ("role_regulatory_auditor", "auditor"),
]

PASSWORD_DEMO = "aerohub-demo-2026"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hostname", default="localhost")
    parser.add_argument("--port", type=int, default=50000)
    parser.add_argument("--database", default="aerohub")
    parser.add_argument("--username", default="monetdb")
    parser.add_argument("--password", default="aerohub")
    parser.add_argument("--tenant-codigo", default="MEC")
    args = parser.parse_args()

    conn = pymonetdb.connect(
        hostname=args.hostname,
        port=args.port,
        database=args.database,
        username=args.username,
        password=args.password,
    )
    cur = conn.cursor()

    cur.execute("SELECT id, razon_social FROM tenants.tenant WHERE codigo = %s", (args.tenant_codigo,))
    fila_tenant = cur.fetchone()
    if fila_tenant is None:
        raise SystemExit(f"tenant {args.tenant_codigo!r} no encontrado -- correr seeds primero")
    tenant_id, razon_social = fila_tenant

    cur.execute(
        "SELECT id FROM tenants.usuario WHERE tenant_id = %s AND email = %s",
        (tenant_id, f"canario@{args.tenant_codigo.lower()}.aerohub.test"),
    )
    fila_otorgante = cur.fetchone()
    if fila_otorgante is None:
        raise SystemExit("usuario canario (role_tenant_admin) no encontrado -- correr seeds primero")
    otorgado_por = fila_otorgante[0]

    creados = []
    for rol_codigo, slug in ROLES_TENANT_SCOPED:
        cur.execute("SELECT id FROM tenants.rol WHERE codigo = %s", (rol_codigo,))
        rol_id = cur.fetchone()[0]

        email = f"{slug}@{args.tenant_codigo.lower()}.aerohub.test"
        cur.execute(
            "SELECT id FROM tenants.usuario WHERE tenant_id = %s AND email = %s",
            (tenant_id, email),
        )
        fila = cur.fetchone()
        if fila is not None:
            print(f"  {email} ya existe (id={fila[0]}), se reutiliza")
            creados.append((rol_codigo, email, fila[0]))
            continue

        usuario_id = generar_id()
        cur.execute(
            "INSERT INTO tenants.usuario "
            "(id, tenant_id, email, hash_credencial, nombre, estado, "
            "debe_cambiar_password, email_verificado_en) "
            "VALUES (%s, %s, %s, %s, %s, 'activo', FALSE, NOW())",
            (
                usuario_id,
                tenant_id,
                email,
                hash_credencial(PASSWORD_DEMO),
                f"Demo {rol_codigo}",
            ),
        )
        cur.execute(
            "INSERT INTO tenants.usuario_rol (usuario_id, rol_id, otorgado_por, otorgado_en) "
            "VALUES (%s, %s, %s, NOW())",
            (usuario_id, rol_id, otorgado_por),
        )
        print(f"  {email} creado (id={usuario_id}, rol={rol_codigo})")
        creados.append((rol_codigo, email, usuario_id))

    conn.commit()
    cur.close()
    conn.close()

    print(f"\nListo -- {len(creados)} usuarios de demo en {razon_social} ({args.tenant_codigo}).")


if __name__ == "__main__":
    main()
