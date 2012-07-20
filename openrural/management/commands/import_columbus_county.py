import logging
from optparse import make_option
import os

from django.core.management.base import BaseCommand
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.gdal.geometries import LineString

from ebpub.db.models import Location, LocationType, get_city_locations
from ebpub.db.bin.import_locations import LocationImporter
from ebpub.metros.allmetros import get_metro
from ebpub.streets.blockimport.base import BlockImporter
from ebpub.streets.models import Block
from ebpub.geocoder.parser import parsing
from ebpub.utils.geodjango import geos_with_projection

from openrural.management.commands.import_county import CountyImporter

COLUMBUS_COUNTY = '37047' # NC, Columbus county

logger = logging.getLogger('openrural')

class ColumbusCountyBlockImporter(BlockImporter):

    def skip_feature(self, feature):
        if feature.get('LENGTH') and isinstance(feature.geom, LineString):
            return False
        return True

    def gen_blocks(self, feature):
        block_fields = {}
        block_fields['right_zip'] = feature.get('RZIP')
        block_fields['left_zip'] = feature.get('LZIP')
        block_fields['right_from_num'] = feature.get('FROMRIGHT')
        block_fields['right_to_num'] = feature.get('TORIGHT')
        block_fields['left_from_num'] = feature.get('FROMLEFT')
        block_fields['left_to_num'] = feature.get('TOLEFT')
        block_fields['street'] = feature.get('STREET').upper().strip()
        block_fields['predir'] = feature.get('PREDIR').upper().strip()
        block_fields['suffix'] = feature.get('TYPE').upper().strip()
        block_fields['postdir'] = feature.get('SUFDIR').upper().strip()
        block_fields['prefix'] = feature.get('PRETYPE').upper().strip()

        for side in ['left', 'right']:
            if block_fields['%s_from_num' % side] == 0 and not (block_fields['%s_to_num' % side] % 2):
                block_fields['%s_from_num' % side] = 2
        # As of OpenBlock 1.2 these values must be strings, else they get turned into None
        for side in ['left', 'right']:
            block_fields['%s_from_num' % side] = str(block_fields['%s_from_num' % side])
            block_fields['%s_to_num' % side] = str(block_fields['%s_to_num' % side])

        cities = list(get_city_locations().filter(location__intersects=geos_with_projection(feature.geom, 4326)))
        city_name = cities[0].name.upper() if cities else ''
        for side in ('right', 'left'):
            block_fields['%s_city' % side] = city_name
            block_fields['%s_state' % side] = 'NC'

        yield block_fields.copy()


class ColumbusCountyImporter(CountyImporter):
    def __init__(self, *args, **kwargs):
        self.use_tiger = kwargs.pop('use_tiger', False)
        super(ColumbusCountyImporter, self).__init__(COLUMBUS_COUNTY, *args, **kwargs)

        # Override a couple of the default files with county GIS versions.
        county_data = {
            'source': 'Columbus County GIS site',
            'base_url': 'http://www.columbusco.org',
            'path': 'GISData',
        }

        self.datafiles['county'] = county_data.copy()
        self.datafiles['county'].update({
            'file_name': 'County',
            'name_field': 'NAME',
        })
        self.datafiles['cousub'] = county_data.copy()
        self.datafiles['cousub'].update({
            'file_name': 'Township',
            'name_field': 'NAME',
        })

        # And add one that isn't used by base importer but we'll use
        self.datafiles['centerlines'] = county_data.copy()
        self.datafiles['centerlines'].update({
            'file_name': 'Roads',
            'shapefile_name': 'centerlines',
        })

    def import_blocks(self):
        if self.use_tiger:
            return super(ColumbusCountyImporter, self).import_blocks()
        else:
            shapefile_path = '%s/%s.shp' % (self.zip_dir, self.datafiles['centerlines']['shapefile_name'])
            cc_block_importer = ColumbusCountyBlockImporter(shapefile_path, verbose=True)
            new, existing = cc_block_importer.save()
            print 'import_blocks saved %s new, %s existing blocks from Columbus County centerlines file.' % (new, existing)


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("-d", "--dir", action="store", type="string", dest="dir"),
        make_option("-t", "--tiger", action="store_true", dest="tiger", default=False,
            help="Use TIGER data for blocks")
    )
    help = 'Import Columbus County data: county shape and townships, census places, blocks, zips'

    def handle(self, **options):

        county_importer = ColumbusCountyImporter(COLUMBUS_COUNTY, use_tiger=options['tiger'])

        zip_dir = county_importer.fetch_files(options['dir'])

        # Do our own import of the county location, using the Columbus County GIS file
        # instead of the census NC Counties file. Columbus County file has just one
        # feature in it.
        metro_name = get_metro()['metro_name'].upper()
        county_type_data = {
            'name': 'County',
            'plural_name': 'Counties',
            'slug': 'counties',
            'is_browsable': True,
            'is_significant': False,
            'scope': metro_name,
        }
        try:
            county_type = LocationType.objects.get(slug=county_type_data['slug'])
        except LocationType.DoesNotExist:
            county_type = LocationType.objects.create(**county_type_data)

        Location.objects.filter(location_type=county_type).delete()
        county_layer = DataSource('%s/%s.shp' % (zip_dir, county_importer.datafiles['county']['file_name']))[0]
        loc_importer = LocationImporter(county_layer, county_type, filter_bounds=False, verbose=True)
        loc_created_count = loc_importer.save(county_importer.datafiles['county']['name_field'])
        columbus_county_location = Location.objects.get(location_type=county_type)

        # Set the county location in the county_importer and call its full_import to do the rest.
        county_importer.county_location = columbus_county_location
        county_importer.full_import()
        print "Done."

        if not options['dir']:
            print "Removing temp directory %s" % zip_dir
            os.system('rm -rf %s' % zip_dir)
