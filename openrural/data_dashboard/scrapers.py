
import json
import urllib
import urllib2
import logging
import datetime
import traceback

import ebdata.retrieval.log  # sets up base handlers.
from ebdata.retrieval.scrapers.base import BaseScraper
from ebpub.geocoder import GeocodingException, ParsingError, AmbiguousResult

from openrural.error_log import models as error_log
from django.core.urlresolvers import NoReverseMatch


logging.getLogger().setLevel(logging.DEBUG)


class DataScraper(BaseScraper):

    slug = None
    geocoder_type = 'openblock'

    def __init__(self, *args, **kwargs):
        clear = kwargs.pop('clear', False)
        super(ScraperWikiScraper, self).__init__(*args, **kwargs)
        if clear:
            self._create_schema()
        # these are incremented by NewsItemListDetailScraper
        self.num_added = 0
        self.num_changed = 0
        self.num_skipped = 0
        self.batch = \
            error_log.GeocodeBatch.objects.create(scraper=self.schema_slugs[0])
        self.geocode_log = None
        if self.geocoder_type == 'google':
            from openrural.retrieval.geocoders import GoogleGeocoder
            self._geocoder = GoogleGeocoder()

    # def update(self):
    #     super(ScraperWikiScraper, self).update()
    #     self.batch.end_time = datetime.datetime.now()
    #     self.batch.num_added = self.num_added
    #     self.batch.num_changed = self.num_changed
    #     self.batch.num_skipped = self.num_skipped
    #     self.batch.save()

    # def geocode(self, location_name, zipcode=None):
    #     """
    #     Tries to geocode the given location string, returning a Point object
    #     or None.
    #     """
    #     self.geocode_log = error_log.Geocode(
    #         batch=self.batch,
    #         scraper=self.schema_slugs[0],
    #         location=location_name,
    #         zipcode=zipcode or '',
    #     )
    #     self.batch.num_geocoded += 1
    #     # Try to lookup the adress, if it is ambiguous, attempt to use
    #     # any provided zipcode information to resolve the ambiguity.
    #     # The zipcode is not included in the initial pass because it
    #     # is often too picky yeilding no results when there is a
    #     # legitimate nearby zipcode identified in either the address
    #     # or street number data.
    #     try:
    #         loc = self._geocoder.geocode(location_name)
    #         self.batch.num_geocoded_success += 1
    #         return loc
    #     except AmbiguousResult as result:
    #         # try to resolve based on zipcode...
    #         if zipcode is None:
    #             self.logger.info(
    #                 "Ambiguous results for address %s. (no zipcode to resolve dispute)" %
    #                 (location_name, ))
    #             return None
    #         in_zip = [r for r in result.choices if r['zip'] == zipcode]
    #         if len(in_zip) == 0:
    #             self.logger.info(
    #                 "Ambiguous results for address %s, but none in specified zipcode %s" %
    #                 (location_name, zipcode))
    #             return None
    #         elif len(in_zip) > 1:
    #             self.logger.info(
    #                 "Ambiguous results for address %s in zipcode %s, guessing first." %
    #                 (location_name, zipcode))
    #             return in_zip[0]
    #         else:
    #             return in_zip[0]
    #     except (GeocodingException, ParsingError, NoReverseMatch) as e:
    #         self.geocode_log.success = False
    #         self.geocode_log.name = type(e).__name__
    #         self.geocode_log.description = traceback.format_exc()
    #         self.logger.error(unicode(e))
    #         return None

    # def create_newsitem(self, attributes, **kwargs):
    #     news_item = super(ScraperWikiScraper, self).create_newsitem(attributes,
    #                                                                 **kwargs)
    #     self.geocode_log.news_item = news_item
    #     self.geocode_log.save()
    #     return news_item
