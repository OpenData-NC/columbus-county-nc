
import json
import urllib
import urllib2
import logging
import datetime
import traceback
import collections

import ebdata.retrieval.log  # sets up base handlers.
from ebdata.retrieval.scrapers.base import BaseScraper
from ebpub.geocoder import GeocodingException, ParsingError, AmbiguousResult

from openrural.data_dashboard.models import Scraper, Run


class DashboardMixin(object):
    """Scraper mixin with specific overrides to hook into data dashboard"""

    geocoder_type = 'openblock'

    def __init__(self, *args, **kwargs):
        clear = kwargs.pop('clear', False)
        # use defaultdict here (Python 2.6 doesn't have collections.Counter)
        self.counter = collections.defaultdict(lambda x: 0)
        super(DashboardMixin, self).__init__(*args, **kwargs)
        # create data_dashboard-specific logger here, otherwise eb.*
        # loggers get hijacked by ebdata.retrieval.log
        logger_name = 'data_dashboard.scraper.%s' % self.logname
        self.logger = logging.getLogger(logger_name)
        if clear and hasattr(self, '_create_schema'):
            self._create_schema()
        self.geocode_log = None

    def start_run(self):
        self.logger.info('Starting...')
        schema_slug = self.schema_slugs[0]
        self.scraper, _ = Scraper.objects.get_or_create(slug=self.logname,
                                                        schema=schema_slug)
        self.run = self.scraper.runs.create()

    def end_run(self):
        self.logger.info('Ending...')
        for name, value in self.counter.iteritems():
            self.run.stats.create(name=name, value=value)
        self.run.end_date = datetime.datetime.now()
        self.run.save()

    def run(self, *args, **kwargs):
        self.start_run()
        try:
            self.update(*args, **kwargs)
        except (KeyboardInterrupt, SystemExit):
            self.logger.warning('KeyboardInterrupt or SystemExit')
        self.end_run()

    @property
    def num_added(self):
        return self.counter['Added']

    @num_added.setter
    def num_added(self, x):
        self.counter['Added'] = x

    @property
    def num_changed(self):
        return self.counter['Changed']

    @num_added.setter
    def num_changed(self, x):
        self.counter['Changed'] = x

    @property
    def num_changed(self):
        return self.counter['Skipped']

    @num_added.setter
    def num_changed(self, x):
        self.counter['Skipped'] = x
