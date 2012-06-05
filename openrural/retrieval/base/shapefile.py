import os
import fnmatch
from tempfile import mkdtemp

from django.contrib.gis.gdal import DataSource

from ebdata.retrieval.scrapers import newsitem_list_detail
from ebpub.utils.script_utils import unzip


class ShapefileMissing(Exception):
    pass


class ShapefileScraper(newsitem_list_detail.NewsItemListDetailScraper):
    """OpenBlock scraper class to extract data from shapefile data sources"""

    layer_index = 0

    def find_shapefile(self, directory):
        self.logger.debug('Searching for a shapefile')
        for filename in os.listdir(directory):
            if fnmatch.fnmatch(filename, '*.shp'):
                self.logger.debug('Found shapefile %s' % filename)
                return filename
        self.logger.error('No shapefile found in %s' % directory)
        raise ShapefileMissing()

    def list_pages(self):
        self.logger.debug('Downloading %s' % self.url)
        filename = self.retriever.get_to_tempfile(uri=self.url)
        self.logger.debug('Downloaded to %s' % filename)
        directory = mkdtemp(suffix='-shapefile')
        self.logger.debug('Unzipping to %s' % directory)
        unzip(filename=filename, cwd=directory)
        try:
            shapefile = self.find_shapefile(directory)
        except ShapefileMissing:
            return []
        shapefile = os.path.join(directory, shapefile)
        self.logger.debug('Full path %s' % shapefile)
        layer = DataSource(shapefile)[self.layer_index]
        self.logger.debug('Loaded Data Source: %s' % layer)
        return [layer]

    def parse_list(self, layer):
        for feature in layer:
            self.stats['Downloaded'] += 1
            self.logger_extra['Row'] = "%s-%s" % (self.logger_extra['Run'],
                                                  self.stats['Downloaded'])
            self.geocode_log = None
            yield feature
