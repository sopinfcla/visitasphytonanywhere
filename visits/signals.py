from django.apps import AppConfig
from django.db.models.signals import post_migrate

def cleanup_slots_on_startup(sender, **kwargs):
    from .models import AvailabilitySlot
    cleaned = AvailabilitySlot.cleanup_old_slots()
    if cleaned > 0:
        print(f"[Startup] Se eliminaron {cleaned} slots antiguos sin citas asignadas")

class VisitsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'visits'

    def ready(self):
        post_migrate.connect(cleanup_slots_on_startup, sender=self)