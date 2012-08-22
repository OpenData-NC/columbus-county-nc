#!/usr/bin/env python

import sys
import datetime
from string import capwords
from optparse import OptionParser

from ebpub.db.models import NewsItem, Schema, SchemaField
from ebpub.utils.script_utils import add_verbosity_options

from openrural.retrieval.base.scraperwiki import ScraperWikiScraper
from openrural.data_dashboard.scrapers import DashboardMixin


FACILITY_STATUS_CODES = {
    'A': 'Open for business.',
    'B': 'Closed for the season.',
    'C': 'Closed for business.',
    'D': 'Closed for nonpayment of fees.',
    'E': 'Closed due to violations.',
    'F': 'Closed for violating conditional permit.',
    'G': 'Permit permanently revoked.',
    'H': 'Permit invalid.',
    'I': 'New permit. First inspection.',
    'J': 'Permit expired.',
    'K': 'Open for business.',
    'L': 'Open for business.',
    'M': 'Open for business.',
    'S': 'Open for business.',
    'T': 'New permit. First inspection.',
    'U': 'New permit. First inspection.',
    'W': 'Permit faces suspension due to rule violation.',
    'X': 'Open for business.',
    'Z': 'No inspection required.'
}


class RestaurantsScraper(DashboardMixin, ScraperWikiScraper):
    # scraper settings
    logname = 'restaurants'
    schema_slugs = ('restaurants',)

    # ScraperWiki Settings
    scraper_name = 'restaurant'

    # Rerfers to whether a detail page exists for a downloaded item
    has_detail = False

    # Override base ScraperWikiScraper get_query
    def get_query(self, select='*', limit=10, offset=0):
        query = ['SELECT {0} FROM `facinfo` NATURAL JOIN `inspinfo`'.format(select)]
        query.append("WHERE FacilityID LIKE '07024%'")
        if self.ordering:
            query.append('ORDER BY {0}'.format(self.ordering))
        if limit > 0:
            query.append('LIMIT {0}'.format(limit))
        if offset > 0:
            query.append('OFFSET {0}'.format(offset))
        query = ' '.join(query)
        self.logger.debug(query)
        return query

    def existing_record(self, record):
        record_date = datetime.datetime.strptime(record['ACTIVITY_DATE'], "%Y-%m-%d").date()
        if record_date:
            try:
                qs = NewsItem.objects.filter(schema__id=self.schema.id, item_date=record_date)
                qs = qs.by_attribute(self.schema_fields['facility_id'], record['FacilityID'])
                return qs[0]
            except IndexError:
                return None

    def save(self, old_record, data, detail_record):
        item_date = datetime.datetime.strptime(data['ACTIVITY_DATE'], "%Y-%m-%d").date()
        status = data['STATUS_CODE']
        attrs = {
            'name': capwords(data['FAC_NAME']),
            'facility_id': data['FacilityID'],
            'score': data['ACTIVITY_FINAL_SCORE'],
            'status_code': self.get_or_create_lookup('status_code', status, status,
                description=FACILITY_STATUS_CODES[status]).id,
        }

        item = self.create_or_update(
            old_record,
            attrs,
            title=attrs['name'],
            item_date=item_date,
            location_name=capwords(data['ADDR_LINE1']),
            city=capwords(data['ADDR_CITY']),
            state=data['STATE_CODE'],
            zipcode=data['ADDR_ZIP5'],
        )

    def _create_schema(self):
        try:
            Schema.objects.get(slug=self.schema_slugs[0]).delete()
        except Schema.DoesNotExist:
            pass
        schema = Schema.objects.create(
            name='Restaurant Inspection',
            plural_name='Restaurant Inspections',
            indefinite_article = 'a',
            slug=self.schema_slugs[0],
            last_updated=datetime.datetime.now(),
            is_public=True,
            has_newsitem_detail=True,
            allow_charting=True,
        )
        SchemaField.objects.create(
            schema=schema,
            pretty_name="Establishment Name",
            pretty_name_plural="Establishment Names",
            real_name='varchar01',
            name='name',
        )
        SchemaField.objects.create(
            schema=schema,
            pretty_name="Facility ID",
            pretty_name_plural="Facility IDs",
            real_name='varchar02',
            name='facility_id',
            display=False,
        )
        SchemaField.objects.create(
            schema=schema,
            pretty_name="Score",
            pretty_name_plural="Scores",
            real_name='varchar03',
            name='score',
        )
        SchemaField.objects.create(
            schema=schema,
            is_lookup=True,
            pretty_name="Status Code",
            pretty_name_plural="Status Codes",
            real_name='int03',
            name='status_code',
        )


def main():
    parser = OptionParser()
    parser.add_option('-c', '--clear', help='Clear schema',
                      action="store_true", dest="clear")
    add_verbosity_options(parser)
    opts, args = parser.parse_args(sys.argv)
    RestaurantsScraper(clear=opts.clear).run()


if __name__ == '__main__':
    sys.exit(main())
