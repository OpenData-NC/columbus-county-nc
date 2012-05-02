from celery.registry import tasks

from django.core.management.base import BaseCommand

from openrural.data_dashboard import tasks as dashboard_tasks


class Command(BaseCommand):
    help = 'Run celery task from management command'

    def handle(self, *args, **options):
        task_name = args[0]
        try:
            Task = tasks[task_name]
        except KeyError:
            raise Exception('Task not found!')
        Task.delay()
