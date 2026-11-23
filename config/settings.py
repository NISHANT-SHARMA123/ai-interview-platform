"""
Django settings for Online Mock Interview Platform.
Built with Django 5.1, PostgreSQL 16, and modern security hardening.
"""

from pathlib import Path
import environ
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# Initialize environment variables
env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, 'django-insecure-mock-interview-dev-key-change-in-production-!#99'),
    ALLOWED_HOSTS=(list, ['127.0.0.1', 'localhost']),
    DB_ENGINE=(str, 'django.db.backends.postgresql'),
    DB_NAME=(str, 'mock_interview_db'),
    DB_USER=(str, 'interview_app_user'),
    DB_PASSWORD=(str, 'SecureAppUserPassword123!'),
    DB_HOST=(str, 'localhost'),
    DB_PORT=(str, '5432'),
    DEFAULT_AI_PROVIDER=(str, 'gemini'),
    GEMINI_API_KEY=(str, ''),
    GEMINI_MODEL=(str, 'gemini-2.5-flash'),
    GROQ_API_KEY=(str, ''),
    GROQ_MODEL=(str, 'llama-3.3-70b-versatile'),
    AI_REQUEST_TIMEOUT=(int, 15),
    GOOGLE_CLIENT_ID=(str, ''),
    GOOGLE_CLIENT_SECRET=(str, ''),
    CSRF_TRUSTED_ORIGINS=(list, ['http://127.0.0.1:8000', 'http://localhost:8000']),
)

# Read .env file if it exists
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env('ALLOWED_HOSTS')
CSRF_TRUSTED_ORIGINS = env('CSRF_TRUSTED_ORIGINS')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party hardening
    'axes',

    # Core Platform Apps
    'accounts.apps.AccountsConfig',
    'interviews.apps.InterviewsConfig',
    'analytics.apps.AnalyticsConfig',
    'ai_engine.apps.AiEngineConfig',
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
    'axes.middleware.AxesMiddleware',
    'config.middleware.SecurityHeadersMiddleware',
]

AUTHENTICATION_BACKENDS = [
    # AxesStandaloneBackend handles login tracking and lockouts
    'axes.backends.AxesStandaloneBackend',
    # Default ModelBackend
    'django.contrib.auth.backends.ModelBackend',
]

ROOT_URLCONF = 'config.urls'

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

WSGI_APPLICATION = 'config.wsgi.application'

# Database Configuration (Supports DATABASE_URL in production or local DB_* vars)
if os.environ.get('DATABASE_URL'):
    DATABASES = {
        'default': {**env.db('DATABASE_URL'), 'CONN_MAX_AGE': 60}
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': env('DB_ENGINE'),
            'NAME': env('DB_NAME'),
            'USER': env('DB_USER'),
            'PASSWORD': env('DB_PASSWORD'),
            'HOST': env('DB_HOST'),
            'PORT': env('DB_PORT'),
            'CONN_MAX_AGE': 60,
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images, MediaPipe WASM & Models)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}

# Media Files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# -----------------------------------------------------------------------------
# Security & Headers Hardening
# -----------------------------------------------------------------------------
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Session & Cookie Security
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False  # Allows client-side Vanilla JS fetch calls to read CSRF token
CSRF_COOKIE_SAMESITE = 'Lax'

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# -----------------------------------------------------------------------------
# Django-Axes (Login Throttling & Brute Force Defense)
# -----------------------------------------------------------------------------
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 15  # Minutes
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_CALLABLE = None
AXES_VERBOSE = True

# -----------------------------------------------------------------------------
# AI Engine Configuration
# -----------------------------------------------------------------------------
DEFAULT_AI_PROVIDER = env('DEFAULT_AI_PROVIDER')
GEMINI_API_KEY = env('GEMINI_API_KEY')
GEMINI_MODEL = env('GEMINI_MODEL')
GROQ_API_KEY = env('GROQ_API_KEY')
GROQ_MODEL = env('GROQ_MODEL')
AI_REQUEST_TIMEOUT = env('AI_REQUEST_TIMEOUT')

# Google OAuth Configuration
GOOGLE_CLIENT_ID = env('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = env('GOOGLE_CLIENT_SECRET')

# Content Security Policy (CSP) headers config for MediaPipe WASM, WebWorkers & Google OAuth
CSP_HEADER_POLICY = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' 'wasm-unsafe-eval' blob: https://fonts.googleapis.com https://accounts.google.com https://apis.google.com https://cdn.jsdelivr.net; "
    "worker-src 'self' blob:; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://accounts.google.com; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "img-src 'self' data: blob: https://lh3.googleusercontent.com https://ssl.gstatic.com; "
    "media-src 'self' blob:; "
    "connect-src 'self' https://accounts.google.com https://oauth2.googleapis.com https://www.googleapis.com https://cdn.jsdelivr.net https://storage.googleapis.com; "
    "frame-src https://accounts.google.com; "
    "frame-ancestors 'none';"
)