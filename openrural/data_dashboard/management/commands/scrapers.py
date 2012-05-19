from optparse import make_option

from celery.registry import tasks

from django.core.management.base import BaseCommand

from openrural.data_dashboard import tasks as dashboard_tasks


class Command(BaseCommand):
    help = 'Run celery task from management command'
    option_list = BaseCommand.option_list + (
        make_option("-c", "--clear", action="store_true", default=False),
    )

    def handle(self, *args, **options):
        task_name = args[0]
        try:
            Task = tasks[task_name]
        except KeyError:
            raise Exception('Task not found!')
        Task.delay(clear=options['clear'])
