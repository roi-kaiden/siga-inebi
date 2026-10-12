# ruff: noqa: F403,F405
"""Cloud Run QA: private persistent media and static files bundled in the image."""

from datetime import timedelta

from django.core.exceptions import ImproperlyConfigured

from .production import *

DJANGO_ENVIRONMENT = "staging"
TIME_ZONE = "America/Guatemala"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_REDIRECT_EXEMPT = [r"^api/v1/health/(database/)?$"]
# QA has no dedicated domain; do not preload institutional browsers with HSTS.
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

bucket_name = env("GCS_BUCKET_NAME", "").strip()
service_account_email = env("STORAGE_SA_EMAIL", "").strip()
if not bucket_name or not service_account_email:
    raise ImproperlyConfigured("Cloud Run requires GCS_BUCKET_NAME and STORAGE_SA_EMAIL.")

MIDDLEWARE = [MIDDLEWARE[0], "whitenoise.middleware.WhiteNoiseMiddleware", *MIDDLEWARE[1:]]
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
        "OPTIONS": {
            "bucket_name": bucket_name,
            "default_acl": None,
            "querystring_auth": True,
            "iam_sign_blob": True,
            "sa_email": service_account_email,
            "file_overwrite": False,
            "expiration": timedelta(seconds=300),
        },
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Workers share PostgreSQL, not process-local connections retained indefinitely.
DATABASES["default"]["CONN_MAX_AGE"] = env_int("DATABASE_CONN_MAX_AGE", 0)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
