import pprint
import logging
import datetime
import traceback
import collections

from django.core.urlresolvers import NoReverseMatch

from ebpub import geocoder
from ebpub.geocoder import GeocodingException, ParsingError, AmbiguousResult
from ebpub.geocoder.base import full_geocode
from ebpub.db.models import Schema

from openrural.data_dashboard.models import Scraper, Run, Geocode


LEGACY_COUNTERS = ('num_added', 'num_changed', 'num_skipped')


class DashboardMixin(object):
    """Scraper mixin with specific overrides to hook into Data Dashboard"""

    def __init__(self, *args, **kwargs):
        clear = kwargs.pop('clear', False)
        # use defaultdict here (Python 2.6 doesn't have collections.Counter)
        self.stats = collections.defaultdict(lambda: 0)
        # legacy support for counters
        for name in LEGACY_COUNTERS:
            setattr(self, name, 0)
        super(DashboardMixin, self).__init__(*args, **kwargs)
        # create data_dashboard-specific logger here, otherwise eb.*
        # loggers get hijacked by ebdata.retrieval.log
        logger_name = 'data_dashboard.scraper.%s' % self.logname
        self.logger = logging.getLogger(logger_name)
        # reset schema if it doesn't exist (first run)
        if not Schema.objects.filter(slug=self.schema_slugs[0]).exists():
            clear = True
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
        geocoded = self.stats['Geocoded']
        success = self.stats['Geocoded Success']
        if geocoded > 0:
            rate = float(success) / geocoded
        else:
            rate = 0.0
        self.stats['Geocoded Success Rate'] = '{0:.2%}'.format(rate)
        # save legacy counters
        for name in LEGACY_COUNTERS:
            self.stats[name] = getattr(self, name)
        for name, value in self.stats.iteritems():
            self.run.stats.create(name=name, value=value)
        self.run.end_date = datetime.datetime.now()
        if self.stats['num_added'] > 0 or self.stats['num_changed'] > 0:
            self.run.status = 'updated'
        else:
            self.run.status = 'skipped'
        self.run.save()

    def run(self, *args, **kwargs):
        self.start_run()
        self.run.status = 'running'
        self.run.save()
        try:
            self.update(*args, **kwargs)
        except Exception, e:
            self.logger.exception(e)
            self.run.status = 'failed'
            self.run.status_description = traceback.format_exc()
            self.run.save()
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
        self.stats['Geocoded'] += 1
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
            self.stats['Geocode Exception - %s' % type(e).__name__] += 1
            self.geocode_log.description += '\n\n%s' % traceback.format_exc()
            self.logger.error(unicode(e))
            return None
        self.geocode_log.description += '\n\n%s' % pprint.pformat(result)
        if result['ambiguous'] is True:
            self.geocode_log.success = False
            self.geocode_log.name = 'Ambiguous %s' % result['type']
            self.stats['Geocode Exception - %s' % self.geocode_log.name] += 1
            self.logger.error('Ambiguous result for %s' % location_name)
            return None
        self.stats['Geocoded Success'] += 1
        return result['result']

    def update_existing(self, newsitem, new_values, new_attributes):
        new_values.pop('convert_to_block', None)
        new_values.pop('city', None)
        new_values.pop('state', None)
        new_values.pop('zipcode', None)
        return super(DashboardMixin, self).update_existing(newsitem,
                                                           new_values,
                                                           new_attributes)
