# Contrato consumido: `aerohub_support`

10 de los 11 endpoints originales de S1.8 ya existen y son estables
(`services/support/aerohub_support/api/router.py`) -- documentado aquí
como referencia de lo que el frontend nuevo llama. **1 endpoint nuevo**
se agregó en este sprint (`GET /support/catalogo/categorias-ticket`):
el formulario de alta de ticket necesitaba `categoria_id`, y no existía
ningún catálogo -- la única forma de conocer un id válido era leerlo de
un ticket ya creado, mismo patrón de brecha ya corregido para
aerolíneas/aeronaves en S1.15. `docs/api/openapi.yaml` se regenera al
cerrar el sprint (mismo mecanismo de S1.15, `tools/generar_openapi.py`).

| Método | Ruta | Scope | Usado por |
|---|---|---|---|
| POST | `/support/tickets` | `support:escribir` | US1 (fuera de alcance de la vista si no hay formulario de alta explícito en spec -- ver tasks.md) |
| GET | `/support/tickets` | `support:leer` | US1 -- bandeja |
| GET | `/support/tickets/{id}` | `support:leer` | US1 -- detalle + hilo |
| POST | `/support/tickets/{id}/mensajes` | `support:escribir` | US1 -- responder |
| PATCH | `/support/tickets/{id}/estado` | `support:escribir` | US1 -- cambiar estado |
| POST | `/support/kb/articulos` | `support:escribir` | US2 -- publicar |
| GET | `/support/kb/articulos` | `support:leer` | US2 -- buscar/listar |
| GET | `/support/kb/articulos/{id}` | `support:leer` | US2 -- detalle (si se necesita, ver tasks.md) |
| POST | `/support/changelog` | `support:escribir` | US3 -- publicar |
| GET | `/support/changelog` | `support:leer` | US3 -- listar |
| GET | `/support/observabilidad/uptime` | `support:leer` \| `compliance:leer` | **sin consumidor por diseño** (research.md Decisión 5) |
| GET | `/support/catalogo/categorias-ticket` | `support:leer` | **NUEVO** -- US1, select del formulario de alta |

Todas las rutas de escritura devuelven 403 si falta el scope; las de
lectura igual. `PATCH /support/tickets/{id}/estado` devuelve 409 ante
una transición inválida (`TransicionInvalida`), 404 si el ticket no
existe.

**Hallazgo de `gestionar_tickets.py` relevante para el frontend**
(`_es_role_support()` / `consultar_ticket`, líneas 364-381):

- `POST /support/tickets/{id}/mensajes` con `es_interno: true` lanza
  `MensajeInternoNoAutorizado` (403) para cualquier rol que **no** sea
  `role_support` -- el checkbox "marcar como interno" debe ocultarse
  para el resto de los roles, no solo deshabilitarse tras el error.
- `GET /support/tickets/{id}` filtra los mensajes internos del hilo
  para cualquier rol que no sea `role_support` (`mensajes = [m for m
  in todos if not m.es_interno]`) -- el frontend no necesita filtrar
  nada del lado cliente, el backend ya garantiza que un tenant nunca
  ve una nota interna.
- `role_support` opera con `alcance_global()` sobre tickets: ve
  tickets de **todos** los tenants, no solo el suyo (coherente con ser
  el rol de la plataforma que atiende soporte a todos los clientes).
