import os
import glob
import tempfile
import datetime

from optparse import make_option, OptionParser

from django.core.management.base import BaseCommand
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import GEOSGeometry

from ebpub.utils.text import slugify
from ebpub.db.models import Location, LocationType
from ebpub.db.bin.import_zips import ZipImporter
from ebpub.db.bin.import_locations import LocationImporter
from ebpub.metros.allmetros import get_metro
from ebpub.utils.geodjango import ensure_valid
from ebpub.utils.geodjango import flatten_geomcollection
from ebpub.utils.script_utils import die, makedirs, wget, unzip
from ebpub.streets.blockimport.tiger.import_blocks import TigerImporter
from ebpub.streets.bin import populate_streets
from ebpub.geocoder.parser.parsing import normalize


def census_name_for(shapetype, state, county):
    start = 'tl_2010'
    end = '10'
    if shapetype in ('edges', 'faces', 'featnames'):
        return '%s_%s_%s' % (start, county, shapetype)
    elif shapetype in ('place', 'county'):
        return '%s_%s_%s%s' % (start, state, shapetype, end)
    elif shapetype == 'cousub':
        return '%s_%s_%s%s' % (start, county, shapetype, end)
    elif shapetype == 'zips':
        return '%s_%s_zcta5%s' % (start, state, end)


class CountyImporter(object):
    def __init__(self, county, county_location=None):
        self.county = county
        state = self.state = county[0:2]
        self.county_location = None
        self.metro_name = get_metro()['metro_name'].upper()

        self.datafiles = {}
        self.datafiles['zips'] = {
            'path': 'ZCTA5/2010',
            'name_field': 'ZCTA5CE10',
        }
        for key in ('county', 'cousub', 'place'):
            self.datafiles[key] = {
                'path': '%s/2010' % key.upper(),
                'name_field': 'NAME10',
            }
        for key in ('edges', 'faces', 'featnames'):
            self.datafiles[key] = {
                'path': key.upper(),
            }
        for key in self.datafiles.keys():
            self.datafiles[key]['file_name'] = census_name_for(key, state, county)
            self.datafiles[key]['base_url'] = 'ftp://ftp2.census.gov/geo/tiger/TIGER2010'
            self.datafiles[key]['source'] = '2010 Tiger Census data'

    def fetch_files(self, zip_dir):
        orig_cwd = os.getcwd()
        if zip_dir:
            download = not os.path.exists(zip_dir)
            if download:
                os.makedirs(zip_dir)
        else:
            zip_dir = tempfile.mkdtemp()
            download = True
        self.zip_dir = zip_dir
        os.chdir(zip_dir)
        if download:
            print 'Download data files to %s' % zip_dir
            for k, v in self.datafiles.items():
                fetch_name = '%s/%s/%s.zip' % (v['base_url'], v['path'], v['file_name'])
                wget(fetch_name) or die('Could not download %s' % fetch_name)
            for fname in glob.glob('*zip'):
                unzip(fname) or die('Could not unzip %s' % fname)
            print "Shapefiles unzipped in %s" % zip_dir
        os.chdir(orig_cwd)
        return zip_dir

    def import_county(self):
        county_type_data = {
            'name': 'County',
            'plural_name': 'Counties',
            'slug': 'counties',
            'is_browsable': True,
            'is_significant': False,
            'scope': self.metro_name,
        }
        try:
            county_type = LocationType.objects.get(slug=county_type_data['slug'])
        except LocationType.DoesNotExist:
            county_type = LocationType.objects.create(**county_type_data)

        Location.objects.filter(location_type=county_type).delete()
        county_layer = DataSource('%s/%s.shp' % (self.zip_dir,
            self.datafiles['county']['file_name']))[0]
        now = datetime.datetime.now()
        county_location = None
        for feature in county_layer:
            if feature.get('GEOID10') == self.county:
                name = feature.get(self.datafiles['county']['name_field'])
                geom = feature.geom.transform(4326, True).geos
                geom = ensure_valid(geom, name)
                geom = flatten_geomcollection(geom)
                loc_fields = dict(
                    name = name,
                    slug = slugify(name),
                    location_type = county_type,
                    location = geom,
                    city = self.metro_name,
                    is_public = True,
                )
                kwargs = dict(
                    loc_fields,
                )
                kwargs.update({
                    'creation_date': now,
                    'last_mod_date': now,
                    'display_order': 0,
                    'normalized_name': normalize(loc_fields['name']),
                    'area': loc_fields['location'].transform(3395, True).area,
                })
                county_location = Location.objects.create(**kwargs)
                break
        return county_location

    def import_starter_cities(self):
        fkey = 'place'
        type_data = {
            'name': 'Community',
            'plural_name': 'Communities',
            'slug': 'cities',
            'is_browsable': True,
            'is_significant': True,
            'scope': self.metro_name,
        }
        try:
            self.city_type = LocationType.objects.get(slug=type_data['slug'])
        except LocationType.DoesNotExist:
            self.city_type = LocationType.objects.create(**type_data)

        Location.objects.filter(location_type=self.city_type).delete()
        layer = DataSource('%s/%s.shp' % (self.zip_dir, self.datafiles[fkey]['file_name']))[0]
        loc_importer = LocationImporter(layer,
            self.city_type,
            source = self.datafiles[fkey].get('source', 'Unknown'),
            filter_bounds=True,
            verbose=True)
        loc_importer.bounds = self.county_location.location
        loc_created_count = loc_importer.save(self.datafiles[fkey]['name_field'])
        return loc_created_count

    def augment_cities(self):
        # Add in county subdivisions, deleting from their shapes any area already covered by a "proper" city.
        fkey = 'cousub'
        starter_cities = Location.objects.filter(location_type=self.city_type)
        within_cities = GEOSGeometry('MULTIPOLYGON EMPTY')
        for city in starter_cities:
            within_cities = within_cities.union(city.location)
        city_pks = [l.pk for l in starter_cities]
        layer = DataSource('%s/%s.shp' % (self.zip_dir, self.datafiles[fkey]['file_name']))[0]
        loc_importer = LocationImporter(layer,
            self.city_type,
            source = self.datafiles[fkey].get('source', 'Unknown'),
            filter_bounds=False,
            verbose=True)
        loc_created_count = loc_importer.save(self.datafiles[fkey]['name_field'])
        townships = Location.objects.filter(location_type=self.city_type).exclude(pk__in=city_pks)
        city_names = Location.objects.filter(location_type=self.city_type, pk__in=city_pks).values_list('name', flat=True)
        city_names = [name.lower() for name in city_names]
        for township in townships:
            # If a same-named city already exists, then:
            #   1. Rename the township to "Cityname area."
            #   2. Rename the city to "Cityname town limits."
            if township.name.lower() in city_names:
                city = Location.objects.get(location_type=self.city_type, pk__in=city_pks, name__iexact=township.name)
                city.name = '%s town limits' % city.name.title()
                city.slug = slugify(city.name)  # This seems to be expected by some OpenBlock code.
                city.save()
                township.name = '%s area' % township.name.title()
            else:
                township.name = township.name.title()
            township.slug = slugify(township.name)
            township.location = township.location.difference(within_cities)
            township.save()
        return loc_created_count

    def import_zips(self):
        fkey = 'zips'
        Location.objects.filter(location_type__slug='zipcodes').delete()
        zip_layer = DataSource('%s/%s.shp' % (self.zip_dir, self.datafiles[fkey]['file_name']))[0]
        zip_importer = ZipImporter(zip_layer,
            name_field=self.datafiles[fkey]['name_field'],
            source=self.datafiles[fkey].get('source', 'Unknown'),
            filter_bounds=True,
            verbose=True)
        zip_importer.bounds = self.county_location.location
        loc_created_count = zip_importer.save()
        return loc_created_count

    def import_blocks(self):
        # Now we load them the blocks table.
        print "Importing blocks, this may take several minutes ..."

        importer = TigerImporter(
            '%s/%s.shp' % (self.zip_dir, self.datafiles['edges']['file_name']),
            '%s/%s.dbf' % (self.zip_dir, self.datafiles['featnames']['file_name']),
            '%s/%s.dbf' % (self.zip_dir, self.datafiles['faces']['file_name']),
            '%s/%s.shp' % (self.zip_dir, self.datafiles['place']['file_name']),
            fix_cities=True,
            encoding='utf8',
            filter_bounds=self.county_location.location)
        num_created, num_updated = importer.save()
        print "Created %d blocks, updated %d" % (num_created, num_updated)

    def populate_streets(self):
        print "Populating streets and fixing addresses, these can take several minutes..."

        # Note these scripts should be run ONCE, in this order,
        # after you have imported *all* your blocks.

        populate_streets.main(['streets'])
        populate_streets.main(['block_intersections'])
        populate_streets.main(['intersections'])

    def full_import(self):
        if not self.county_location:
            self.county_location = self.import_county()
        self.import_starter_cities()
        self.augment_cities()
        self.import_zips()
        self.import_blocks()
        self.populate_streets()

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("-d", "--dir", action="store", type="string", dest="dir"),
    )
    help = 'Import county data: county shape, places and county subdivisions, blocks and zips'

    def handle(self, county, **options):
        county_importer = CountyImporter(county)
        zip_dir = county_importer.fetch_files(options['dir'])
        county_importer.full_import()
        print "Done."

        if not options['dir']:
            print "Removing temp directory %s" % zip_dir
            os.system('rm -rf %s' % zip_dir)
