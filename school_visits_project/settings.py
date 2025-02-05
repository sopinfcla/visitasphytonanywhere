import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-0798)j)82a^ufal=f$8#nc6vy0p$vqym2pp+^3y0ui7g2wou2-'

DEBUG = True

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth', 
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'visits.apps.VisitsConfig',  #
]

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

# Configuración de archivos estáticos
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
   BASE_DIR / 'visits' / 'static'
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGOUT_REDIRECT_URL = '/'  # Redirige a la página principal después del logout



# Ejemplo de configuración de logging en settings.py
LOGGING = {
    'version': 1,  # Versión del diccionario de configuración de logging
    'disable_existing_loggers': False,  # Permite que se usen también los loggers existentes de Django
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
        'console': {  # Handler para imprimir en consola
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',  # Puedes usar 'simple' si prefieres un formato más sencillo
        },
        # Opcional: Handler para escribir en un archivo de log
        'file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(Path(__file__).resolve().parent, 'django.log'),
            'formatter': 'verbose',
        },
    },
    'root': {  # Logger raíz: afecta a todos los mensajes de log
        'handlers': ['console', 'file'],  # O solo 'console' si no deseas escribir en archivo
        'level': 'DEBUG',  # Ajusta el nivel (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    },
    'loggers': {
        'django': {  # Logger para los mensajes internos de Django
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        # Logger para tus módulos, por ejemplo, si tu app se llama "visits"
        'visits': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}