# Runbook — Airflow en desarrollo local

| Campo | Contenido |
|:---|:---|
| Sprint de origen | S0.1 (Plan §7.1) |
| Servicio | `airflow` (modo `standalone`) |

## Arranque

```bash
docker compose -f infra/docker-compose.yml up -d airflow
```

Primer arranque en un volumen `airflowdata` vacío: healthcheck en verde en **~30-45 s** (verificado, Sprint S0.1). UI en `http://localhost:8080`; usuario/contraseña generados en `/opt/airflow/simple_auth_manager_passwords.json.generated` dentro del volumen — consultar con:

```bash
docker exec aerohub-airflow cat /opt/airflow/simple_auth_manager_passwords.json.generated
```

## Ejecutor

Sin backend Postgres propio para el metastore, `standalone` solo admite `SequentialExecutor` sobre su SQLite por defecto (un DAG a la vez). **No fijar `AIRFLOW__CORE__EXECUTOR=LocalExecutor`** sin antes añadir un servicio Postgres dedicado al metastore de Airflow — `LocalExecutor` exige un backend con soporte de conexiones concurrentes y falla al arrancar contra SQLite (`AirflowConfigException: cannot use SQLite with the LocalExecutor`, reproducido en S0.1). Revisar esta decisión en el Sprint S2.1 si el volumen de DAGs exige paralelismo real; el metastore de Airflow es una base de datos interna de su propio control plane, ortogonal a ADR-013 (que rige el motor operacional de negocio, MonetDB).

## Problema conocido: recrear el contenedor sobre un volumen ya inicializado puede colgarse

**Síntoma observado (S0.1):** tras un `docker compose up -d` que fuerza `Recreate` de `airflow` (p. ej. por cambiar su `healthcheck` u otra config) **reutilizando el volumen `airflowdata` de un arranque anterior ya exitoso**, el contenedor queda indefinidamente en el paso `Checking database is initialized` sin avanzar ni fallar — no es lento, está bloqueado (probado esperando > 5 minutos sin progreso en el log).

**No ocurre en un arranque limpio:** contra un volumen `airflowdata` recién creado, el mismo `standalone` inicializa y queda `healthy` en menos de un minuto, de forma repetible.

**Hipótesis:** contención de bloqueo del archivo SQLite del metastore sobre el volumen con el backend de Docker Desktop en Windows; no se investigó la causa raíz a fondo por no ser bloqueante para S0.1 (aún no existe ningún DAG).

**Mitigación práctica hasta resolverlo:**

```bash
docker compose -f infra/docker-compose.yml stop airflow
docker compose -f infra/docker-compose.yml rm -f airflow
docker volume rm infra_airflowdata
docker compose -f infra/docker-compose.yml up -d airflow
```

Si el proyecto migra el metastore a Postgres (ver "Ejecutor" arriba), reevaluar si el problema persiste — un backend real en vez de SQLite sobre volumen probablemente lo elimina de raíz.
