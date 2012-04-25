#!/usr/bin/env python

import sys
import datetime
from optparse import OptionParser

from ebpub import geocoder
from ebpub.db.models import NewsItem, Schema, SchemaField
from ebpub.utils.script_utils import add_verbosity_options

from openrural.retrieval.base.scraperwiki import ScraperWikiScraper
from openrural.data_dashboard.scrapers import DashboardMixin


class Scraper(DashboardMixin, ScraperWikiScraper):

    # scraper settings
    logname = 'corporations-scraper'
    schema_slugs = ('corporations',)

    # ScraperWiki settings
    scraper_name = "nc_secretary_of_state_corporation_filings"
    list_filter = {'Status': 'Current-Active', 'PrinCounty': 'Columbus'}
    ordering = 'DateFormed ASC'

    has_detail = False

    def save(self, old_record, data, detail_record):
        date, time = data['DateFormed'].split('T', 1)
        item_date = datetime.datetime.strptime(date, "%Y-%m-%d")
        attrs = {
            'citizenship': data['Citizenship'],
            'type': data['Type'],
            'sosid': data['SOSID'],
            'agent': data['RegAgent'],
        }
        address_parts = {
            'line1': data['PrinAddr1'],
            'line2': data['PrinAddr2'],
            'city': data['PrinCity'],
            'state': data['PrinState'],
            'zip': data['PrinZip'],
        }
        if address_parts['line1'] == 'None':
            self.logger.debug("{0} has no address, skipping".format(*data))
            return
        if address_parts['line2']:
            address_parts['line1'] = address_parts['line2']
        address = "{line1} {line2}".format(**address_parts)
        item = self.create_or_update(
            old_record,
            attrs,
            title=data['CorpName'],
            item_date=item_date,
            location_name=address,
            city=address_parts['city'],
            state=address_parts['state'],
            zipcode=address_parts['zip'],
            convert_to_block=True,
        )

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id)
            qs = qs.by_attribute(self.schema_fields['sosid'], record['SOSID'])
            return qs[0]
        except IndexError:
            return None

    def _create_schema(self):
        try:
            Schema.objects.get(slug=self.schema_slugs[0]).delete()
        except Schema.DoesNotExist:
            pass
        schema = Schema.objects.create(
            name='Corporation',
            plural_name='corporations',
            slug=self.schema_slugs[0],
            last_updated=datetime.datetime.now(),
            is_public=True,
            indefinite_article='a',
            has_newsitem_detail=True,
        )
        SchemaField.objects.create(
            schema=schema,
            pretty_name="Type",
            pretty_name_plural="Types",
            real_name='varchar01',
            name='type',
        )
        SchemaField.objects.create(
            schema=schema,
            pretty_name="Registered Agent",
            pretty_name_plural="Registered Agents",
            real_name='varchar02',
            name='agent',
        )
        SchemaField.objects.create(
            schema=schema,
            pretty_name="Citizenship",
            pretty_name_plural="Citizenships",
            real_name='varchar03',
            name='citizenship',
        )
        SchemaField.objects.create(
            schema=schema,
            pretty_name="SOSID",
            pretty_name_plural="SOSIDs",
            real_name='int01',
            name='sosid',
        )


def main():
    parser = OptionParser()
    parser.add_option('-c', '--clear', help='Clear schema',
                      action="store_true", dest="clear")
    add_verbosity_options(parser)
    opts, args = parser.parse_args(sys.argv)
    Scraper(clear=opts.clear).run()


if __name__ == '__main__':
    sys.exit(main())
