from django.apps import AppConfig


class BackendConfig(AppConfig):
    name = "backend"

    def ready(self):
        # Import signals to ensure receivers are registered on startup
        import backend.signals  # noqa: F401
