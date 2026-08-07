"""Endpoints HTTP de aerohub_analytics_api (M7, panel táctico -- demo
mínima sobre ClickHouse, ver `infrastructure/__init__.py`). Solo traduce
HTTP <-> `application/`, ninguna regla de negocio vive aquí (SRS §6.4)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..application import consultar_informe_tactico
from ..domain import ModuloTacticoInvalido

router = APIRouter(prefix="/analytics", tags=["analytics-tactico"])

# Cada módulo tactico requiere el mismo scope de lectura que su
# contraparte operativa en MonetDB (S1.18) -- ver un compuesto táctico
# de vuelos exige lo mismo que ver el operativo de vuelos.
_SCOPE_POR_MODULO = {
    "vuelos": "vuelos:leer",
    "puertas": "puertas:leer",
    "rampa": "rampa:leer",
    "billing": "billing:leer",
    "tenants": "tenants:administrar",
    "compliance": "compliance:leer",
}


class GrupoTacticoResponse(BaseModel):
    clave: str
    subtotal: int
    metrica_principal: str | None


class InformeTacticoResponse(BaseModel):
    modulo_codigo: str
    grupos: list[GrupoTacticoResponse]
    total_general: int
    calculado_en: str | None


@router.get("/tactico/{modulo_codigo}", response_model=InformeTacticoResponse)
def obtener_informe_tactico_endpoint(
    modulo_codigo: str, request: Request
) -> InformeTacticoResponse:
    scope_requerido = _SCOPE_POR_MODULO.get(modulo_codigo)
    if scope_requerido is None:
        raise HTTPException(
            status_code=404, detail=f"módulo táctico desconocido: {modulo_codigo!r}"
        )
    scopes_de_la_peticion: frozenset[str] = getattr(request.state, "scopes", frozenset())
    if scope_requerido not in scopes_de_la_peticion:
        raise HTTPException(
            status_code=403, detail=f"scope insuficiente: se requiere {scope_requerido!r}"
        )

    try:
        informe = consultar_informe_tactico(modulo_codigo)
    except ModuloTacticoInvalido as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return InformeTacticoResponse(
        modulo_codigo=informe.modulo_codigo,
        grupos=[
            GrupoTacticoResponse(
                clave=g.clave, subtotal=g.subtotal, metrica_principal=g.metrica_principal
            )
            for g in informe.grupos
        ],
        total_general=informe.total_general,
        calculado_en=informe.calculado_en.isoformat() if informe.calculado_en else None,
    )
