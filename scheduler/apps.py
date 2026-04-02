from django.apps import AppConfig


class SchedulerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scheduler'
    verbose_name = 'Instagram Post Scheduler'

    def ready(self):
        """Start the APScheduler when Django starts."""
        import os
        # Only start scheduler in the main process (not in migrations or management commands)
        if os.environ.get('RUN_MAIN') == 'true':
            try:
                from scheduler.tasks import start_scheduler
                start_scheduler()
            except Exception as e:
                print(f"Warning: Could not start scheduler: {e}")
