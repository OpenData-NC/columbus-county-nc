OpenRural: Columbus County, North Carolina
==========================================

This is the official Columbus County OpenRural repository.

Local Development Setup
-----------------------

Clone Open Rural and create a new virtualenv::

    $ git clone git://github.com/openrural/openrural-nc.git
    $ cd openrural-nc/
    $ mkvirtualenv --distribute -p python2.6 openrural

If you're on Ubuntu 11.04, install `GDAL the hard way <http://openblockproject.org/docs/install/common_install_problems.html#gdal-the-hard-way>`_. The commands are::

    $ gdal-config --version
    1.6.3
    $ pip install --no-install "GDAL>=1.6,<1.7a"  # adjust version as needed
    $ rm -f $VIRTUAL_ENV/build/GDAL/setup.cfg
    $ cd $VIRTUAL_ENV/build/GDAL
    $ python setup.py build_ext --gdal-config=gdal-config \
                                --library-dirs=/usr/lib \
                                --libraries=gdal1.6.0 \
                                --include-dirs=/usr/include/gdal \
                                install

Install the OpenRural packages::

    $ cd openrural-nc/
    $ pip install -r requirements/deploy.txt
    $ pip install --no-index \
                  --find-links=file:$PWD/requirements/sdists/ \
                  -r requirements/ebdata.txt \
                  -r requirements/ebpub.txt \
                  -r requirements/obadmin.txt \
                  -r requirements/openrural.txt
    $ add2virtualenv .

If you're developing OpenBlock, you should install the development version::

    $ mkvirtualenv --distribute -p python2.6 openrural
    $ pip install -r requirements/deploy.txt
    $ fab develop:../openblock,no_index=True
    $ pip install -r requirements/dev.txt
    $ add2virtualenv .

Create a PostgreSQL database for development::

    $ createdb --template=template_postgis openblock_devel

Create a local settings file::

    $ cp openrural/local_settings.py.example openrural/local_settings.py

Edit ``local_settings.py`` and extend from the project settings module you want to work on::

    1c1
    < from openrural.settings import *
    ---
    > from openrural.settings_whiteville import *

Point Django do your local settings and initialize the database::

    $ export DJANGO_SETTINGS_MODULE=openrural.local_settings
    $ django-admin.py syncdb --migrate

If everything went smoothly, you can now runserver::

    $ django-admin.py runserver

Columbus County, NC
-------------------

To import data for Columbus County, NC::

    $ django-admin.py import_nc_zips
    $ django-admin.py import_county_streets 37047
    $ django-admin.py import import_columbus_county

Where 37047 is the U.S. Census county ID for the county you want to import
(37047 = Columbus County, NC).
