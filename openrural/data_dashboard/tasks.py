from celery.task import Task, PeriodicTask
from celery.registry import tasks
from datetime import timedelta

from openrural.retrieval.corporations import CorporationsScraper


class CorporationsTask(PeriodicTask):

    name = 'openrural.corporations'
    run_every = timedelta(hours=6)

    def run(self, clear=False):
        logger = self.get_logger()
        logger.info("Starting corporations task")
        CorporationsScraper(clear=clear).run()
        logger.info("Stopping corporations task")


tasks.register(CorporationsTask)
