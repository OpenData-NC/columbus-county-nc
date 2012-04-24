from optparse import make_option

from django.core.management.base import BaseCommand
from django.contrib.gis.gdal import DataSource

from ebpub.db.models import Location, LocationType
from ebpub.db.bin.import_locations import LocationImporter
from ebpub.metros.allmetros import get_metro

from openrural.management.commands.import_county import CountyImporter

COLUMBUS_COUNTY = '37047' # NC, Columbus county

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("-d", "--dir", action="store", type="string", dest="dir"),
    )
    help = 'Import Columbus County data: county shape and townships, census places, blocks, zips'

    def handle(self, **options):

        county_importer = CountyImporter(COLUMBUS_COUNTY)

        # Override a couple of the default files with county GIS versions.
        county_importer.datafiles['county'] = {
            'source': 'Columbus County GIS site',
            'base_url': 'http://www.columbusco.org',
            'path': 'GISData',
            'file_name': 'County',
            'name_field': 'NAME',
        }
        county_importer.datafiles['cousub'] = {
            'source': 'Columbus County GIS site',
            'base_url': 'http://www.columbusco.org',
            'path': 'GISData',
            'file_name': 'Township',
            'name_field': 'NAME',
        }

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
            'is_significant': True,
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
