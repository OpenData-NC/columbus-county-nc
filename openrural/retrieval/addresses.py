#!/usr/bin/env python

import sys
import datetime
from optparse import OptionParser

from django.template.defaultfilters import title

from ebpub import geocoder
from ebpub.db.models import NewsItem, Schema, SchemaField
from ebpub.utils.script_utils import add_verbosity_options

from openrural.retrieval.base.shapefile import ShapefileScraper
from openrural.data_dashboard.scrapers import DashboardMixin


class AddressesScraper(DashboardMixin, ShapefileScraper):

    # scraper settings
    logname = 'addresses'
    schema_slugs = ('addresses',)
    has_detail = False

    # ShapefileScraper settings
    url = "http://www.columbusco.org/GISData/Addresses.zip"

    def save(self, old_record, data, detail_record):
        item_date = datetime.date.today()
        attrs = {
            'city': title(str(data['CITY'])),
            'zipcode': str(data['ZIP']),
            'property_id': int(str(data['PROP'])),
        }
        address = title(str(data['FULLADD']))
        full_address = '%s, %s, NC %s' % (address, attrs['city'],
                                          attrs['zipcode'])
        item = self.create_or_update(
            old_record,
            attrs,
            title=address,
            item_date=item_date,
            location_name=address,
            city=attrs['city'],
            state='NC',
            zipcode=attrs['zipcode'],
        )

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id)
            qs = qs.by_attribute(self.schema_fields['property_id'],
                                 int(str(record['PROP'])))
            return qs[0]
        except IndexError:
            return None

    def create_newsitem(self, attributes, **kwargs):
        convert_to_block = kwargs.pop('convert_to_block', False)
        location, location_name = self.geocode_if_needed(
            kwargs.get('location', None),
            kwargs.get('location_name', None),
            zipcode=kwargs.pop('zipcode', None),
            city=kwargs.pop('city', None),
            state=kwargs.pop('state', None),
            convert_to_block=convert_to_block,
            )
        if self.geocode_log is None:
            self.geocode_log = Geocode(
                run=self.run,
                scraper=self.schema_slugs[0],
                location=location_name,
                name='No Geocode',
                status='failure',
            )
        self.geocode_log.save()
        self.logger.debug('Skipping news item creation... (faster)')
        self.num_added += 1

    def _create_schema(self):
        try:
            Schema.objects.get(slug=self.schema_slugs[0]).delete()
        except Schema.DoesNotExist:
            pass
        schema = Schema.objects.create(
            name='Address',
            plural_name='addresses',
            slug=self.schema_slugs[0],
            last_updated=datetime.datetime.now(),
            is_public=False,
            indefinite_article='an',
            has_newsitem_detail=False,
        )
        SchemaField.objects.create(
            schema=schema,
            pretty_name="Property ID",
            pretty_name_plural="property IDs",
            real_name='int01',
            name='property_id',
        )
        SchemaField.objects.create(
            schema=schema,
            pretty_name="City",
            pretty_name_plural="cities",
            real_name='varchar01',
            name='city',
        )
        SchemaField.objects.create(
            schema=schema,
            pretty_name="Zipcode",
            pretty_name_plural="zipcodes",
            real_name='varchar02',
            name='zipcode',
        )


def main():
    parser = OptionParser()
    parser.add_option('-c', '--clear', help='Clear schema',
                      action="store_true", dest="clear")
    add_verbosity_options(parser)
    opts, args = parser.parse_args(sys.argv)
    AddressesScraper(clear=opts.clear).run()


if __name__ == '__main__':
    sys.exit(main())
