OpenRural: Columbus County, North Carolina
==========================================

This is the official Columbus County OpenRural repository.

Local Development Setup
-----------------------

To setup OpenRural, you need to clone OpenBlock along side OpenRural::

    $ git clone git://github.com/openrural/openblock.git
    $ git clone git://github.com/openrural/columbus-county-nc.git

OpenRural runs a modifed branch of OpenBlock, so switch to that branch::

    $ cd openblock/
    $ git checkout openrural

Now we can setup our local OpenRural Python environment::

    $ cd columbus-county-nc/
    $ mkvirtualenv --distribute -p python2.6 columbusco
    $ add2virtualenv .
    $ pip install -r requirements/deploy.txt
    $ fab update_ve:True

Create a PostgreSQL database for development::

    $ createdb --template=template_postgis openblock_devel

Create a local settings file::

    $ cp openrural/local_settings.py.example openrural/local_settings.py

Point Django do your local settings and initialize the database::

    $ export DJANGO_SETTINGS_MODULE=openrural.local_settings
    $ django-admin.py syncdb --migrate

If everything went smoothly, you can now runserver::

    $ django-admin.py runserver

Columbus County, NC
*******************

To import data for Columbus County, NC::

    $ django-admin.py import_columbus_county --dir=shapefiles

The --dir option specified to import_columbus_county directs the command to look
for the necessary shapefiles in the specified directory. If that directory does not
exist, then it will be created, the files will be downloaded into that directory,
and they will be left there for later use. If --dir is not specified then the files
will be downloaded to a temporary directory which will be deleted before the command
finishes.

Server Provisioning and Deployment
----------------------------------

First, add your AWS credentials to your shell environment::

    export AWS_ACCESS_KEY_ID=
    export AWS_SECRET_ACCESS_KEY=

It easiest to store this in a file and source it ``source aws.sh``.

Server Provisioning
*******************

Use fabric to create a new environment::

    $ pip install -r requirements/deploy.txt
    $ fab new_instance:us-east-1d,columbusco,staging

Next we bootstrap the server with::

    $ fab staging:columbusco bootstrap deploy load_geo_files

If the nginx configuration is setup to use htpasswd, setup a new user::

    $ fab staging set_htpasswd:<username>,<password>

Deployment
**********

For regular deployments, simply run::

    $ fab staging:columbusco deploy

You can reset your local database with::

    $ fab staging reset_local_db:columbusco_devel

Manual Setup
------------

Only run these if the above instructions failed.

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

If you're developing OpenBlock, you should install the development version::

    $ pip install -r requirements/deploy.txt
    $ fab develop:../openblock
    $ pip install --no-index \
                  --find-links=file:$PWD/requirements/sdists/ \
                  -r requirements/openrural.txt
    $ add2virtualenv .

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
