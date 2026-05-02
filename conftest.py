from django.conf import settings


def pytest_configure():
    if not settings.configured:
        settings.configure(
            DBT_KEY='test-key',
            GOOGLE_TTS_LANGUAGE_CODE='lv-LV',
            GOOGLE_TTS_VOICE_NAME='lv-LV-Chirp3-HD-Sadachbia',
            GOOGLE_TTS_SAMPLE_RATE_HERTZ=24000,
            AUDIO_BUCKET_NAME='test-audio-bucket',
            AUDIO_SIGNED_URL_TTL_SECONDS=3600,
            # A minimal set of settings required for DRF and Django to run
            # tests
            INSTALLED_APPS=[
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'rest_framework',
                'bible',
            ],
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            # Minimal middleware setup
            MIDDLEWARE=[
                'django.middleware.security.SecurityMiddleware',
                'django.contrib.sessions.middleware.SessionMiddleware',
                'django.middleware.common.CommonMiddleware',
                'django.middleware.csrf.CsrfViewMiddleware',
                'django.contrib.auth.middleware.AuthenticationMiddleware',
                'django.contrib.messages.middleware.MessageMiddleware',
                'django.middleware.clickjacking.XFrameOptionsMiddleware',
            ],
            # Needed for APIRequestFactory
            ROOT_URLCONF='bible.urls',
            # Suppress warning about default secret key
            SECRET_KEY='a-test-secret-for-pytest',
        )
