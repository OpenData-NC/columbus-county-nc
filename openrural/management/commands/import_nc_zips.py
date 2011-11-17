#   Copyright 2011 OpenPlans and contributors
#
#   This file is part of OpenBlock
#
#   OpenBlock is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   OpenBlock is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with OpenBlock.  If not, see <http://www.gnu.org/licenses/>.
#

from django.core.management.base import BaseCommand
from ebpub.utils.script_utils import die, makedirs, wget, unzip
import os
import tempfile

class Command(BaseCommand):
    help = 'Import NC zip codes'

    def handle(self, *args, **options):
        
        TMP = tempfile.mkdtemp()
        print 'Download TIGER data to %s' % TMP
        os.chdir(TMP)
        
        ZIP_SERVER = "http://www2.census.gov/geo/tiger/TIGER2009/37_NORTH_CAROLINA/"
        ZIP_FILE = "tl_2009_37_zcta5.zip"
        ZIP_URL = "%s/%s" % (ZIP_SERVER, ZIP_FILE)
        ZIP_FOLDER = os.path.join(TMP, 'zip_data')
        makedirs(ZIP_FOLDER) or die("couldn't create %s" % ZIP_FOLDER)

        print "Downloading zip code data..."
        wget(ZIP_URL, cwd=ZIP_FOLDER) or die("Could not download %s" % ZIP_URL)
        zip_path = os.path.join(ZIP_FOLDER, ZIP_FILE)
        unzip(zip_path, cwd=ZIP_FOLDER) or die("failed to unzip %s" % zip_path)

        print "Importing zip codes..."
        from ebpub.db.bin import import_zips
        import_zips.main([ZIP_FOLDER, '-v', '-b'])
        
        os.system('rm -rf %s' % TMP)

