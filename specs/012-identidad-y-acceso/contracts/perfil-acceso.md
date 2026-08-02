# Contrato: perfil de acceso (`GET /auth/yo`)

Es la **única fuente** desde la que el frontend construye su menú
(FR-028). El cálculo de qué puede ver cada persona vive aquí, no
duplicado en Angular.

## Cuerpo de respuesta

```json
{
  "usuario": {
    "id": "76900737489043456",
    "email": "canario@mec.aerohub.test",
    "nombre": "Usuario Canario MEC",
    "email_verificado": true,
    "debe_cambiar_password": false
  },
  "tenant": {
    "id": "76900737489043457",
    "codigo": "MEC",
    "razon_social": "Aeropuerto de prueba MEC (canario)"
  },
  "rol": {
    "codigo": "role_tenant_admin",
    "nombre": "Administrador del Tenant"
  },
  "scopes": ["vuelos:leer", "vuelos:escribir", "..."],
  "modulos_visibles": [
    { "codigo": "M1", "nombre": "AODB", "ruta": "/vuelos/tiempo-real" },
    { "codigo": "M3", "nombre": "Terminal & Gate Manager", "ruta": "/puertas/tablero" }
  ]
}
```

`tenant` es `null` para un usuario de plataforma (`role_platform_admin` y
demás roles de alcance `'plataforma'`), que no pertenece a ningún tenant
— en ese caso `modulos_visibles` no pasa por el filtro de licencia.

## Cómo se calcula `modulos_visibles`

```
modulos_del_rol(rol)  ∩  modulos_con_licencia_vigente(tenant)
```

1. `modulos_del_rol` sale del mapeo versionado en
   `aerohub_contracts/roles_modulos.py` (research.md Decisión 4).
2. `modulos_con_licencia_vigente` reutiliza `existe_licencia_vigente()`
   de S1.7 **sin modificarla**.
3. `ruta` es la ruta del frontend asociada al módulo — vive junto al
   mapeo de roles, para que agregar un módulo nuevo al menú sea un solo
   cambio y no dos.

**Un módulo aparece solo si está en ambos conjuntos.** Un rol que
permitiría operar M5 en un tenant sin licencia de M5 **no** lo ve
(FR-010, spec.md US2 escenario 2); un tenant con licencia de M5 cuyo
usuario tiene un rol que no contempla M5 **tampoco** lo ve (escenario 3).

## Relación con el control real de acceso

Este endpoint es de **presentación**: decide qué se muestra. No sustituye
a ningún control:

- `requiere_scope(...)` sigue gateando cada endpoint de negocio (S1.2).
- El middleware de licencia sigue devolviendo `403` ante un módulo sin
  licencia (S1.7), aunque el menú alcanzara a mostrarlo.
- El guardián de tenant sigue aislando los datos (ADR-019).

Un menú desactualizado (p. ej. una licencia que venció mientras la sesión
estaba abierta) produce un `403` al hacer clic, nunca un acceso indebido
(spec.md, Edge Cases).
