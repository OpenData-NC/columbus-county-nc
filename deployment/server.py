from __future__ import with_statement

import os
import subprocess

from fabric.api import *
from fabric.contrib import files

from fabulaws.decorators import uses_fabric
from fabulaws.ec2 import EC2Instance
from fabulaws.ubuntu.instances import UbuntuInstance
from fabulaws.ubuntu.packages.postgres import PostgresMixin
from fabulaws.ubuntu.packages.python import PythonMixin

__all__ = [
    'ServerInstance',
    'DbMixin',
    'WebMixin', 
    'OpenRuralInstance',
]


class ServerInstance(UbuntuInstance):
    # from http://uec-images.ubuntu.com/releases/10.04/release/
    ami_map = {
        # 10.04
        't1.micro': 'ami-ad36fbc4', # us-east-1 10.04 64-bit w/EBS root store
        'm1.small': 'ami-929644fb', # us-east-1 10.04 32-bit w/instance root store
        'c1.medium': 'ami-6936fb00', # us-east-1 10.04 32-bit w/instance root store
        'm1.large': 'ami-1136fb78', # us-east-1 10.04 64-bit w/instance root store
        # 11.04:
        # 't1.micro': 'ami-fd589594', # us-east-1 11.04 64-bit w/EBS root store
        # 'm1.small': 'ami-e358958a', # us-east-1 11.04 32-bit w/instance root store
        # 'c1.medium': 'ami-e358958a', # us-east-1 11.04 32-bit w/instance root store
        # 'm1.large': 'ami-fd589594', # us-east-1 11.04 64-bit w/instance root store
        # 11.10
        #'t1.micro': 'ami-bf62a9d6', # us-east-1 11.10 64-bit w/EBS root store
        #'m1.small': 'ami-3962a950', # us-east-1 11.10 32-bit w/instance root store
        #'c1.medium': 'ami-3962a950', # us-east-1 11.10 32-bit w/instance root store
        #'m1.large': 'ami-c162a9a8', # us-east-1 11.10 64-bit w/instance root store
    }
    key_prefix = 'openrural-'
    admin_groups = ['admin', 'sudo']
    deployment_dir = os.path.dirname(__file__)
    project_root = os.path.dirname(deployment_dir)
    run_upgrade = True

    def __init__(self, *args, **kwargs):
        self.instance_type = kwargs.pop('instance_type')
        self.deploy_user = kwargs.pop('deploy_user')
        if 'terminate' not in kwargs:
            kwargs['terminate'] = False
        if self.instance_type not in self.ami_map:
            supported_types = ', '.join(self.ami_map.keys())
            raise ValueError('Unsupported instance_type "%s". Pick one of: %s'
                             '' % (self.instance_type, supported_types))
        self.ami = self.ami_map[self.instance_type]
        super(ServerInstance, self).__init__(*args, **kwargs)
        self.home = '/home/%s' % self.deploy_user
        self.security_groups = ['openrural-web-sg'] # mixins add other groups

    def _get_users(self):
        """
        Returns a list of tuples of (username, key_file_path).
        """
        users_dir = os.path.join(self.deployment_dir, 'users')
        users = [(n, os.path.join(users_dir, n))
                 for n in os.listdir(users_dir)]
        return users

    @uses_fabric
    def setup_sudoers(self):
        """
        Creates the sudoers file on the server, based on the supplied template.
        """
        sudoers_file = os.path.join(self.deployment_dir, 'templates', 'sudoers')
        files.upload_template(sudoers_file, '/etc/sudoers.new', backup=False,
                              use_sudo=True, mode=0440)
        sudo('chown root:root /etc/sudoers.new')
        sudo('mv /etc/sudoers.new /etc/sudoers')

    @uses_fabric
    def create_deployer(self):
        """
        Creates a deployment user with a directory for Apache configurations.
        """
        user = self.deploy_user
        sudo('useradd -d {0} -m -s /bin/bash {1}'.format(self.home, user))
        sudo('mkdir {0}/.ssh'.format(self.home), user=user)

    @uses_fabric
    def update_deployer_keys(self):
        """
        Replaces deployer keys with the current sysadmin users keys.
        """
        user = self.deploy_user
        file_ = '{0}/.ssh/authorized_keys2'.format(self.home)
        if files.exists(file_):
            sudo('rm {0}'.format(file_), user=user)
        sudo('touch {0}'.format(file_), user=user)
        for _, key_file in self._get_users():
            files.append(file_, open(key_file).read().strip(), use_sudo=True)

    def setup(self):
        """
        Creates sysadmin users and secures the required directories.
        """
        super(ServerInstance, self).setup()
        self.create_users(self._get_users())
        self.setup_sudoers()
        # needed for SSH agent forwarding during replication setup:
        # self.reset_authentication()
        # self.secure_directories(self.secure_dirs, self.secure_root)
        self.create_deployer()
        self.update_deployer_keys()
        self.upgrade_packages()


class DbMixin(PostgresMixin):
    """Mixin that creates a database based on the Fabric env."""

    # use the PPA so we get PostgreSQL 9.1
    # postgresql_ppa = 'ppa:pitti/postgresql'
    postgresql_packages = ['postgresql', 'libpq-dev']
    # postgresql_tune = True
    # postgresql_shmmax = 536870912 # 512 MB
    # postgresql_shmmax = 2147483648 # 2048 MB
    postgresql_networks = []

    @uses_fabric
    def pg_cmd(self, action):
        """Run the specified action (e.g., start, stop, restart) on the postgresql server."""

        sudo('service postgresql-8.4 %s' % action)

    @uses_fabric
    def create_postgis_template(self):
        """Create the Postgres postgis template database."""

        share_dir = run('pg_config --sharedir').strip()
        env.postgis_path = '%s/contrib' % share_dir
        sudo('createdb -E UTF8 %(template_db)s' % env, user='postgres')
        sudo('createlang -d %(template_db)s plpgsql' % env, user='postgres')
        # Allows non-superusers the ability to create from this template
        sudo('psql -d postgres -c "UPDATE pg_database SET datistemplate=\'true\' WHERE datname=\'%(template_db)s\';"' % env, user='postgres')
        # Loading the PostGIS SQL routines
        sudo('psql -d %(template_db)s -f %(postgis_path)s/postgis.sql' % env, user='postgres')
        sudo('psql -d %(template_db)s -f %(postgis_path)s/spatial_ref_sys.sql' % env, user='postgres')
        # Enabling users to alter spatial tables.
        sudo('psql -d %(template_db)s -c "GRANT ALL ON geometry_columns TO PUBLIC;"' % env, user='postgres')
        #sudo('psql -d %(template_db)s -c "GRANT ALL ON geography_columns TO PUBLIC;"' % env, user='postgres')
        sudo('psql -d %(template_db)s -c "GRANT ALL ON spatial_ref_sys TO PUBLIC;"' % env, user='postgres')

    @uses_fabric
    def create_db(self, name, owner=None, encoding=u'UTF-8', template=None):
        """Create a Postgres database."""

        flags = []
        if encoding:
            flags.append(u'-E %s' % encoding)
        if owner:
            flags.append(u'-O %s' % owner)
        if template:
            flags.append(u'-T %s' % template)
        flags.append(name)
        sudo('createdb %s' % ' '.join(flags), user='postgres')

    def setup(self):
        """
        Creates necessary directories, installs required packages, and copies
        the required SSH keys to the server.
        """

        super(DbMixin, self).setup()
        self.create_postgis_template()
        self.create_db_user(env.database_user, password=env.database_password)
        self.create_db(env.database_name, owner=env.database_user,
                       template=env.template_db)


class WebMixin(PythonMixin):
    """Mixin that creates a web application server."""

    python_packages = ['python2.6', 'python2.6-dev']
    python_pip_version = '1.0.1'
    python_virtualenv_version = '1.7'

    def install_system_packages(self):
        """Installs the required system packages."""

        # Install required system packages for deployment, plus some extras
        # Install pip, and use it to install virtualenv
        packages_file = os.path.join(self.project_root, 'requirements', 'packages.txt')
        self.install_packages_from_file(packages_file)

    @uses_fabric
    def create_webserver_user(self):
        """Create a user for gunicorn, celery, etc."""

        if env.webserver_user != env.deploy_user: # deploy_user already exists
            sudo('useradd --system %(webserver_user)s' % env)

    def setup(self):
        """
        Creates necessary directories, installs required packages, and copies
        the required SSH keys to the server.
        """

        super(WebMixin, self).setup()
        self.install_system_packages()
        self.create_webserver_user()


class OpenRuralInstance(DbMixin, WebMixin, ServerInstance):
    pass
