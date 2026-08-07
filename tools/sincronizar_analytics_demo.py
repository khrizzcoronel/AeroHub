"""Sincronización manual DEMO del panel táctico (M7, pedido directo del
usuario 2026-08-05) -- NO es la ingesta medallion real de la Fase 2
(S2.1-S2.4, `docs/PLAN_IMPLEMENTACION_v3.0.md` §9). Llama a los 6
endpoints `/X/informes/compuesto` ya existentes y verificados sobre
MonetDB (S1.18) vía HTTP real (mismo patrón que el frontend, respeta la
independencia de módulos -- este script no importa domain/application de
ningún módulo de negocio) y escribe el snapshot resultante en la tabla
ClickHouse `ah_tactico_demo.compuesto_informe`.

Cuando la Fase 2 construya `ah_tactico` de verdad, este script y la
tabla demo se retiran -- documentado también en
`services/analytics_api/aerohub_analytics_api/infrastructure/__init__.py`.

Uso (dentro del contenedor gateway, que tiene acceso de red a MonetDB
Y a ClickHouse por nombre de servicio):
    uv run python tools/sincronizar_analytics_demo.py --tenant-codigo MEC
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, date, datetime, timedelta

import httpx
import pymonetdb
from aerohub_analytics_api.infrastructure import asegurar_esquema, reemplazar_filas_modulo
from aerohub_gateway.infrastructure import codificar_jwt

_ROL_TENANT_ADMIN = "role_tenant_admin"
_ROL_SRE = "role_sre"

# (modulo_codigo, ruta del endpoint compuesto, rol a usar, scopes)
_MODULOS = [
    ("vuelos", "/vuelos/informes/compuesto", _ROL_TENANT_ADMIN, ["vuelos:leer"]),
    ("puertas", "/puertas/informes/compuesto", _ROL_TENANT_ADMIN, ["puertas:leer"]),
    ("rampa", "/rampa/informes/compuesto", _ROL_TENANT_ADMIN, ["rampa:leer"]),
    ("billing", "/billing/informes/compuesto", _ROL_TENANT_ADMIN, ["billing:leer"]),
    ("tenants", "/tenants/informes/compuesto", _ROL_TENANT_ADMIN, ["tenants:administrar"]),
    # role_tenant_admin no tiene GRANT de motor sobre compliance.* (hallazgo
    # documentado desde S1.7/S1.19, CLAUDE.md) -- role_sre si lo tiene.
    ("compliance", "/compliance/informes/compuesto", _ROL_SRE, ["compliance:leer"]),
]


def _datos_canario(hostname: str, tenant_codigo: str) -> tuple[int, int]:
    conn = pymonetdb.connect(
        hostname=hostname, port=50000, database="aerohub", username="monetdb", password="aerohub"
    )
    cur = conn.cursor()
    cur.execute("SELECT id FROM tenants.tenant WHERE codigo = %s", (tenant_codigo,))
    fila_tenant = cur.fetchone()
    if fila_tenant is None:
        raise SystemExit(f"tenant {tenant_codigo!r} no encontrado -- correr seeds primero")
    tenant_id = fila_tenant[0]
    cur.execute(
        "SELECT id FROM tenants.usuario WHERE tenant_id = %s LIMIT 1", (tenant_id,)
    )
    fila_usuario = cur.fetchone()
    if fila_usuario is None:
        raise SystemExit(f"ningún usuario en el tenant {tenant_codigo!r}")
    usuario_id = fila_usuario[0]
    cur.close()
    conn.close()
    return tenant_id, usuario_id


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gateway-url", default="http://localhost:8000")
    parser.add_argument("--monetdb-host", default="localhost")
    parser.add_argument("--tenant-codigo", default="MEC")
    parser.add_argument("--dias", type=int, default=30)
    args = parser.parse_args()

    tenant_id, usuario_id = _datos_canario(args.monetdb_host, args.tenant_codigo)

    periodo_fin = date.today()
    periodo_inicio = periodo_fin - timedelta(days=args.dias)

    asegurar_esquema()

    ahora = datetime.now(UTC).replace(tzinfo=None)
    ok = 0
    for modulo_codigo, ruta, rol, scopes in _MODULOS:
        token = codificar_jwt(rol=rol, tenant_id=tenant_id, usuario_id=usuario_id, scopes=scopes)
        try:
            r = httpx.get(
                f"{args.gateway_url}{ruta}",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "periodo_inicio": periodo_inicio.isoformat(),
                    "periodo_fin": periodo_fin.isoformat(),
                },
                timeout=15.0,
            )
            r.raise_for_status()
        except httpx.HTTPStatusError as exc:
            print(f"  {modulo_codigo}: HTTP {exc.response.status_code} -- {exc.response.text}")
            continue
        except httpx.HTTPError as exc:
            print(f"  {modulo_codigo}: error de red -- {exc}")
            continue

        cuerpo = r.json()
        filas = [
            (
                g["clave"],
                int(g["subtotal"]),
                str(next(iter(g["metricas"].values()), "")) if g["metricas"] else "",
                int(cuerpo["total"]),
            )
            for g in cuerpo["grupos"]
        ]
        reemplazar_filas_modulo(modulo_codigo, filas=filas, calculado_en=ahora)
        print(f"  {modulo_codigo}: {len(filas)} grupo(s), total={cuerpo['total']}")
        ok += 1

    print(f"\nListo -- {ok}/{len(_MODULOS)} módulos sincronizados a ClickHouse.")
    if ok < len(_MODULOS):
        sys.exit(1)


if __name__ == "__main__":
    main()
