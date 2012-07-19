OpenRural: Columbus County, North Carolina
==========================================

This is the official Columbus County OpenRural repository.

Ubuntu 11.04 - Local Development Setup
--------------------------------------

To setup OpenRural, you need to clone OpenBlock along side OpenRural::

    $ git clone git://github.com/openrural/openblock.git
    $ git clone git://github.com/openrural/columbus-county-nc.git

OpenRural runs a modifed branch of OpenBlock, so switch to that branch::

    $ cd openblock/
    $ git checkout openrural

If you're running a fresh 11.04 install, update your Python utilities::

    $ sudo apt-get install python-setuptools python2.6 python2.6-dev
    $ sudo easy_install -U pip
    $ sudo pip install -U distribute virtualenv virtualenvwrapper

Now we can setup our local OpenRural Python environment::

    $ cd columbus-county-nc/
    $ mkvirtualenv --distribute --python=python2.6 columbusco
    $ add2virtualenv .
    $ $VIRTUAL_ENV/bin/pip install -q -r $PWD/requirements/dev.txt
    $ fab update_ve:True

Then create a local settings file and set your ``DJANGO_SETTINGS_MODULE`` to use it::

    cp openrural/settings/local.example.py openrural/settings/local.py
    echo "export DJANGO_SETTINGS_MODULE=openrural.settings.local" >> $VIRTUAL_ENV/bin/postactivate
    echo "unset DJANGO_SETTINGS_MODULE" >> $VIRTUAL_ENV/bin/postdeactivate

Download the Debian/Ubuntu script from `Creating a spatial database template for PostGIS <https://docs.djangoproject.com/en/1.4/ref/contrib/gis/install/#creating-a-spatial-database-template-for-postgis>`_ and run it as the `posgres` user.

Create a PostgreSQL database for development and initialize the database::

    $ createdb --template=template_postgis openrural
    $ django-admin.py syncdb --migrate

To hide certain schemas from the site by setting public to False, use the
hide_schemas management command with the slugs of the schemas you wish to hide
as the arguments::

    $ django-admin.py hide_schemas local-news open311-service-requests

To hide just the Local News and Open311 Service Requests schemas, use the
--default option.

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

By default the import_columbus_county command uses the county GIS department's road
centerliens file to generate blocks. If you would prefer to use census (Tiger) data,
pass --tiger to the command.

Vagrant Testing
------------------------

You can test the provisioning/deployment using `Vagrant <http://vagrantup.com/>`_.
Using the Vagrantfile you can start up the VM. This requires the ``lucid32`` box::

    vagrant up

With the VM up and running you can create the necessary users as before.
The location of the key file may vary on your system.

On Debian/Ubuntu::

    fab -H 33.33.33.10 -u vagrant -i /opt/vagrant/embedded/gems/gems/vagrant-1.0.3/keys/vagrant create_users

On OSX::

    fab -H 33.33.33.10 -u vagrant -i /Applications/Vagrant/embedded/gems/gems/vagrant-1.0.3/keys/vagrant create_users

Then setup the server::

    fab vagrant setup_server:all
    fab vagrant setup_local_dev
    fab vagrant deploy

It is not necessary to reconfigure the SSH settings on the vagrant box. This forwards
port 80 in the VM to port 8080 on the host box. You can view the site
by visiting localhost:8080 in your browser. You may also want to add::

    33.33.33.10 dev.example.com

to your hosts (/etc/hosts) file. You can stop the VM with ``vagrant halt`` and
destroy the box completely to retest the provisioning with ``vagrant destroy``.
For more information please review the Vagrant documentation.

Server Provisioning and Deployment
----------------------------------

Server Provisioning
*******************

Use fabric to create a new environment::

    $ $VIRTUAL_ENV/bin/pip install -q -r $PWD/requirements/dev.txt
    $ fab -H <host> -u ubuntu -i <aws-private-key> create_users
    $ fab <fab-environment> setup_server:all deploy

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
