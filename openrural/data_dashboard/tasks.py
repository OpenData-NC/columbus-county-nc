from celery.task import Task, PeriodicTask
from celery.registry import tasks
from datetime import timedelta

from openrural.retrieval.corporations import CorporationsScraper
from openrural.retrieval.addresses import AddressesScraper
from openrural.retrieval.whiteville_props import PropsScraper
from openrural.retrieval.whiteville_restaurants import RestaurantsScraper
from openrural.retrieval.whiteville_news import WhitevilleNewsScraper
from openrural.retrieval.schools import WhitevilleSchoolsScraper
from openrural.retrieval.incidents import WhitevilleIncidentsScraper
from openrural.retrieval.arrests import WhitevilleArrestsScraper


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
        RestaurantsScraper(clear=clear).run()
        logger.info("Stopping restaurant inspections task")


class WhitevilleNewsTask(PeriodicTask):

    name = 'openrural.newsreporter'
    run_every = timedelta(minutes=30)

    def run(self, clear=False):
        logger = self.get_logger()
        logger.info("Starting news reporter task")
        WhitevilleNewsScraper(clear=clear).run()
        logger.info("Stopping news reporter task")


class WhitevilleSchoolsTask(PeriodicTask):

    name = 'openrural.schools'
    run_every = timedelta(days=1)

    def run(self, clear=False):
        logger = self.get_logger()
        logger.info("Starting school task")
        WhitevilleSchoolsScraper(clear=clear).run()
        logger.info("Stopping school task")


class WhitevilleIncidentsTask(PeriodicTask):

    name = 'openrural.incidents'
    run_every = timedelta(days=1)

    def run(self, clear=False):
        logger = self.get_logger()
        logger.info("Starting incidents task")
        WhitevilleIncidentsScraper(clear=clear).run()
        logger.info("Stopping incidents task")


class WhitevilleArrestsTask(PeriodicTask):

    name = 'openrural.arrests'
    run_every = timedelta(days=1)

    def run(self, clear=False):
        logger = self.get_logger()
        logger.info("Starting arrests task")
        WhitevilleArrestsScraper(clear=clear).run()
        logger.info("Stopping arrests task")

tasks.register(CorporationsTask)
tasks.register(AddressesTask)
tasks.register(PropertyTransactionsTask)
tasks.register(RestaurantInspectionsTask)
tasks.register(WhitevilleNewsTask)
tasks.register(WhitevilleSchoolsTask)
tasks.register(WhitevilleIncidentsTask)
tasks.register(WhitevilleArrestsTask)
