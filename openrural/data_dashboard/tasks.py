from celery.task import Task
from celery.registry import tasks

from openrural.retrieval.corporations import CorporationsScraper


class CorporationsTask(Task):

    name = 'openrural.corporations'

    def run(self):
        logger = self.get_logger()
        logger.info("Starting corporations task")
        CorporationsScraper(clear=False).run()
        logger.info("Stopping corporations task")


tasks.register(CorporationsTask)
