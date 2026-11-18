
import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(BASE_DIR / '.env')


# SECURITY SETTINGS
SECRET_KEY = os.getenv(
    'SECRET_KEY',
    'django-insecure-development-key'
)

DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = [
    '127.0.0.1',
    'localhost',
    'occasion-bluetooth-linked-dean.trycloudflare.com',
]


# APPLICATIONS
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party applications
    'rest_framework',
    'corsheaders',

     # Our applications
    'products',
    'orders',
    'payments',
]


# MIDDLEWARE
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
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
STATIC_URL = 'static/'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]


# MEDIA FILES
MEDIA_URL = 'media/'

MEDIA_ROOT = BASE_DIR / 'media'


# DEFAULT PRIMARY KEY
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# DJANGO REST FRAMEWORK
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
}


# CORS CONFIGURATION
CORS_ALLOWED_ORIGINS = [
    'http://127.0.0.1:8000',
    'http://localhost:8000',
]

# M-Pesa Daraja Configuration

MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY')

MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET')

MPESA_PASSKEY = os.getenv('MPESA_PASSKEY')

MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE')

MPESA_ENVIRONMENT = os.getenv('MPESA_ENVIRONMENT', 'sandbox')

MPESA_CALLBACK_URL = os.getenv('MPESA_CALLBACK_URL')