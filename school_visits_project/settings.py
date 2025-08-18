import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-0798)j)82a^ufal=f$8#nc6vy0p$vqym2pp+^3y0ui7g2wou2-'

DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'soporteinformatico.pythonanywhere.com']


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth', 
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'visits.apps.VisitsConfig',
]

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': None,
    'PAGE_SIZE': None,
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'school_visits_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'school_visits_project.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

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

LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'Europe/Madrid'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'visits' / 'static'
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configuración de Autenticación
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'public_booking'

# Configuración de Sesiones
SESSION_COOKIE_AGE = 86400  # 24 horas
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_SECURE = DEBUG is False  # True en producción, False en desarrollo
SESSION_SAVE_EVERY_REQUEST = True

# Configuración CSRF
CSRF_TRUSTED_ORIGINS = ['http://localhost:8000']

# Configuración de Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(Path(__file__).resolve().parent, 'django.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        '': {  
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'visits': {  
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# ====================================
# CONFIGURACIÓN DE EMAIL - IONOS
# ====================================

# Configuración para desarrollo local (ACTIVA)
if DEBUG:
    # SMTP REAL con Ionos - ACTIVADO
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.ionos.es')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
    EMAIL_USE_TLS = True
    EMAIL_USE_SSL = False  # Para puerto 587
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
    EMAIL_TIMEOUT = 60  # Timeout en segundos
    
    # Para debug: descomenta la siguiente línea si quieres ver solo en consola
    # EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Configuración para producción
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.ionos.es')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
    EMAIL_USE_TLS = True
    EMAIL_USE_SSL = False
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
    EMAIL_TIMEOUT = 60

# Configuración común para ambos entornos
DEFAULT_FROM_EMAIL = os.environ.get('EMAIL_HOST_USER', 'no-reply@claretsegovia.es')
APPOINTMENT_NOTIFICATION_EMAIL = os.environ.get('EMAIL_HOST_USER', 'no-reply@claretsegovia.es')

# Configuración de URLs del colegio
SCHOOL_CONFIG = {
    'name': 'Colegio Claret Segovia',
    'address': 'Av. Padre Claret, 3, 40003 Segovia',
    'phone': '921 42 03 00',
    'email': os.environ.get('EMAIL_HOST_USER', 'no-reply@claretsegovia.es'),
    'website': 'https://claretsegovia.es',
    'base_url': os.environ.get('BASE_URL', 'http://localhost:8000' if DEBUG else 'https://soporteinformatico.pythonanywhere.com')
}