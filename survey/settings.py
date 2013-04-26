from django.conf import settings

LOGIN_URL = getattr(settings, "LOGIN_URL", "/")
