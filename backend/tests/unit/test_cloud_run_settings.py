"""Cloud QA profile contracts without accessing Google APIs or credentials."""

import json
import os
import subprocess
import sys

import pytest

pytestmark = pytest.mark.unit


def _profile(**overrides):
    env = {
        **os.environ,
        "DJANGO_SECRET_KEY": "cloud-profile-test-only",
        "DJANGO_ALLOWED_HOSTS": "localhost,.run.app",
        "DJANGO_ENVIRONMENT": "production",
        "DATABASE_ENGINE": "postgresql",
        "GCS_BUCKET_NAME": "qa-test-bucket",
        "STORAGE_SA_EMAIL": "qa@test-project.iam.gserviceaccount.com",
        "DATABASE_CONN_MAX_AGE": "0",
        **overrides,
    }
    return subprocess.run(  # noqa: S603 - fixed Python snippet with synthetic settings
        [
            sys.executable,
            "-c",
            """
import json
from config.settings import cloud_run as s
storage = s.STORAGES['default']
options = dict(storage['OPTIONS'])
options['expiration'] = options['expiration'].total_seconds()
print(json.dumps({
    'debug': s.DEBUG,
    'session_secure': s.SESSION_COOKIE_SECURE,
    'csrf_secure': s.CSRF_COOKIE_SECURE,
    'redirect': s.SECURE_SSL_REDIRECT,
    'probe_exemptions': s.SECURE_REDIRECT_EXEMPT,
    'proxy': s.SECURE_PROXY_SSL_HEADER,
    'middleware': s.MIDDLEWARE,
    'storage': storage['BACKEND'],
    'options': options,
    'static': s.STORAGES['staticfiles']['BACKEND'],
    'database': {'engine': s.DATABASES['default']['ENGINE'],
                 'options': s.DATABASES['default'].get('OPTIONS', {}),
                 'age': s.DATABASES['default']['CONN_MAX_AGE']},
    'timezone': s.TIME_ZONE,
}))
""",
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_cloud_profile_preserves_secure_cookies_private_storage_and_proxy_https():
    result = _profile()
    assert result.returncode == 0, result.stderr
    profile = json.loads(result.stdout)
    assert profile["debug"] is False
    assert profile["session_secure"] is True
    assert profile["csrf_secure"] is True
    assert profile["redirect"] is True
    assert profile["proxy"] == ["HTTP_X_FORWARDED_PROTO", "https"]
    assert profile["probe_exemptions"] == [r"^api/v1/health/(database/)?$"]
    assert profile["middleware"][1] == "whitenoise.middleware.WhiteNoiseMiddleware"
    assert profile["storage"] == "storages.backends.gcloud.GoogleCloudStorage"
    assert profile["options"] == {
        "bucket_name": "qa-test-bucket",
        "default_acl": None,
        "querystring_auth": True,
        "iam_sign_blob": True,
        "sa_email": "qa@test-project.iam.gserviceaccount.com",
        "file_overwrite": False,
        "expiration": 300,
    }
    assert profile["static"] == "whitenoise.storage.CompressedManifestStaticFilesStorage"
    assert profile["database"]["engine"] == "django.db.backends.postgresql"
    assert profile["database"]["age"] == 0
    assert profile["timezone"] == "America/Guatemala"


@pytest.mark.parametrize("missing", ["GCS_BUCKET_NAME", "STORAGE_SA_EMAIL"])
def test_cloud_profile_fails_closed_without_persistent_storage_configuration(missing):
    result = _profile(**{missing: ""})
    assert result.returncode != 0
    assert "requires GCS_BUCKET_NAME and STORAGE_SA_EMAIL" in result.stderr
