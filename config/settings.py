
import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


# SECURITY SETTINGS

DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

SECRET_KEY = os.getenv('SECRET_KEY')

if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured(
            'Set SECRET_KEY when DEBUG is disabled.'
        )
    SECRET_KEY = 'django-insecure-development-key'

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        'ALLOWED_HOSTS',
        '127.0.0.1,localhost'
    ).split(',')
    if host.strip()
]


# APPLICATIONS

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'corsheaders',

    'products',
    'orders',
    'payments',
]


# MIDDLEWARE

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# URL CONFIGURATION

ROOT_URLCONF = 'config.urls'


# TEMPLATES

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


# WSGI APPLICATION

WSGI_APPLICATION = 'config.wsgi.application'


# DATABASE CONFIGURATION
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
    }
}

if os.getenv('DATABASE_URL'):
    DATABASES['default'] = dj_database_url.config(
        conn_max_age=600,
        ssl_require=True,
    )


# PASSWORD VALIDATION

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


# INTERNATIONALIZATION

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True


# STATIC FILES

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / 'static'
] if (BASE_DIR / 'static').exists() else []

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}


# MEDIA FILES

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# DEFAULT PRIMARY KEY

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# DJANGO REST FRAMEWORK

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
}


# CORS AND CSRF CONFIGURATION

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        'CORS_ALLOWED_ORIGINS',
        'http://localhost:5173,http://127.0.0.1:5173'
    ).split(',')
    if origin.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        'CSRF_TRUSTED_ORIGINS',
        'http://localhost:5173,http://127.0.0.1:5173'
    ).split(',')
    if origin.strip()
]


# PRODUCTION SECURITY

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SECURE_SSL_REDIRECT = os.getenv(
    'SECURE_SSL_REDIRECT', 'False'
).lower() == 'true'

SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG


# M-PESA DAR AJA CONFIGURATION

MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY')
MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET')
MPESA_PASSKEY = os.getenv('MPESA_PASSKEY')
MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE')

MPESA_ENVIRONMENT = os.getenv('MPESA_ENVIRONMENT', 'sandbox')

MPESA_TRANSACTION_TYPE = os.getenv(
    'MPESA_TRANSACTION_TYPE',
    'CustomerPayBillOnline'
)

MPESA_CALLBACK_URL = os.getenv('MPESA_CALLBACK_URL')
