import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.environ['SECRET_KEY']

DEBUG = os.environ.get('DEBUG', 'False') == 'True'

if DEBUG:
    ALLOWED_HOSTS = ['events.wfco.io', 'wfco.io', '159.223.195.211', "*"]
else:
    ALLOWED_HOSTS = ['events.wfco.io', 'wfco.io', '159.223.195.211']


# Applicaton definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'events',
    'people',
    'clients',
    'login',
    'django_microsoft_sso',
]

MICROSOFT_SSO_APPLICATION_ID = os.environ['MICROSOFT_SSO_APPLICATION_ID']
MICROSOFT_SSO_CLIENT_SECRET = os.environ['MICROSOFT_SSO_CLIENT_SECRET']
MICROSOFT_SSO_SCOPE = ['User.Read.All']

MICROSOFT_SSO_ALLOWABLE_DOMAINS = ["topconconsulting.com", "watson-forsberg.com"]

MICROSOFT_CALENDAR_API_CLIENT_ID = os.environ['MICROSOFT_CALENDAR_API_CLIENT_ID']
MICROSOFT_CALENDAR_API_CLIENT_SECRET = os.environ['MICROSOFT_CALENDAR_API_CLIENT_SECRET']

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/events/'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'eventPlanner.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'eventPlanner.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Static files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

GOOGLE_MAPS_API_KEY = os.environ['GOOGLE_MAPS_API_KEY']

# CSRF
CSRF_TRUSTED_ORIGINS = [
    'https://events.wfco.io',
    'https://wfco.io',
]


# Security — only enforce in production (when DEBUG is False)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
