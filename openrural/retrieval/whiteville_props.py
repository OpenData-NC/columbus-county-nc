#!/usr/bin/env python

import sys
import logging
import datetime
from optparse import OptionParser
from tempfile import mkdtemp
from string import capwords

from django.contrib.gis.gdal import DataSource

from ebpub.db.models import NewsItem, Schema, SchemaField
from ebpub.utils.script_utils import add_verbosity_options, unzip

from openrural.retrieval.base.scraperwiki import ScraperWikiScraper
from openrural.data_dashboard.scrapers import DashboardMixin

logger = logging.getLogger('openrural.retrieval.whiteville_props')

class PropsScraper(DashboardMixin, ScraperWikiScraper):
    # scraper settings
    logname = 'properties'
    schema_slugs = ('properties',)

    # ScraperWiki settings
    scraper_name = 'daily_columbus_county_nc_property_sales'

    # Rerfers to whether a detail page exists for a downloaded item
    has_detail = False

    def __init__(self, *args, **kwargs):
        super(PropsScraper, self).__init__(*args, **kwargs)

        addresses_url = 'http://www.columbusco.org/GISData/Addresses.zip'
        parcels_url = 'http://www.columbusco.org/GISData/parcels.zip'

        directory = mkdtemp(suffix='props-shapefiles')
        for url in [addresses_url, parcels_url]:
            filename = self.retriever.get_to_tempfile(uri=url)
            unzip(filename=filename, cwd=directory)

        address_layer = DataSource('%s/Addresses.shp' % directory)[0]
        addr_feature_by_prop = {}
        for feature in address_layer:
            addr_feature_by_prop[int(feature.get('PROP'))] = feature
        self.addr_features = addr_feature_by_prop

        parcels_layer = DataSource('%s/parcel.shp' % directory)[0]
        parcel_feature_by_prop = {}
        for feature in parcels_layer:
            parcel_feature_by_prop[int(feature.get('VIEWINFO'))] = feature
        self.parcel_features = parcel_feature_by_prop

    def existing_record(self, record):
        record_date = self.parse_date(record['DATE'])
        if record_date:
            try:
                qs = NewsItem.objects.filter(schema__id=self.schema.id, item_date=record_date)
                qs = qs.by_attribute(self.schema_fields['prop'], int(record['PROP']))
                return qs[0]
            except IndexError:
                return None

    def save(self, old_record, data, detail_record):
        item_date = self.parse_date(data['DATE'])
        prop_val = int(data['PROP'])
        addr_feature = self.addr_features.get(prop_val)
        parcel_feature = self.parcel_features.get(prop_val)

        if item_date and parcel_feature:
            attrs = {
                'prop': prop_val,
                'owner_name': capwords(data['GRANTEE']),
                'previous_owner': capwords(data['GRANTOR']),
                'acres': '%s' % data['ACRES'],
                'tax_value': int(data['APPRAISAL']),
                'sale_amount': int(data['SALE']),
                'prop_card': 'http://webtax.columbusco.org/prc/pid%06d.pdf' % prop_val
            }

            transformed_point = parcel_feature.geom.transform(4326, True)
            if addr_feature:
                location_name = capwords(str(addr_feature['FULLADD']))
                city = capwords(str(addr_feature['CITY']))
                zipcode = str(addr_feature['ZIP'])
            else:
                location_name = 'Property %s (address unknown)' % prop_val
                city = zipcode = ''

            self.create_or_update(
                old_record,
                attrs,
                title=location_name,
                url=str(addr_feature['PhotoImage']) if addr_feature else '',
                item_date=item_date,
                location=transformed_point.geos,
                location_name=location_name,
                city=city,
                zipcode=zipcode,
            )

    def parse_date(self, float_value):
        int_value = int(float_value)
        if int_value != 0:
            string_value = '%s' % int(float_value)
            if len(string_value) == 7:
                string_value = '0%s' % string_value

            if len(string_value) != 8:
                self.logger.error('Unable to parse %s into year, month, day.' % float_value)
            else:
                mm = int(string_value[0:2])
                dd = int(string_value[2:4])
                year = int(string_value[-4:])
                try:
                    return datetime.date(year, mm, dd)
                except ValueError, e:
                    message = 'Unable to parse date %s (year=%s, month=%s, day=%s): %s' % (
                        string_value, year, mm, dd, e)
                    self.logger.error(message)

    def _create_schema(self):
        try:
            Schema.objects.get(slug=self.schema_slugs[0]).delete()
        except Schema.DoesNotExist:
            pass

        schema = Schema.objects.create(
            name='Property Transaction',
            indefinite_article='A',
            plural_name='Property Transactions',
            slug=self.schema_slugs[0],
            last_updated=datetime.datetime.now(),
            is_public=True,
            has_newsitem_detail=True,
            short_source="Columbus County Tax Office",
            allow_charting=True,
            date_name='Sale Date',
            date_name_plural='Sale Dates',
        )

        SchemaField.objects.create(
            schema=schema,
            name='owner_name',
            pretty_name='Buyer/Grantee',
            pretty_name_plural='Buyers/Grantees',
            real_name='varchar01',
        )

        SchemaField.objects.create(
            schema=schema,
            name='previous_owner',
            pretty_name='Seller/Grantor',
            pretty_name_plural='Sellers/Grantors',
            real_name='varchar04',
        )

        SchemaField.objects.create(
            schema=schema,
            name='prop_card',
            pretty_name='Tax Information',
            pretty_name_plural='Tax Information',
            real_name='varchar02',
        )

        SchemaField.objects.create(
            schema=schema,
            name='prop',
            pretty_name='Property ID',
            pretty_name_plural='Property IDs',
            real_name='int01',
            display=False,
        )

        SchemaField.objects.create(
            schema=schema,
            name='acres',
            pretty_name='Acres',
            pretty_name_plural='Acres',
            real_name='varchar03',
        )

        SchemaField.objects.create(
            schema=schema,
            name='sale_amount',
            pretty_name='Sale Amount',
            pretty_name_plural='Sales Amounts',
            real_name='int02',
        )

        SchemaField.objects.create(
            schema=schema,
            name='tax_value',
            pretty_name='Tax Value',
            pretty_name_plural='Tax Values',
            real_name='int03',
        )


def main():
    parser = OptionParser()
    parser.add_option('-c', '--clear', help='Clear schema',
                      action="store_true", dest="clear")
    add_verbosity_options(parser)
    opts, args = parser.parse_args(sys.argv)
    PropsScraper(clear=opts.clear).run()


if __name__ == '__main__':
    sys.exit(main())
