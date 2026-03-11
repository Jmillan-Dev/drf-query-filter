from typing import Any


import django


def pytest_configure(config: Any) -> None:
    from django.conf import settings

    settings.configure(
        DEBUG_PROPAGATE_EXCEPTIONS=True,
        DEFAULT_AUTO_FIELD="django.db.models.AutoField",
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        SITE_ID=1,
        SECRET_KEY="not-a-secure-secret-key",
        USE_I18N=True,
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "APP_DIRS": True,
                "OPTIONS": {
                    "debug": True,
                },
            }
        ],
        TIME_ZONE="America/Phoenix",
        MIDDLEWARE=[
            "django.middleware.common.CommonMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
        ],
        INSTALLED_APPS=[
            "django.contrib.sessions",
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "tests",
        ],
    )

    django.setup()
