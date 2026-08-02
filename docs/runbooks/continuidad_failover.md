# Runbook — Conmutación hacia la réplica de respaldo (failover)

| Campo | Contenido |
|:---|:---|
| Sprint de origen | S1.9 (ADR-018, componente C4) |
| Motivo | Procedimiento paso a paso para conmutar hacia `monetdb-standby` cuando el primario (`monetdb`) falla -- research.md Decision 8 de `specs/011-continuidad-rto-rpo/`: la conmutación NUNCA es automática, siempre la ejecuta una persona con autorización de plataforma |
| Herramienta de apoyo | `tools/continuidad_conmutar.py` (contracts/conmutacion-runbook.md) -- verifica el atraso, nunca reinicia nada por sí sola |

## 1. Confirmar que el fallo es real, no transitorio

Antes de considerar una conmutación:

- Verificar el estado del contenedor: `docker compose -f infra/docker-compose.yml ps monetdb`.
- Revisar si `up{job="aerohub_gateway"}` está en `0` de forma sostenida en Prometheus (no un blip de un solo scrape) -- las alertas `AeroHubGatewayIndisponibleSev1/2/3` (`infra/prometheus/alertas.yml`, S1.8) ya distinguen esto por duración.
- Intentar una reconexión simple (`docker compose restart monetdb`) SI el fallo parece ser del proceso, no del host/volumen -- una conmutación es más costosa de revertir que un reinicio del mismo contenedor.

Solo si el primario está genuinamente inalcanzable o corrupto, continuar.

## 2. Ejecutar el preflight

```bash
uv run python tools/continuidad_conmutar.py --standby monetdb-standby
```

- Código de salida `0` con "OK" o "ADVERTENCIA": el atraso está dentro de lo tolerable, se imprime el DSN sugerido.
- Código de salida `1`: el atraso supera el umbral de alerta (120 s) -- conmutar ahora implica perder más datos de los que RPO tolera. Evaluar si la urgencia justifica esa pérdida antes de continuar (decisión humana, no automatizable).

## 3. Aplicar el cambio de DSN

El único punto de configuración a cambiar es `AEROHUB_DB_DSN` del servicio `gateway` (`infra/docker-compose.yml`):

```bash
# Editar infra/docker-compose.yml -- reemplazar temporalmente:
#   AEROHUB_DB_DSN: "monetdb://aerohub_app:aerohub_app_dev_password@monetdb:50000/aerohub"
# por el DSN sugerido por el preflight (mismo formato, host monetdb-standby).
docker compose -f infra/docker-compose.yml up -d gateway
```

`packages/repository/base.py` lee `AEROHUB_DB_DSN` al crear el `Engine` (perezosamente, una vez por proceso) -- reiniciar el contenedor `gateway` es suficiente, no hace falta reconstruir la imagen.

## 4. Verificación de consistencia post-conmutación

- `GET /metrics` del `gateway` responde (confirma que el proceso arrancó contra el nuevo DSN).
- Un endpoint de lectura simple (p. ej. `GET /support/changelog`) responde `200` -- confirma que el standby sirve tráfico de aplicación real.
- Comparar el `lsn` máximo de `continuidad.journal_mutacion` en el standby contra el que tenía el primario al momento del fallo (si es alcanzable) -- documenta la ventana de pérdida real para el post-mortem (`compliance.post_mortem`, S1.7).

## 5. Si el primario original vuelve a estar disponible

El primario original NO se reincorpora automáticamente como primario otra vez. Dos caminos, decisión de la persona a cargo:

- **Reconmutar** al primario original: solo si su estado es confiable (no se corrompió durante el fallo) y su `lsn` no diverge del que aplicó el standby mientras sirvió tráfico -- si divergen, el primario original necesita restaurarse desde un snapshot posterior a la conmutación, no reincorporarse tal cual.
- **El standby pasa a ser el nuevo primario de referencia**: más simple y más seguro cuando no hay certeza sobre el estado del primario original -- en ese caso, el primario original se reconstruye desde cero (nuevo volumen, DDL aplicado, sembrado como un standby nuevo) y pasa a cumplir el rol de réplica.

En ambos casos, registrar la decisión y el motivo en `compliance.log_auditoria` (mismo mecanismo de auditoría de cualquier otra excepción operativa) y abrir un post-mortem si el incidente lo amerita (severidad Sev1/Sev2, S1.7).
