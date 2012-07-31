from celery.task import Task, PeriodicTask
from celery.registry import tasks
from datetime import timedelta

from ebpub.db.bin.update_aggregates import update_all_aggregates

class AggregatesTask(PeriodicTask):

    name = 'openrural.aggregates'
    run_every = timedelta(hours=12)

    def run(self, dry_run=False, reset=False):
        logger = self.get_logger()
        logger.info("Starting aggregates task")
        update_all_aggregates(dry_run, reset)
        logger.info("Stopping aggregates task")

tasks.register(AggregatesTask)
