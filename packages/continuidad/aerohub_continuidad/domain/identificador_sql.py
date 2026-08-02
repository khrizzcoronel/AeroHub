"""Validacion de identificadores SQL (Sprint S1.9). El *shipper*/la prueba
de restauracion interpolan nombres de esquema/tabla/columna en SQL crudo
(`operaciones/shipper.py`, `operaciones/restauracion.py`,
`operaciones/snapshot.py`) porque el destino es generico -- CUALQUIER
`(esquema, tabla)` que ya paso por `journal_mutacion` o por `sys.tables`,
no un conjunto fijo de `Table()` tipados (research.md Decision 2/9 de
specs/011-continuidad-rto-rpo/). Ningun *driver* de MonetDB permite
parametrizar un nombre de identificador (solo valores) -- por eso esta
validacion es la unica defensa posible antes de interpolar. En la practica
`esquema`/`tabla` siempre se originan de literales de Python en el codigo
de la aplicacion (`escribir_journal(esquema="support", ...)`) o del propio
catalogo del motor (`sys.tables`), nunca de entrada HTTP directa -- esto es
defensa en profundidad, no el control primario.
"""

from __future__ import annotations

import re

_PATRON_IDENTIFICADOR = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class IdentificadorSQLInvalido(Exception):
    pass


def validar_identificador(nombre: str) -> str:
    if not _PATRON_IDENTIFICADOR.match(nombre):
        raise IdentificadorSQLInvalido(f"identificador SQL invalido: {nombre!r}")
    return nombre
