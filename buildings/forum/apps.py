from django.apps import AppConfig

class ForumConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'buildings.forum'
    label = 'forum'
    verbose_name = 'Forum'

    def ready(self):
        """
        Override this to put in:
        - Add system checks
        - Register signals
        """
        pass