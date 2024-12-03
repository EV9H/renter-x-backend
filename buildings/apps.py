from django.apps import AppConfig


class BuildingsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "buildings"
    def ready(self):
        import buildings.signals