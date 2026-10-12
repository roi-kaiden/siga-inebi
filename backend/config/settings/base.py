import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def env(name, default=None):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    return env(name, str(default)).lower() in {"1", "true", "yes", "on"}


def env_int(name, default):
    return int(env(name, str(default)))


def env_list(name, default=""):
    value = env(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


SECRET_KEY = env("DJANGO_SECRET_KEY", "insecure-development-key")
DEBUG = env_bool("DJANGO_DEBUG", False)
DJANGO_ENVIRONMENT = env("DJANGO_ENVIRONMENT", "development")
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "apps.common",
    "apps.people",
    "apps.identity",
    "apps.students",
    "apps.teachers",
    "apps.academics",
    "apps.enrolments",
    "apps.attendance",
    "apps.evaluation",
    "apps.reporting",
    "apps.documents",
    "apps.audit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.common.middleware.NoStoreApiResponseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.identity.middleware.SessionIdleTimeoutMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.audit.middleware.AuditContextMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

AUTH_USER_MODEL = "identity.UserAccount"
LOGIN_MAX_FAILED_ATTEMPTS = env_int("LOGIN_MAX_FAILED_ATTEMPTS", 5)
LOGIN_LOCKOUT_MINUTES = env_int("LOGIN_LOCKOUT_MINUTES", 10)
DEFAULT_SESSION_IDLE_TIMEOUT_MINUTES = env_int("DEFAULT_SESSION_IDLE_TIMEOUT_MINUTES", 30)
ACCOUNT_ACTIVATION_TTL_MINUTES = env_int("ACCOUNT_ACTIVATION_TTL_MINUTES", 15)
ACCOUNT_ACTIVATION_MAX_ATTEMPTS = env_int("ACCOUNT_ACTIVATION_MAX_ATTEMPTS", 3)
DOCUMENT_MAX_UPLOAD_SIZE_BYTES = env_int("DOCUMENT_MAX_UPLOAD_SIZE_BYTES", 10 * 1024 * 1024)
# RNF-CAP-002: crecimiento estimado de almacenamiento por ciclo, con umbral
# configurable de advertencia. El valor por defecto sigue la estimacion del
# requerimiento (2 GiB por ciclo) y puede ajustarse por infraestructura real.
DOCUMENT_STORAGE_GROWTH_PER_CYCLE_BYTES = env_int(
    "DOCUMENT_STORAGE_GROWTH_PER_CYCLE_BYTES", 2 * 1024**3
)
DOCUMENT_STORAGE_WARNING_THRESHOLD_BYTES = env_int(
    "DOCUMENT_STORAGE_WARNING_THRESHOLD_BYTES",
    DOCUMENT_STORAGE_GROWTH_PER_CYCLE_BYTES,
)
# RF-ARC-006: la politica exacta de retencion institucional de justificaciones
# se define por la institucion, pero el sistema debe conservar una referencia
# operativa por defecto y dejarla configurable sin tocar codigo.
JUSTIFICATION_ATTACHMENT_RETENTION_DAYS = env_int("JUSTIFICATION_ATTACHMENT_RETENTION_DAYS", 365)

# RNF-RES-001 / RNF-RES-002: respaldo y recuperacion.
#
# Las dos pilas tienen directorios separados a proposito: el requerimiento pide
# que los esquemas sean independientes, y compartir destino invita a que un
# borrado o una rotacion se lleve las dos.
#
# RPO y RTO son declaraciones institucionales, no medidas de infraestructura.
# Los valores por defecto son la declaracion de referencia documentada en
# `docs/architecture/backup-and-recovery.md` (PD-002) y se ajustan por entorno
# en cuanto el establecimiento confirme los suyos.
BACKUP_ROOT = env("BACKUP_ROOT", str(BASE_DIR.parent / "backups"))
# Los scripts viven en el repositorio, fuera de `backend/`. La imagen del
# backend solo copia `backend/`, asi que en contenedor se montan aparte y esta
# variable dice donde quedaron.
BACKUP_SCRIPTS_DIR = env("BACKUP_SCRIPTS_DIR", str(BASE_DIR.parent / "scripts" / "backup"))
DATABASE_BACKUP_DIR = env("DATABASE_BACKUP_DIR", f"{BACKUP_ROOT}/database")
FILES_BACKUP_DIR = env("FILES_BACKUP_DIR", f"{BACKUP_ROOT}/files")
RECOVERY_POINT_OBJECTIVE_HOURS = env_int("RECOVERY_POINT_OBJECTIVE_HOURS", 24)
RECOVERY_TIME_OBJECTIVE_HOURS = env_int("RECOVERY_TIME_OBJECTIVE_HOURS", 4)

DATABASE_ENGINE = env("DATABASE_ENGINE", "postgresql")
SQLITE_PATH = env("SQLITE_PATH", "db.sqlite3")

if DATABASE_ENGINE == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / SQLITE_PATH,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DATABASE_NAME", "siga_inebi"),
            "USER": env("DATABASE_USER", "siga_inebi"),
            "PASSWORD": env("DATABASE_PASSWORD", "siga_inebi_dev_password"),
            "HOST": env("DATABASE_HOST", "localhost"),
            "PORT": env("DATABASE_PORT", "5432"),
            # RNF-CAP-001: en 1 vCPU / 2 GB abrir una conexion TCP por
            # request compite por la misma CPU que atiende la peticion.
            # Reusar la conexion durante este tiempo evita ese costo sin
            # agotar el limite de conexiones de un Postgres de un solo nodo.
            "CONN_MAX_AGE": env_int("DATABASE_CONN_MAX_AGE", 60),
        }
    }

# RF-CTA-004: Longitud mínima configurable; rechazo de contraseñas comunes.
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": env_int("PASSWORD_MIN_LENGTH", 10)},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "es-gt"
# RNF-LOC-002: el producto es monolingue. `LocaleMiddleware` solo puede activar
# un idioma que este en `LANGUAGES`, asi que declarar uno cierra la unica puerta
# por la que un `Accept-Language: en` cambiaba a ingles los mensajes propios de
# DRF y de Django. Sin esto, la garantia dependia del navegador del usuario.
LANGUAGES = [("es-gt", "Espanol (Guatemala)")]
TIME_ZONE = env("TIME_ZONE", "America/Guatemala")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = DJANGO_ENVIRONMENT != "development"
CSRF_COOKIE_SECURE = DJANGO_ENVIRONMENT != "development"
CSRF_COOKIE_HTTPONLY = False
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = DJANGO_ENVIRONMENT == "production"
SECURE_HSTS_SECONDS = 31_536_000 if DJANGO_ENVIRONMENT == "production" else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = DJANGO_ENVIRONMENT == "production"
SECURE_HSTS_PRELOAD = DJANGO_ENVIRONMENT == "production"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "config.api.exception_handler.api_exception_handler",
    # RNF-SEG-006: limite por IP para el unico endpoint publico y sin
    # autenticacion del catalogo (verificacion de documentos, RF-EMI-009).
    # Generoso para el uso legitimo de consultar un documento propio, bajo
    # para frenar raspado/enumeracion de codigos.
    "DEFAULT_THROTTLE_RATES": {
        "document_verification": "20/min",
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "SIGA-INEBI API",
    "DESCRIPTION": "Fundacion ejecutable inicial del sistema SIGA-INEBI",
    "VERSION": "0.1.0",
    # Componentes separados para peticion y respuesta. Sin esto un serializer
    # produce UN solo componente compartido por las dos direcciones, asi que los
    # campos de solo lectura (`public_id`, `created_at`, `updated_at`) aparecen
    # como requeridos en el cuerpo de un POST o PUT, y cualquier cliente
    # generado a partir del schema obliga a enviarlos aunque el backend los
    # ignore.
    "COMPONENT_SPLIT_REQUEST": True,
    # Un campo de solo lectura nunca es obligatorio en una peticion.
    "COMPONENT_NO_READ_ONLY_REQUIRED": True,
    "SCHEMA_PATH_PREFIX": "/api/v1",
    # El schema y Swagger UI describen toda la superficie de la API: solo se
    # sirven a sesiones autenticadas (deny by default, igual que el resto).
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAuthenticated"],
    # Pendiente conocido, NO intentar con `ENUM_NAME_OVERRIDES` a secas: cuatro
    # dominios tienen un campo `status`, y drf-spectacular resuelve la colision
    # con nombres por hash (`Status113Enum`, `StatusE41Enum`). Es feo pero es
    # solo el nombre del componente; los valores son correctos.
    #
    # No se arregla aqui porque `ENUM_NAME_OVERRIDES` resuelve las rutas con
    # `import_string`, que no puede recorrer clases anidadas: apuntar a
    # `Enrolment.EnrolmentStatus.choices` falla en silencio y deja el schema con
    # un error de duplicacion. La solucion correcta es exponer las choices como
    # variable de modulo en cada `models.py` y apuntar a esa, y toca hacerlo
    # cuando se generen tipos desde el schema (ahi el nombre si importa).
}

# RNF-OPE-001: nivel del registro operativo, ajustable por despliegue sin tocar
# codigo. INFO deja una linea por inicio y fin de cada tarea; WARNING la calla y
# conserva solo los fallos.
LOG_LEVEL = env("DJANGO_LOG_LEVEL", "INFO").upper()
TASK_LOG_LEVEL = env("TASK_LOG_LEVEL", LOG_LEVEL).upper()

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "%(levelname)s %(name)s %(message)s",
        },
        # Las lineas de tarea se leen en un log recolectado, a veces meses
        # despues, asi que llevan marca de tiempo y proceso: sin eso no se puede
        # distinguir dos corridas de la misma tarea.
        "operational": {
            "format": "%(asctime)s %(levelname)s %(name)s pid=%(process)d %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "operational": {
            "class": "logging.StreamHandler",
            "formatter": "operational",
        },
    },
    "loggers": {
        # RNF-OPE-001: registro del proceso trabajador y de las tareas
        # programadas. Va a su propio handler para que el formato con marca de
        # tiempo no cambie el resto de la salida, y no propaga para no
        # duplicar cada linea en la raiz.
        "siga.tasks": {
            "handlers": ["operational"],
            "level": TASK_LOG_LEVEL,
            "propagate": False,
        },
        # Django's default configuration attaches AdminEmailHandler to this
        # logger, and every 4xx/5xx response goes through it. That handler
        # renders a traceback template even when ADMINS is empty, so an error
        # response would pay for a report nobody receives. Logs go to the
        # console like everything else.
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
}


def require_postgresql():
    if DATABASE_ENGINE != "postgresql":
        raise ImproperlyConfigured("This environment requires PostgreSQL.")
