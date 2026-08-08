# Plan — Propagar el patrón de workpanel/modal de `usuarios/usuario-list` al resto de módulos de `role_tenant_admin`

| Campo | Contenido |
|:---|:---|
| **Fecha** | 2026-08-08 |
| **Estado** | **Implementado y verificado (2026-08-08) — las 5 vistas cerradas.** Orden real: API Keys → Licencias → FIDS → Soporte → Compliance. Detalle de verificación por vista en `CLAUDE.md`. |
| **Origen** | Pedido directo del usuario tras cerrar la iteración de `usuarios/usuario-list` (commit `b4fc851`): "elabora un plan para implementar todos estos cambios en los diferentes módulos, workpanel y modales". |
| **Alcance** | Los módulos administrativos que ve `role_tenant_admin` (regla de sesión vigente: todo cambio va sobre sus módulos hasta nuevo aviso). **No incluye** `tenants/tenant-list` (es de `role_platform_admin`, fuera de este alcance) ni las 4 vistas operativas densas (`vuelos`, `puertas`, `rampa`, `billing/facturas` — patrón distinto y deliberado, "densidad no aire", ver §0). |
| **Referencia obligatoria** | `docs/diseno/MODAL_Y_WORKPANEL.md` §1.2 (cabecera) y §2 (modal) — este plan no redefine el patrón, solo lo aplica vista por vista. Leer ese documento antes de tocar código. |

---

## 0. Qué entra y qué no

`role_tenant_admin` hoy ve, además de Usuarios (ya hecho), estas 5
superficies administrativas: **API Keys**, **Licencias**, **FIDS**
(plantillas + pantallas), **Compliance Hub** (incidentes + post-mortems +
reportes DGAC + accesos de auditor + evidencia SOC2) y **Soporte** (tickets
+ KB + changelog).

Las 4 vistas operativas (`vuelos/estado-tiempo-real`, `puertas/tablero-puertas`,
`rampa/panel-turnaround`, `billing/panel-facturas`) **quedan fuera a
propósito**: son tableros de monitoreo denso con su propio patrón ya
establecido (`DIRECCION_VISUAL.md` §2.4.2, tabla + semáforo, ya con KPI en
vivo desde Fase 5) — mezclar ahí el eyebrow/chips de un panel
administrativo de registros sería forzar un patrón pensado para otra cosa.
Si se pide extender la cabecera nueva a esas vistas, es una decisión aparte
que hay que confirmar explícitamente, no una extensión automática de este
plan. Además, `role_tenant_admin` ya no tiene scope de escritura en
ninguna de las 4 (Fase 1 de la corrección transversal de módulos, cerrada)
ni ve el panel de Tarifarios (perdió `billing:escribir`) — no hay ningún
modal de creación que mover ahí para este rol.

---

## 1. Estado real de cada vista (verificado por lectura de código, no supuesto)

Las 5 vistas **todavía usan el patrón anterior completo**: `.consola__resumen`
(oración de resumen, no chips), `.ah-panel` con "Buscar…" separado de la
tabla, `.consola__acciones` con botón "Actualizar" suelto, y "Ver
detalles" como texto de botón (no "Ver").

| Vista | Secciones (tablas independientes) | Modal de creación existente | Complejidad de propagar |
|:---|:---:|:---|:---|
| `api-keys/api-key-list` | 1 | No (genera/rota/revoca, sin formulario de alta) | Baja — casi 1:1 con `usuario-list` |
| `licencias/licencia-list` | 1 | No (solo lectura, sin alta) | Baja — sin modal de creación, solo cabecera+tabla |
| `fids/pantalla-list` | 2 (plantillas, pantallas) | Sí — "Nueva plantilla", "Nueva pantalla" | Media — 1 eyebrow, 2 filas de búsqueda (una por sección) |
| `compliance/panel-compliance` | 5 (incidentes, post-mortems, reportes DGAC, accesos de auditor, evidencia SOC2) | Sí — 4 de las 5 secciones | Alta — 1 eyebrow, hasta 5 filas de búsqueda |
| `soporte/panel-soporte` | 3 (tickets, KB, changelog) | Sí — tickets y KB (changelog se publica desde otro flujo) | Media-alta — 1 eyebrow, 3 filas de búsqueda |

**Decisión de diseño para vistas multi-sección** (FIDS, Compliance,
Soporte): el eyebrow y el ícono de refresco son de **página completa**
(uno solo, en el `<h1>` principal — no uno por sección). Los chips de KPI
también son de página completa cuando hay un KPI transversal que ya existe
(ej. compliance ya tiene "incidentes abiertos"/"post-mortems sin publicar"
como computeds desde Fase 5 — esos se convierten en chips). La fila de
búsqueda+filtro+acción combinada **sí se repite por sección** (cada tabla
mantiene su propio buscador y su propio botón de alta), reemplazando el
`.ah-panel` + `.consola__acciones` de esa sección puntual.

---

## 2. Checklist de cambios por vista (contra `usuario-list` como referencia)

Para cada vista, en este orden:

1. **Cabecera**: agregar `.consola__eyebrow` (texto = el mismo nombre que
   ya usa el enlace del menú lateral) + mover el botón "Actualizar" a
   `.consola__refrescar` (ícono `↻`) inline junto al `<h1>`.
2. **KPI como chips**: si la vista ya tiene un `.consola__resumen` con
   cláusulas condicionales (todas la tienen, de Fase 5), convertir cada
   cláusula en un `.ah-chip` (`--critico`/`--atencion` según corresponda)
   en vez de la oración armada con `computed<string>`. El primitivo
   `.ah-chip` hoy vive **local** en `usuario-list.scss` — al tercer uso
   real (este plan llega a 5 más), promoverlo a `_primitivos.scss` en vez
   de seguir copiándolo por vista.
3. **Fila de búsqueda combinada** (por sección): reemplazar el `.ah-panel`
   ("Buscar…") + `.consola__acciones` de esa sección por una sola
   `.consola__fila-busqueda` con `.ah-buscador` (ícono `⌕`) + filtro(s)
   inline (`.ah-campo--inline`) + el botón de alta correspondiente (si la
   sección lo tiene). Si una sección no tiene texto libre para buscar
   (ej. `licencias`, catálogo cerrado sin filtro), la fila queda solo con
   el filtro/acción que sí tenga.
4. **Acción de fila**: texto corto ("Ver", no "Ver detalles") en el botón
   que abre el modal de cada fila.
5. **Modal(es) de creación**: si la vista tiene un modal de alta embebido
   (FIDS: 2: Compliance: 4; Soporte: 2), verificar que **no** traiga
   título/tarjeta propia duplicando la cabecera del modal contenedor
   (mismo hallazgo del modal "Invitar Usuario", §2.7 de
   `MODAL_Y_WORKPANEL.md`) — si alguno la tiene, corregirlo de paso.
6. **Modal(es) "Ver detalles"**: si el registro tiene campos identificadores
   de solo lectura (ej. un ticket: categoría, usuario que lo abrió) y
   campos editables (ej. estado), aplicar la tarjeta de contexto
   (`.modal-usuario-contexto`, renombrar la clase a algo neutral tipo
   `.modal-registro-contexto` si se promueve a primitivo compartido) +
   guardado diferido + `.modal-acciones` a la derecha, **solo si la vista
   ya tenía edición de campos** (no forzarlo en vistas puramente de
   lectura como `licencias` o `evidencia-soc2`).

---

## 3. Orden de implementación propuesto

1. **`api-keys/api-key-list`** — la más simple (1 sección, sin modal de
   creación con campos), sirve para validar que el patrón se traslada
   limpio a una segunda vista antes de tocar las multi-sección.
2. **`licencias/licencia-list`** — igual de simple, sin modal de
   creación en absoluto (solo cabecera + fila de búsqueda si aplica +
   tabla + "Ver detalles" de solo lectura).
3. **`fids/pantalla-list`** — primera vista multi-sección, 2 tablas,
   valida el criterio de "un eyebrow, N filas de búsqueda" antes de
   escalar a compliance/soporte.
4. **`soporte/panel-soporte`** — 3 secciones.
5. **`compliance/panel-compliance`** — la más grande (5 secciones),
   última a propósito para tener el patrón ya afinado en las 4 anteriores.

En el paso 2 (o donde se repita `.ah-chip` una tercera vez), promoverlo de
`usuario-list.scss` a `_primitivos.scss` para no seguir duplicando la
definición vista por vista.

---

## 4. Verificación (cada vista, antes de pasar a la siguiente)

Mismo checklist ya establecido en `CLAUDE.md`/`MODAL_Y_WORKPANEL.md`:
build de producción de `apps/web` en verde, verificación en navegador real
con login real de `canario@mec.aerohub.test` (`role_tenant_admin`) — no
JWT fabricado —, sin errores de consola, y confirmar que ningún modal de
creación quedó con título duplicado (§2.7).

---

## 5. Fuera de alcance explícito (no implementar sin pedido nuevo)

- Las 4 vistas operativas densas (§0).
- `tenants/tenant-list` (`role_platform_admin`).
- Promover `.ah-switch`/`.modal-usuario-contexto` a `_primitivos.scss`
  antes de que un segundo módulo realmente los necesite (evitar
  abstraer sobre un solo caso de uso).
