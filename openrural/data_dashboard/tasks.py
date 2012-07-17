from celery.task import Task, PeriodicTask
from celery.registry import tasks
from datetime import timedelta

from openrural.retrieval.corporations import CorporationsScraper
from openrural.retrieval.addresses import AddressesScraper
from openrural.retrieval.whiteville_props import PropsScraper
from openrural.retrieval.whiteville_restaurants import RestaurantsScraper


class CorporationsTask(PeriodicTask):

    name = 'openrural.corporations'
    run_every = timedelta(hours=6)

    def run(self, clear=False):
        logger = self.get_logger()
        logger.info("Starting corporations task")
        CorporationsScraper(clear=clear).run()
        logger.info("Stopping corporations task")


class AddressesTask(PeriodicTask):

    name = 'openrural.addresses'
    run_every = timedelta(days=1)

    # we always want to reimport all addresses, so set clear=True
    def run(self, clear=True):
        logger = self.get_logger()
        logger.info("Starting address task")
        AddressesScraper(clear=clear).run()
        logger.info("Stopping address task")


class PropertyTransactionsTask(PeriodicTask):

    name = 'openrural.properties'
    run_every = timedelta(days=1)

    def run(self, clear=False):
        logger = self.get_logger()
        logger.info("Starting properties task")
        PropsScraper(clear=clear).run()
        logger.info("Stopping properties task")


class RestaurantInspectionsTask(PeriodicTask):

    name = 'openrural.restaurants'
    run_every = timedelta(days=1)

    def run(self, clear=False):
        logger = self.get_logger()
        logger.info("Starting restaurant inspections task")
        PropsScraper(clear=clear).run()
        logger.info("Stopping restaurant inspections task")


tasks.register(CorporationsTask)
tasks.register(AddressesTask)
tasks.register(PropertyTransactionsTask)
tasks.register(RestaurantInspectionsTask)
