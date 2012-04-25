import pprint
import logging
import datetime
import traceback
import collections

from django.core.urlresolvers import NoReverseMatch

from ebpub import geocoder
from ebpub.geocoder import GeocodingException, ParsingError, AmbiguousResult
from ebpub.geocoder.base import full_geocode

from openrural.data_dashboard.models import Scraper, Run, Geocode


class DashboardMixin(object):
    """Scraper mixin with specific overrides to hook into Data Dashboard"""

    geocoder = geocoder.SmartGeocoder()

    def __init__(self, *args, **kwargs):
        clear = kwargs.pop('clear', False)
        # use defaultdict here (Python 2.6 doesn't have collections.Counter)
        self.counter = collections.defaultdict(lambda: 0)
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
        geocoded = self.counter['Geocoded']
        success = self.counter['Geocoded Success']
        if geocoded > 0:
            rate = float(success) / geocoded
        else:
            rate = 0.0
        self.counter['Geocoded Success Rate'] = '{0:.2%}'.format(rate)
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

    def create_newsitem(self, attributes, **kwargs):
        """Override to associate NewsItem to Geocode object"""
        news_item = super(DashboardMixin, self).create_newsitem(attributes,
                                                                **kwargs)
        if self.geocode_log is None:
            self.geocode_log = Geocode(
                run=self.run,
                scraper=self.schema_slugs[0],
                location=news_item.location_name,
                name='No Geocode',
                success=False,
            )
        self.geocode_log.news_item = news_item
        self.geocode_log.save()
        return news_item

    def geocode(self, location_name, **kwargs):
        self.counter['Geocoded'] += 1
        self.geocode_log = Geocode(
            run=self.run,
            scraper=self.schema_slugs[0],
            location=location_name,
        )
        self.geocode_log.description = pprint.pformat(kwargs)
        try:
            result = full_geocode(location_name, guess=True, **kwargs)
        except (geocoder.GeocodingException, geocoder.ParsingError, NoReverseMatch) as e:
            self.geocode_log.success = False
            self.geocode_log.name = type(e).__name__
            self.counter['Geocode Exception - %s' % type(e).__name__] += 1
            self.geocode_log.description += '\n\n%s' % traceback.format_exc()
            self.logger.error(unicode(e))
            return None
        self.geocode_log.description += '\n\n%s' % pprint.pformat(result)
        if result['ambiguous'] is True:
            self.geocode_log.success = False
            self.geocode_log.name = 'Ambiguous %s' % result['type']
            self.counter['Geocode Exception - %s' % self.geocode_log.name] += 1
            self.logger.error('Ambiguous result for %s' % location_name)
            return None
        self.counter['Geocoded Success'] += 1
        return result['result']

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
