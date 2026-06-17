
from django.apps import AppConfig

class InterviewConfig(AppConfig):
    name = 'interview'

    def ready(self):
        # Preload skillNER when Django starts
        # so first request isn't slow
        try:
            from core.skill_extractor import _load
            _load()
        except Exception as e:
            print(f"skillNER preload failed: {e}")