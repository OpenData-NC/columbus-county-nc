#!/usr/bin/env python

import sys
import csv
import logging
import datetime
from optparse import OptionParser
from collections import defaultdict

from django.contrib.gis.gdal import DataSource

from ebpub.db.models import NewsItem, Schema, SchemaField
from ebdata.retrieval.scrapers.base import BaseScraper
from ebpub.utils.script_utils import add_verbosity_options, setup_logging_from_opts

logger = logging.getLogger('openrural.retrieval.whiteville_props')

class PropertyTransactions(BaseScraper):
    schema_slug = 'property-transactions'

    def __init__(self, *args, **kwargs):
        clear = kwargs.pop('clear', False)
        super(PropertyTransactions, self).__init__(*args, **kwargs)
        if clear:
            self._create_schema()
        self.schema = Schema.objects.get(slug=self.schema_slug)
        self.num_added = 0

    def update(self, csvreader, struct_layer, parcel_layer):
        struct_feature_by_prop = {}
        for feature in struct_layer:
            struct_feature_by_prop[int(feature.get('PROP'))] = feature

        parcel_feature_by_prop = {}
        for feature in parcel_layer:
            parcel_feature_by_prop[int(feature.get('PROP'))] = feature

        for item in csvreader:
            item_date = self.parse_date(item['SaleDate'])
            struct_feature = struct_feature_by_prop.get(int(item['Prop']))
            parcel_feature = parcel_feature_by_prop.get(int(item['Prop']))

            owner_address = item['Address1']
            for i in range(2, 4):
                item_field = item['Address%s' % i]
                if item_field:
                    owner_address = '%s / %s' % (owner_address, item_field)
            owner_address = '%s %s' % (owner_address, item['ZipCode'])

            if item_date and parcel_feature:

                attrs = {
                    'pin': item['PIN'],
                    'owner_name': item['Owner'],
                    'owner_address': owner_address,
                    'prop': item['Prop'],
                    'acres': item['Acres'],
                    'total_val': int(item['TotalVal']),
                    'sale_amt': int(item['SaleAmt']),
                    'year_built': int(item['YrBlt']),
                    'prop_card': str(struct_feature['PROPCARD']) if struct_feature else '',
                }

                transformed_point = parcel_feature.geom.transform(4326, True)
                if struct_feature:
                    location_name = '%s %s %s' % (struct_feature['FULLADD'], struct_feature['CITY'], struct_feature['ZIP'])
                else:
                    location_name = 'Property %s (address unknown)' % item['Prop']

                self.create_newsitem(
                    attrs,
                    title='Property %s' % item['Prop'],
                    url=struct_feature['PHOTO_URL'] if struct_feature else '',
                    item_date=item_date,
                    location=transformed_point.geos,
                    location_name=location_name.strip(),
                    zipcode=item['ZipCode']
                )

    def stats(self, csvreader, struct_layer, parcel_layer):
        struct_feature_by_prop = defaultdict(list)
        struct_feature_count = len(struct_layer)
        for feature in struct_layer:
            propval = int(feature.get('PROP'))
            struct_feature_by_prop[propval].append(feature)

        parcel_feature_by_prop = defaultdict(list)
        parcel_feature_count = len(parcel_layer)
        for feature in parcel_layer:
            propval = int(feature.get('PROP'))
            parcel_feature_by_prop[propval].append(feature)

        zero_date_count = 0
        invalid_date_count = 0
        props_missing_from_struct_shapefile = 0
        props_missing_from_parcel_shpaefile = 0
        item_count = 0
        valid_date_but_no_struct_feature = 0
        valid_date_but_no_parcel_feature = 0
        valid_date_but_multi_feature = 0
        valid_date_and_single_feature = 0
        item_by_prop = defaultdict(list)
        for rownum, item in enumerate(csvreader):
            item_count += 1
            propval = int(item['Prop'])
            item_by_prop[propval].append(item)
            item_date = item['SaleDate']
            if item_date == '0':
                zero_date_count += 1
                item_date = None
            else:
                item_date = self.parse_date(item_date, rownum=rownum)
                if item_date is None:
                    invalid_date_count += 1

            if item_date:
                if propval not in parcel_feature_by_prop:
                    valid_date_but_no_parcel_feature += 1

                if propval not in struct_feature_by_prop:
                    valid_date_but_no_struct_feature += 1
                else:
                    features = struct_feature_by_prop[propval]
                    if len(features) == 1:
                        valid_date_and_single_feature += 1
                    else:
                        valid_date_but_multi_feature += 1

        csv_props_missing_from_struct_shapefile = []
        for k in item_by_prop.keys():
            if k not in struct_feature_by_prop:
                csv_props_missing_from_struct_shapefile.append(k)

        csv_props_missing_from_parcel_shapefile = []
        for k in item_by_prop.keys():
            if k not in parcel_feature_by_prop:
                csv_props_missing_from_parcel_shapefile.append(k)

        self.logger.info('Struct shapefile has %s features with %s distinct properties.', struct_feature_count, len(struct_feature_by_prop))
        self.logger.info('Parcel shapefile has %s features with %s distinct properties.', parcel_feature_count, len(parcel_feature_by_prop))
        self.logger.info('CSV file has %s rows, with %s distinct properties.', item_count, len(item_by_prop))
        self.logger.info('CSV file has %s "0" dates, and %s invalid dates.', zero_date_count, invalid_date_count)
        self.logger.info('CSV file references %s properties not found in struct shapefile. ', len(csv_props_missing_from_struct_shapefile))
        self.logger.info('CSV file references %s properties not found in parcel shapefile. ', len(csv_props_missing_from_parcel_shapefile))

        valid_date_count = item_count - invalid_date_count - zero_date_count
        self.logger.info('%s CSV rows with valid dates. %s have no parcel mapping, %s have no struct mapping, %s have multiple mappings, %s have a single mapping.' % \
            (valid_date_count, valid_date_but_no_parcel_feature, valid_date_but_no_struct_feature, valid_date_but_multi_feature, valid_date_and_single_feature))


    def parse_date(self, string_value, rownum=None):
        if len(string_value) < 6 or len(string_value) > 8:
            self.logger.error('%sUnable to parse %s into year, month, day.' % (rownum and 'Row %s: ' % rownum or '', string_value))
        elif string_value != '0':
            year = int(string_value[-4:])
            mmdd = string_value[:-4]
            mmdd_len = len(mmdd)
            if mmdd_len == 2:
                mm = int(mmdd[0:1])
                dd = int(mmdd[1:2])
            elif mmdd_len == 4:
                mm = int(mmdd[0:2])
                dd = int(mmdd[2:4])
            else:
                if mmdd[2] != '0' and mmdd[0] == '1' and (mmdd[1] == '0' or mmdd[1] == '1' or mmdd[1] == '2'):
                    mm = int(mmdd[0:2])
                    dd = int(mmdd[2])
                else:
                    mm = int(mmdd[0])
                    dd = int(mmdd[1:3])
            try:
                return datetime.date(year, mm, dd)
            except ValueError, e:
                message = '%sUnable to parse date %s (year=%s, month=%s, day=%s): %s' % (rownum and 'Row %s: ' % rownum or '',
                    string_value, year, mm, dd, e)
                self.logger.error(message)

    def _create_schema(self):
        try:
            Schema.objects.get(slug=self.schema_slug).delete()
        except Schema.DoesNotExist:
            pass

        schema = Schema.objects.create(
            name='Property Transaction',
            indefinite_article='A',
            plural_name='Property Transactions',
            slug=self.schema_slug,
            last_updated=datetime.datetime.now(),
            is_public=True,
            has_newsitem_detail=True,
            short_source="Columbus County GIS department",
            allow_charting=True,
        )

        SchemaField.objects.create(
            schema=schema,
            name='pin',
            pretty_name='PIN',
            pretty_name_plural='PINs',
            real_name='varchar01',
        )

        SchemaField.objects.create(
            schema=schema,
            name='owner_name',
            pretty_name='Owner Name',
            pretty_name_plural='Owner Names',
            real_name='varchar02',
        )

        SchemaField.objects.create(
            schema=schema,
            name='owner_address',
            pretty_name='Owner Address',
            pretty_name_plural='Owner Addresses',
            real_name='varchar03',
        )

        SchemaField.objects.create(
            schema=schema,
            name='prop_card',
            pretty_name='URL of property card',
            pretty_name_plural='URLs of property cards',
            real_name='varchar04',
        )

        SchemaField.objects.create(
            schema=schema,
            name='prop',
            pretty_name='Property ID',
            pretty_name_plural='Property IDs',
            real_name='int01',
        )

        SchemaField.objects.create(
            schema=schema,
            name='acres',
            pretty_name='Acres',
            pretty_name_plural='Acres',
            real_name='varchar05',
        )

        SchemaField.objects.create(
            schema=schema,
            name='total_val',
            pretty_name='Total Value',
            pretty_name_plural='Total Values',
            real_name='int02',
        )

        SchemaField.objects.create(
            schema=schema,
            name='sale_amt',
            pretty_name='Sale Amount',
            pretty_name_plural='Sale Amounts',
            real_name='int03',
        )

        SchemaField.objects.create(
            schema=schema,
            name='year_built',
            pretty_name='Year Built',
            pretty_name_plural='Years Built',
            real_name='int04',
        )


def main():
    parser = OptionParser()
    parser.add_option('-c', '--clear', help='Clear schema',
                      action="store_true", dest="clear")
    parser.add_option('-s', '--stats', help='Report file stats only',
                      action="store_true", dest="stats")
    add_verbosity_options(parser)
    opts, args = parser.parse_args(sys.argv)
    setup_logging_from_opts(opts, logger)
    if len(args) != 4:
        parser.error("Please specify a CSV file, structures shapefile, and parcel shapefile to import")
    csv_name, struct_shp_name, parcel_shp_name = args[1:]
    csvreader = csv.DictReader(open(csv_name))
    struct_layer = DataSource(struct_shp_name)[0]
    parcel_layer = DataSource(parcel_shp_name)[0]

    prop_trans = PropertyTransactions(clear=opts.clear)

    if opts.stats:
        prop_trans.stats(csvreader, struct_layer, parcel_layer)
    else:
        prop_trans.update(csvreader, struct_layer, parcel_layer)


if __name__ == '__main__':
    sys.exit(main())
