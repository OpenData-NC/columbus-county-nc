#!/usr/bin/env python

import sys
import datetime
from optparse import OptionParser

from ebpub.db.models import NewsItem, Schema, Location
from ebpub.utils.script_utils import add_verbosity_options

from ebdata.nlp import places
from ebdata.retrieval.scrapers.list_detail import RssListDetailScraper, SkipRecord
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebdata.textmining.treeutils import text_from_html

from openrural.data_dashboard.scrapers import DashboardMixin


class WhitevilleNewsScraper(DashboardMixin, RssListDetailScraper, NewsItemListDetailScraper):
    # scraper settings
    logname = 'newsreporter'
    schema_slugs = ('news-reporter',)

    # Rerfers to whether a detail page exists for a downloaded item
    has_detail = False

    def __init__(self, *args, **kwargs):
        super(WhitevilleNewsScraper, self).__init__(*args, **kwargs)
        self.grabber = places.location_grabber(ignore_location_types=[])

    def list_pages(self):
        yield self.fetch_data('http://www.whiteville.com/search/?t=article&l=100&&sd=desc&c[]=news,news/*&f=atom')

    def existing_record(self, record):
        qs = NewsItem.objects.filter(schema__id=self.schema.id, url=record['url'])
        try:
            return qs[0]
        except IndexError:
            return None

    def clean_list_record(self, record):
        date = datetime.date(*record['updated_parsed'][:3])
        description = record['summary']

        # This feed doesn't provide geographic data; we'll try to
        # extract addresses from the text, and stop on the first
        # one that successfully geocodes.
        # First we'll need some suitable text; throw away HTML tags.
        full_description = record['content'][0]['value']
        full_description = text_from_html(full_description)
        # This method on the RssListDetailScraper does the rest.
        location, location_name = self.get_point_and_location_name(
            record, address_text=full_description)

        if not (location or location_name):
            locs = self.grabber(full_description)
            if locs:
                location_name = locs[0][2]
                location = Location.objects.get(name=location_name).location

        if not (location or location_name):
            raise SkipRecord("No location or location_name")

        cleaned = {
            'item_date': date,
            'location': location,
            'location_name': location_name,
            'title': record['title'],
            'description': description,
            'url': record['link']
       }
        return cleaned

    def save(self, old_record, list_record, detail_record):
        self.create_or_update(old_record, None, **list_record)

    def _create_schema(self):
        try:
            Schema.objects.get(slug=self.schema_slugs[0]).delete()
        except Schema.DoesNotExist:
            pass
        schema = Schema.objects.create(
            name='News Reporter News Item',
            plural_name='News Reporter News Items',
            indefinite_article = 'a',
            slug=self.schema_slugs[0],
            last_updated=datetime.datetime.now(),
            is_public=True,
            has_newsitem_detail=True,
            allow_charting=True,
        )


def main():
    parser = OptionParser()
    parser.add_option('-c', '--clear', help='Clear schema',
                      action="store_true", dest="clear")
    add_verbosity_options(parser)
    opts, args = parser.parse_args(sys.argv)
    WhitevilleNewsScraper(clear=opts.clear).run()


if __name__ == '__main__':
    sys.exit(main())
