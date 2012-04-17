import os
import glob
import tempfile

from optparse import make_option, OptionParser

from django.core.management.base import BaseCommand
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import GEOSGeometry

from ebpub.utils.text import slugify
from ebpub.db.models import Location, LocationType
from ebpub.db.bin.import_zips import ZipImporter
from ebpub.db.bin.import_locations import LocationImporter
from ebpub.metros.allmetros import get_metro
from ebpub.utils.script_utils import die, makedirs, wget, unzip
from ebpub.streets.blockimport.tiger.import_blocks import TigerImporter
from ebpub.streets.bin import populate_streets

STATE = '37' # NC
COUNTY = '37047' # NC, Columbus county

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("-d", "--dir", action="store", type="string", dest="dir"),
    )
    help = 'Import Columbus County data: county shape and townships, census places, blocks, zips'

    def fetch_files(self, zip_dir):
        orig_cwd = os.getcwd()
        if zip_dir:
            download = not os.path.exists(zip_dir)
            if download:
                os.makedirs(zip_dir)
        else:
            zip_dir = tempfile.mkdtemp()
            download = True
        os.chdir(zip_dir)
        if download:
            print 'Download TIGER & County GIS data to %s' % zip_dir
            census_base_url = 'ftp://ftp2.census.gov/geo/tiger/TIGER2010'
            county_base_url = 'http://www.columbusco.org/GISData'
            census_zips = (
                'PLACE/2010/tl_2010_%s_place10.zip' % STATE,
                'EDGES/tl_2010_%s_edges.zip' % COUNTY,
                'FACES/tl_2010_%s_faces.zip' % COUNTY,
                'FEATNAMES/tl_2010_%s_featnames.zip' % COUNTY,
                'ZCTA5/2010/tl_2010_%s_zcta510.zip' % STATE,
                )
            # Interestingly, versions of these files are available from the census data as well.
            # However, at least the township one has clearly different boundaries for the townships.
            # Going with the county data on the assumption it's coming from a source more likely to
            # know what the "right" boundaries are.
            county_zips = (
                'County.zip',
                'Township.zip',
            )
            for fname in census_zips:
                fetch_name = '%s/%s' % (census_base_url, fname)
                wget(fetch_name) or die(
                    'Could not download %s' % fetch_name)
            for fname in county_zips:
                fetch_name = '%s/%s' % (county_base_url, fname)
                wget(fetch_name) or die(
                    'Could not download %s' % fetch_name)

            for fname in glob.glob('*zip'):
                unzip(fname) or die('Could not unzip %s' % fname)
            print "Shapefiles unzipped in %s" % zip_dir
        os.chdir(orig_cwd)
        return zip_dir

    def handle(self, **options):
        zip_dir = self.fetch_files(options['dir'])

        metro_name = get_metro()['metro_name'].upper()

        county_type_data = {
            'name': 'County',
            'plural_name': 'Counties',
            'slug': 'counties',
            'is_browsable': True,
            'is_significant': True,
            'scope': metro_name,
        }
        try:
            county_type = LocationType.objects.get(slug=county_type_data['slug'])
        except LocationType.DoesNotExist:
            county_type = LocationType.objects.create(**county_type_data)

        Location.objects.filter(location_type=county_type).delete()
        county_layer = DataSource('%s/County.shp' % zip_dir)[0]
        loc_importer = LocationImporter(county_layer, county_type, filter_bounds=False, verbose=True)
        loc_created_count = loc_importer.save('NAME')
        # We are assuming here we are only going to have ONE county!
        columbus_county_location = Location.objects.get(location_type=county_type)

        city_type_data = {
            'name': 'City',
            'plural_name': 'Cities',
            'slug': 'cities',
            'is_browsable': True,
            'is_significant': True,
            'scope': metro_name,
        }
        try:
            city_type = LocationType.objects.get(slug=city_type_data['slug'])
        except LocationType.DoesNotExist:
            city_type = LocationType.objects.create(**city_type_data)

        Location.objects.filter(location_type=city_type).delete()
        city_layer = DataSource('%s/tl_2010_%s_place10.shp' % (zip_dir, STATE))[0]
        loc_importer = LocationImporter(city_layer, city_type, filter_bounds=True, verbose=True)
        loc_importer.bounds = columbus_county_location.location
        loc_created_count = loc_importer.save('NAME10')

        # Add in townships, deleting from their shapes any area already covered by a "proper" city.
        starter_cities = Location.objects.filter(location_type=city_type)
        within_cities = GEOSGeometry('MULTIPOLYGON EMPTY')
        for city in starter_cities:
            within_cities = within_cities.union(city.location)
        city_pks = [l.pk for l in starter_cities]
        township_layer = DataSource('%s/Township.shp' % zip_dir)[0]
        loc_importer = LocationImporter(township_layer, city_type, filter_bounds=False, verbose=True)
        loc_created_count = loc_importer.save('NAME')
        townships = Location.objects.filter(location_type=city_type).exclude(pk__in=city_pks)
        for township in townships:
            township.name = '%s environs' % township.name.title()
            township.slug = slugify(township.name)
            township.location = township.location.difference(within_cities)
            township.save()

        # Zipcodes are used by the block importer
        Location.objects.filter(location_type__slug='zipcodes').delete()
        zip_layer = DataSource('%s/tl_2010_%s_zcta510.shp' % (zip_dir, STATE))[0]
        zip_importer = ZipImporter(zip_layer, name_field='ZCTA5CE10', source='2010 Tiger/Census',
            filter_bounds=True, verbose=True)
        zip_importer.bounds = columbus_county_location.location
        loc_created_count = zip_importer.save()

        # Now we load them the blocks table.
        print "Importing blocks, this may take several minutes ..."

        importer = TigerImporter(
            '%s/tl_2010_%s_edges.shp' % (zip_dir, COUNTY),
            '%s/tl_2010_%s_featnames.dbf' % (zip_dir, COUNTY),
            '%s/tl_2010_%s_faces.dbf' % (zip_dir, COUNTY),
            '%s/tl_2010_%s_place10.shp' % (zip_dir, STATE),
            fix_cities=True,
            encoding='utf8',
            filter_bounds=columbus_county_location.location)
        num_created = importer.save()
        print "Created %d blocks" % num_created

        #########################

        print "Populating streets and fixing addresses, these can take several minutes..."

        # Note these scripts should be run ONCE, in this order,
        # after you have imported *all* your blocks.

        populate_streets.main(['streets'])
        populate_streets.main(['block_intersections'])
        populate_streets.main(['intersections'])
        print "Done."

        if not options['dir']:
            print "Removing temp directory %s" % zip_dir
            os.system('rm -rf %s' % zip_dir)
