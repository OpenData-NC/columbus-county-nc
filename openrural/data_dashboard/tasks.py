from celery.task import Task
from celery.registry import tasks

from openrural.retrieval.orange_corp_filings import CorporationsScraper


class CorporationsTask(Task):

    def run(self):
        logger = self.get_logger()
        logger.info("Starting corporations task")
        CorporationsScraper(clear=False).run()
        logger.info("Stopping corporations task")


tasks.register(CorporationsTask)
