# Instalación y configuración de SIGA-INEBI

Estado: borrador de Fase 7, 2026-10-08. Daniel prepara el procedimiento;
Josué debe repetirlo desde una copia limpia y registrar el SHA y la evidencia.
Este manual permite levantar desarrollo y QA con datos sintéticos.

## 1. Requisitos

Git, Make, Docker Engine accesible al usuario y Docker Compose v2. Las imágenes
del repositorio proporcionan Python 3.11, Node 22 y PostgreSQL 16; en ejecución
local se requieren esas versiones y cliente PostgreSQL 16 para respaldos.
No se ha fijado una versión mínima verificada de Git/Docker/Compose: registrar
las versiones usadas en [entorno QA](../quality/fase-7/entorno-y-datos.md).

El perfil objetivo de rendimiento es 1 vCPU y 2 GB de RAM; no representa el
mínimo medido para construir imágenes o ejecutar todas las suites. Reservar
espacio para imágenes, dependencias, base, archivos y respaldos y medir su uso
en QA. Puertos por defecto: 5173 (UI), 8000 (API) y 5432 (PostgreSQL local).

```sh
git --version
docker --version
docker compose version
docker info >/dev/null
```

Si Docker devuelve permiso denegado, resolver el acceso del usuario al daemon
con el administrador del equipo y repetir la comprobación antes de continuar.

## 2. Camino recomendado desde copia limpia

```sh
git clone https://github.com/siga-inebi/siga-inebi.git
cd siga-inebi
git switch develop
git rev-parse HEAD
make setup
```

Revisar `AGENTS.md` y [onboarding](../development/onboarding.md). Para reproducir
una entrega, seleccionar después el SHA completo consignado en su manifiesto
con `git checkout --detach SHA_VALIDADO` y registrar ese SHA. `develop` cambia.
Editar `.env` localmente antes del arranque: usar proyecto, puertos y credenciales
propios de QA; no imprimir sus valores ni versionar el archivo. Los ejemplos de
credenciales son públicos y solo sirven para desarrollo aislado. La cuenta demo
se configura con `DEMO_ADMIN_USERNAME`, `DEMO_ADMIN_EMAIL` y
`DEMO_ADMIN_PASSWORD`; no reutilizarla en producción.

```sh
docker compose config --quiet
docker compose up --build -d
docker compose ps
docker compose exec backend python manage.py check
docker compose exec backend python manage.py migrate --check
docker compose exec backend python manage.py showmigrations --plan
docker compose exec db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
curl --fail --silent --output /dev/null http://127.0.0.1:5173/
curl --fail --silent --output /dev/null http://127.0.0.1:8000/api/v1/auth/login/
```

Esperar servicios saludables. El entrypoint aplica migraciones y el override
activa `seed_demo_data` al arrancar. No cargar datos reales. La UI local queda
en `http://127.0.0.1:5173`, API en `http://127.0.0.1:8000/api/v1/` y administración
Django en `http://127.0.0.1:8000/admin/`. Iniciar sesión con la cuenta configurada
en `.env` y comprobar una pantalla autorizada. No adjuntar cookies ni credenciales
a las evidencias. Si se necesitan explícitamente:

```sh
make migrate
make seed
docker compose down
```

`down` conserva volúmenes. La opción `-v` los elimina y solo corresponde a datos
de pruebas desechables. Proyectos Compose distintos separan volúmenes, pero los
bind mounts siguen apuntando a la copia local: usar otra copia para aislar
`backend/media` y `backups` de otros ambientes.

## 3. Configuración por ambiente

| Grupo | Finalidad y fuente |
| --- | --- |
| `COMPOSE_PROJECT_NAME`, `*_PORT` | Identidad de stack y puertos host; `.env.example`. |
| `POSTGRES_*`, `DATABASE_*` | Credenciales y conexión; Compose conecta a `db`, ejecución local a `127.0.0.1`. |
| `DJANGO_SETTINGS_MODULE`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS` | Settings, secreto, diagnóstico y hosts; `backend/.env.example`. |
| `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, cookies | Orígenes y sesión; deben coincidir con la URL real del navegador. |
| `VITE_API_URL`, `VITE_BACKEND_PROXY_TARGET` | API visible y destino interno del proxy; `frontend/.env.example`. |
| `TIME_ZONE`, niveles de log | Zona institucional y observabilidad; evitar datos sensibles en logs. |
| `DEMO_ADMIN_*`, `SEED_DEMO_DATA_ON_START` | Aprovisionamiento sintético de desarrollo. |
| `BACKUP_ROOT`, `MEDIA_ROOT`, `RECOVERY_*_HOURS` | Pilas e indicadores de recuperación; [plan de respaldo](09-final-backup-and-recovery-plan.md). |

Compose actual usa Django `runserver`, Vite de desarrollo y HTTP. Pruebas usan
`compose.test.yml`, base `db-test` desechable y settings de test con PostgreSQL
obligatorio. SQLite continúa disponible exclusivamente para desarrollo rápido.
Producción requiere `config.settings.production`, PostgreSQL, servidor de
aplicación y proxy TLS configurados según [despliegue seguro](../development/secure-deployment.md).
El repositorio no proporciona un perfil Compose de producción ni pipeline de
despliegue. Su diseño y comprobación quedan pendientes antes de publicar.

## 4. Validación y alternativa local

La instalación anterior construye la imagen `backend` de Compose. Mantener
esa imagen disponible y `db` saludable para ejecutar `make recovery-drill`:
su target crea un contenedor backend temporal con `--no-deps`, usa el cliente
PostgreSQL 16 y Python 3 de la imagen, y no inicia ni construye dependencias.
El detalle de destinos desechables está en el [plan de respaldo](09-final-backup-and-recovery-plan.md).

```sh
make ci-local
```

Ejecuta pruebas, cobertura, lint, formato backend, migraciones, seguridad backend
y build frontend en Docker. El plan completo añade formato frontend y auditoría
npm; conservar también esos resultados siguiendo el
[plan de pruebas](../planning/tests_plan.md). `ci-local` limpia su stack al
terminar; capturar logs y códigos de salida antes de limpiar y conservar los
fallos. No confundir salida exitosa de un subconjunto con aceptación de Fase 7.

La alternativa soportada para backend local con PostgreSQL y frontend local
está en [local setup](../development/local-setup.md). Crear `.venv` con Python
3.11, instalar `backend/requirements/dev.txt` y ejecutar `npm ci` con Node 22.
Declarar variables `DATABASE_*` y orígenes locales coherentes; sus comandos de
ejemplo usan API 8001 y UI 4173, diferentes de Compose. Las pruebas finales
siempre emplean PostgreSQL. Ver [estrategia de pruebas](../development/testing-strategy.md).

## 5. Diagnóstico y cierre

| Síntoma | Comprobación y acción |
| --- | --- |
| Puerto ocupado | Revisar `docker compose ps` y puertos del host; asignar puertos libres en `.env` y recrear servicios. No detener procesos ajenos. |
| Contenedor detenido | `docker compose ps -a`; inspeccionar logs localmente, corregir el error y ejecutar `docker compose up --build -d`. Redactar secretos antes de compartir logs. |
| Migraciones pendientes | `migrate --check`; aplicar `make migrate` en desarrollo/QA y volver a comprobar. |
| Dependencias ausentes | Reconstruir imágenes; localmente instalar requirements o `npm ci` desde el lockfile. |
| Base no disponible | Confirmar `db` saludable con `pg_isready`; revisar host y puerto de conexión sin imprimir secretos. |
| Sesión/API rechazada | Revisar URL, hosts, CORS, CSRF y settings; no desactivar controles para ocultar el fallo. |

Consultar [troubleshooting](../development/troubleshooting.md); sus cifras de
vulnerabilidades son históricas y deben sustituirse por la auditoría de la corrida.
Teléfono con cámara requiere HTTPS y permiso del navegador; esta instalación
local HTTP no prueba RNF de escaneo en dispositivo real.

- [ ] Josué reproduce este procedimiento en copia limpia y consigna versiones/SHA.
- [ ] Vincular logs de salud, migraciones, suites, cobertura, build y seguridad.
- [ ] Validar configuración HTTPS y teléfono antes de cerrar pruebas QR.
- [ ] Revisor independiente valida la versión final y registra el resultado en
  [seguimiento de manuales](../quality/fase-7/seguimiento-manuales.md).
