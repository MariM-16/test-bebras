"""
Django settings for pdt2 project on Heroku. For more info, see:
https://github.com/heroku/heroku-django-template

For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""

import os
import json
import environ
import dj_database_url
import django_heroku
from google.oauth2 import service_account

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-my)+la&!pf3=@tit7tw$!@yffeb9vee#2#+dv3ec^mppw^)9&%"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    # Disable Django's own staticfiles handling in favour of WhiteNoise, for
    # greater consistency between gunicorn and `./manage.py runserver`. See:
    # http://whitenoise.evans.io/en/stable/django.html#using-whitenoise-in-development
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'test_bebras',
    'ckeditor',
    'ckeditor_uploader',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'pdt2.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'debug': DEBUG,
        },
    },
]

WSGI_APPLICATION = 'pdt2.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
         'OPTIONS': {
            'timeout': 20,
        }
    }
}
if 'DATABASE_URL' in os.environ:
    DATABASES['default'] = dj_database_url.config(
        conn_max_age=600, ssl_require=True
    )
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/

env = environ.Env(
    GS_BUCKET_NAME=(str, ''),
    GS_CREDENTIALS_FILE=(str, ''),  
    GS_CREDENTIALS=(str, ''),  
    EMAIL_HOST_USER=(str, ''),  
    EMAIL_HOST_PASSWORD=(str, ''),  
    SOCIAL_AUTH_GOOGLE_CLIENT_ID=(str, ''),  
    SOCIAL_AUTH_GOOGLE_SECRET=(str, ''),  
)

environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True
TIME_ZONE = 'America/Santiago'

# Change 'default' database configuration with $DATABASE_URL.
DATABASES['default'].update(dj_database_url.config(conn_max_age=500, ssl_require=True))

# Honor the 'X-Forwarded-Proto' header for request.is_secure()
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Allow all host headers
ALLOWED_HOSTS = ['*']

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/

STATIC_ROOT = os.path.join(PROJECT_ROOT, 'staticfiles')
STATIC_URL = '/static/'

# Extra places for collectstatic to find static files.
STATICFILES_DIRS = [
    os.path.join(PROJECT_ROOT, 'static'),
]

# Simplified static file serving.
# https://warehouse.python.org/project/whitenoise/
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

CKEDITOR_UPLOAD_PATH = "uploads/"

CKEDITOR_CONFIGS = {
     'default': {
         'toolbar': 'full',
         'height': 200,
         'width': '100%',
         'extraPlugins': ','.join([
             'uploadimage','image2',
         ]),
     },
 }

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')
LOGIN_URL = '/login/'

# Activate Django-Heroku.
django_heroku.settings(locals())


#google cloud
INSTALLED_APPS += ["storages"]

DEFAULT_FILE_STORAGE = "storages.backends.gcloud.GoogleCloudStorage"
STATICFILES_STORAGE = "storages.backends.gcloud.GoogleCloudStorage"

GS_BUCKET_NAME = env('GS_BUCKET_NAME')

# GS_CREDENTIALS_FILE_NAME = env('GS_CREDENTIALS_FILE')
# GS_CREDENTIALS_PATH = os.path.join(BASE_DIR, 'test_bebras', 'static', GS_CREDENTIALS_FILE_NAME)

# GS_CREDENTIALS = env('GS_CREDENTIALS')
# if GS_CREDENTIALS_FILE_NAME and os.path.exists(GS_CREDENTIALS_PATH):
#     GS_CREDENTIALS = service_account.Credentials.from_service_account_file(GS_CREDENTIALS_PATH)
# else:
#     print(f"ADVERTENCIA: Archivo de credenciales de Google Cloud Storage no encontrado o nombre no especificado: {GS_CREDENTIALS_PATH}")
GS_CREDENTIALS_JSON =  env('GS_CREDENTIALS')
service_account_info = json.loads(GS_CREDENTIALS_JSON)
GS_CREDENTIALS = service_account.Credentials.from_service_account_info(service_account_info)

MEDIA_URL = f'https://storage.googleapis.com/{GS_BUCKET_NAME}/'

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
        "OPTIONS": {
            "bucket_name": GS_BUCKET_NAME,
            "credentials": GS_CREDENTIALS,
        },
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER =   env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
EMAIL_TIMEOUT = 30
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER


# Configuración de ALLAUTH
SITE_ID = 1

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_VERIFICATION = 'optional' 
ACCOUNT_ALLOW_REGISTRATION = False
ACCOUNT_LOGOUT_REDIRECT_URL = '/tests/login/'
LOGIN_REDIRECT_URL = '/tests/'
LOGIN_URL = '/tests/login/'
SOCIALACCOUNT_LOGIN_REDIRECT_URL = '/tests/'
SOCIALACCOUNT_AUTO_SIGNUP = False
SOCIALACCOUNT_ADAPTER = 'test_bebras.adapters.NoSignupSocialAccountAdapter'


SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': env('SOCIAL_AUTH_GOOGLE_CLIENT_ID'),
            'secret': env('SOCIAL_AUTH_GOOGLE_SECRET'), 
            'key': '' 
        },
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'offline',
        }
    }
}

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)
