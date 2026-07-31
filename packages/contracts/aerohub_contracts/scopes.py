"""Verificacion de scope de la peticion autenticada (Sprint S1.2, Plan §8.2,
PN-07: "JWT expirado o con scope insuficiente -> HTTP 401/403, sin fuga de
informacion").

Vive en aerohub_contracts, no en aerohub_gateway ni en ningun modulo de
negocio especifico: cada api/ de cada modulo (aerohub_aodb, aerohub_tenancy,
...) necesita gatear sus propios endpoints por scope, pero el contrato de
independencia de modulos (.importlinter) prohibe que un modulo importe a
otro -- aerohub_contracts es el unico paquete transversal pensado
explicitamente para esto (ADR-017 §5.4: "la comunicacion inter-modulo es
por puerto o evento declarado en aerohub_contracts").

Lee `request.state.scopes`, poblado por
`aerohub_gateway.api.middleware.AutenticacionJWTMiddleware` -- un
acoplamiento por CONVENCION DE NOMBRE del atributo de `Request.state`, no
por import de Python, que es exactamente el patron que el ADR exige.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import HTTPException, Request


def requiere_scope(scope: str) -> Callable[[Request], None]:
    """Fabrica de dependencia FastAPI: `Depends(requiere_scope("vuelos:leer"))`.

    403, no 401 -- la peticion SI esta autenticada (si no lo estuviera, el
    middleware ya la habria rechazado con 401 antes de llegar aqui); lo que
    falta es autorizacion para esta operacion puntual. El detalle no repite
    los scopes que la identidad SI tiene, solo el que falto -- PN-07 exige
    "sin fuga de informacion".
    """

    def _verificar(request: Request) -> None:
        scopes_de_la_peticion: frozenset[str] = getattr(request.state, "scopes", frozenset())
        if scope not in scopes_de_la_peticion:
            raise HTTPException(
                status_code=403, detail=f"scope insuficiente: se requiere {scope!r}"
            )

    return _verificar
