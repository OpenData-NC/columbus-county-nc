import ConfigParser
import os
import random
import string

from argyle import rabbitmq, postgres, nginx, system
from argyle.base import upload_template
from argyle.postgres import create_db_user, create_db
from argyle.supervisor import supervisor_command, upload_supervisor_app_conf
from argyle.system import service_command, start_service, stop_service, restart_service
from argyle import rabbitmq

from fabric.api import cd, env, get, hide, local, put, require, run, settings, sudo, task
from fabric.contrib import files, console
from fabric.colors import yellow

# Directory structure
PROJECT_ROOT = os.path.dirname(__file__)
CONF_ROOT = os.path.join(PROJECT_ROOT, 'conf')
SERVER_ROLES = ['app', 'lb', 'db', 'queue']
env.project = 'openrural'
env.project_user = 'openrural'
env.repo = u'git@github.com:openrural/columbus-county-nc.git'
env.openblock_repo = u'git://github.com/openrural/openblock.git'
env.shell = '/bin/bash -c'
env.disable_known_hosts = True
env.ssh_port = 2222
env.forward_agent = True
env.password_names = ['broker_password']

# Additional settings for argyle
env.ARGYLE_TEMPLATE_DIRS = (
    os.path.join(CONF_ROOT, 'templates')
)


def _random_password(length=8, chars=string.letters + string.digits):
    return ''.join([random.choice(chars) for i in range(length)])


def _load_passwords(names, length=20, generate=False):
    """
    Retrieve password from the user's home directory, or generate a new
    random one if none exists
    """
    for name in names:
        filename = ''.join([env.home, name])
        if env.host_string and files.exists(filename):
            with hide('stdout'):
                passwd = sudo('cat %s' % filename).strip()
        else:
            if generate:
                passwd = _random_password(length=length)
                sudo('touch %s' % filename, user=env.project_user)
                sudo('chmod 600 %s' % filename, user=env.project_user)
                with hide('running'):
                    sudo('echo "%s">%s' % (passwd, filename),
                         user=env.project_user)
            else:
                passwd = getpass('Please enter %s: ' % name)
        setattr(env, name, passwd)


@task
def vagrant():
    env.environment = 'vagrant'
    env.hosts = ['33.33.33.10', ]
    env.branch = 'vagrant'
    env.server_name = 'dev.example.com'
    setup_path()


@task
def staging():
    env.environment = 'staging'
    env.hosts = [] # FIXME: Add staging server hosts
    env.branch = 'master'
    env.server_name = '' # FIXME: Add staging server name
    setup_path()


@task
def production():
    env.environment = 'production'
    env.hosts = [] # FIXME: Add production hosts
    env.branch = 'master'
    env.server_name = '' # FIXME: Add production server name
    setup_path()


def setup_path():
    env.home = '/home/%(project_user)s/' % env
    env.root = os.path.join(env.home, 'www', env.environment)
    env.code_root = os.path.join(env.root, env.project)
    env.project_root = os.path.join(env.code_root, env.project)
    env.virtualenv_root = os.path.join(env.root, 'env')
    env.log_dir = os.path.join(env.root, 'log')
    env.db = env.project
    env.vhost = '%s_%s' % (env.project, env.environment)
    env.settings = '%(project)s.settings.local' % env
    env.openblock_root = os.path.join(env.root, 'openblock')
    env.media_root = os.path.join(env.root, 'media_root')
    env.static_root = os.path.join(env.root, 'static_root')


@task
def create_users():
    """Create project user and developer users."""
    ssh_dir = u"/home/%s/.ssh" % env.project_user
    system.create_user(env.project_user, groups=['www-data', 'login', ])
    sudo('mkdir -p %s' % ssh_dir)
    user_dir = os.path.join(CONF_ROOT, "users")
    for username in os.listdir(user_dir):
        key_file = os.path.normpath(os.path.join(user_dir, username))
        system.create_user(username, groups=['dev', 'login', ], key_file=key_file)
        with open(key_file, 'rt') as f:
            ssh_key = f.read()
        # Add ssh key for project user
        files.append('%s/authorized_keys' % ssh_dir, ssh_key, use_sudo=True)
    files.append(u'/etc/sudoers', r'%dev ALL=(ALL) NOPASSWD:ALL', use_sudo=True)
    sudo('chown -R %s:%s %s' % (env.project_user, env.project_user, ssh_dir))


@task
def configure_ssh():
    """
    Change sshd_config defaults:
    Change default port
    Disable root login
    Disable password login
    Restrict to only login group
    """
    ssh_config = u'/etc/ssh/sshd_config'
    files.sed(ssh_config, u"Port 22$", u"Port %s" % env.ssh_port, use_sudo=True)
    files.sed(ssh_config, u"PermitRootLogin yes", u"PermitRootLogin no", use_sudo=True)
    files.append(ssh_config, u"AllowGroups login", use_sudo=True)
    files.append(ssh_config, u"PasswordAuthentication no", use_sudo=True)
    service_command(u'ssh', u'reload')


@task
def install_packages(*roles):
    """Install packages for the given roles."""
    config_file = os.path.join(CONF_ROOT, u'packages.conf')
    config = ConfigParser.SafeConfigParser()
    config.read(config_file)
    for role in roles:
        if config.has_section(role):
            # Get ppas
            if config.has_option(role, 'ppas'):
                for ppa in config.get(role, 'ppas').split(' '):
                    system.add_ppa(ppa, update=False)
            # Get sources
            if config.has_option(role, 'sources'):
                for section in config.get(role, 'sources').split(' '):
                    source = config.get(section, 'source')
                    key = config.get(section, 'key')
                    system.add_apt_source(source=source, key=key, update=False)
            sudo(u"apt-get update")
            sudo(u"apt-get install -y %s" % config.get(role, 'packages'))
            sudo(u"apt-get upgrade -y")


@task
def setup_server(*roles):
    """Install packages and add configurations for server given roles."""
    require('environment')
    # Set server locale
    sudo('/usr/sbin/update-locale LANG=en_US.UTF-8')
    roles = list(roles)
    if roles == ['all', ]:
        roles = SERVER_ROLES
    if 'base' not in roles:
        roles.insert(0, 'base')
    install_packages(*roles)
    _load_passwords(env.password_names, generate=True)
    if 'db' in roles:
        if console.confirm(u"Do you want to reset the Postgres cluster?.", default=False):
            # Ensure the cluster is using UTF-8
            pg_version = postgres.detect_version()
            sudo('pg_dropcluster --stop %s main' % pg_version, user='postgres')
            sudo('pg_createcluster --start -e UTF-8 %s main' % pg_version,
                 user='postgres')
            create_postgis_template()
            postgres.create_db_user(username=env.project_user)
            create_db(name=env.db, owner=env.project_user,
                      template='template_postgis')
    if 'app' in roles:
        # Create project directories and install Python requirements
        project_run('mkdir -p %(root)s' % env)
        project_run('mkdir -p %(log_dir)s' % env)
        project_run('mkdir -p %(media_root)s' % env)
        project_run('mkdir -p %(static_root)s' % env)
        sudo('chmod a+w %(static_root)s' % env )
        # FIXME: update to SSH as normal user and use sudo
        # we ssh as the project_user here to maintain ssh agent
        # forwarding, because it doesn't work with sudo. read:
        # http://serverfault.com/questions/107187/sudo-su-username-while-keeping-ssh-key-forwarding
        with settings(user=env.project_user):
            # TODO: Add known hosts prior to clone.
            # i.e. ssh -o StrictHostKeyChecking=no git@github.com
            with settings(warn_only=True):
                run('git clone %(repo)s %(code_root)s' % env)
            with cd(env.code_root):
                run('git checkout %(branch)s' % env)
        # Install and create virtualenv
        with settings(hide('everything'), warn_only=True):
            test_for_pip = run('which pip')
        if not test_for_pip:
            sudo("easy_install -U pip")
        with settings(hide('everything'), warn_only=True):
            test_for_virtualenv = run('which virtualenv')
        if not test_for_virtualenv:
            sudo("pip install -U virtualenv")
        project_run('virtualenv -p python2.6 --clear --distribute %s' % env.virtualenv_root)
        path_file = os.path.join(env.virtualenv_root, 'lib', 'python2.6', 'site-packages', 'project.pth')
        files.append(path_file, env.code_root, use_sudo=True)
        sudo('chown %s:%s %s' % (env.project_user, env.project_user, path_file))
        update_requirements()
        update_openblock()
        upload_supervisor_app_conf(app_name=u'gunicorn')
        upload_supervisor_app_conf(app_name=u'group')
        # Restart services to pickup changes
        supervisor_command('reload')
        supervisor_command('restart %(environment)s:*' % env)
    if 'lb' in roles:
        nginx.remove_default_site()
        nginx.upload_nginx_site_conf(site_name=u'%(project)s-%(environment)s.conf' % env)
    if 'queue' in roles:
        with settings(warn_only=True):
            rabbitmq.rabbitmq_command('delete_user %s' % env.project_user)
        rabbitmq.create_user(env.project_user, env.broker_password)
        with settings(warn_only=True):
            rabbitmq.rabbitmq_command('delete_vhost %s' % env.vhost)
        rabbitmq.create_vhost(env.vhost)
        rabbitmq.set_vhost_permissions(env.vhost, env.project_user)


@task
def upload_local_settings():
    """Upload local.py template to server."""
    require('environment')
    dest = os.path.join(env.project_root, 'settings', 'local.py')
    _load_passwords(env.password_names)
    upload_template('django/local.py', dest, use_sudo=True)
    with settings(warn_only=True):
        sudo('chown %s:%s %s' % (env.project_user, env.project_user, dest))


@task
def create_postgis_template():
    """Create PostGIS template using Django's provided script."""
    require('environment')
    script = '/tmp/create_template_postgis-debian.sh'
    if files.exists(script):
        sudo('rm %s' % script)
    sudo('wget -q -P /tmp https://docs.djangoproject.com/en/dev/_downloads/create_template_postgis-debian.sh')
    sudo('chmod +x %s' % script)
    sudo(script, user='postgres')
    sudo('rm %s' % script)


@task
def create_db(name, owner=None, encoding=u'UTF-8', template=''):
    """Create a Postgres database."""

    flags = u''
    if encoding:
        flags = u'-E %s' % encoding
    if owner:
        flags = u'%s -O %s' % (flags, owner)
    if template:
        flags = u'-T %s' % template
    sudo('createdb %s %s' % (flags, name), user='postgres')


def project_run(cmd):
    """ Uses sudo to allow developer to run commands as project user."""
    home = 'HOME=%s' % env.home
    return sudo('%s %s' % (home, cmd), user=env.project_user)


def venv(cmd):
    """Run binaries from within the virtualenv root."""
    if isinstance(cmd, list):
        cmd = ' '.join(cmd)
    return project_run('%s/bin/%s' % (env.virtualenv_root, cmd))


@task
def update_requirements(sdists=False):
    """Update required Python libraries."""
    require('environment')
    requirements = os.path.join(env.code_root, 'requirements')
    base_cmd = ['pip install -q']
    if sdists:
        sdists = os.path.join(requirements, 'sdists')
        base_cmd += ['--no-index --find-links=file://%s' % sdists]
    else:
        base_cmd += ['--use-mirrors']
    # install GDAL by hand, before anything else that might depend on it
    venv(base_cmd + ['--no-install "GDAL==1.6.1"'])
    # this directory won't exist if GDAL was already installed
    if files.exists('%(virtualenv_root)s/build/GDAL' % env):
        project_run('rm -f %(virtualenv_root)s/build/GDAL/setup.cfg' % env)
        with cd('%(virtualenv_root)s/build/GDAL' % env):
            venv('python setup.py build_ext '
                 '--gdal-config=gdal-config '
                 '--library-dirs=/usr/lib '
                 '--libraries=gdal1.6.0 '
                 '--include-dirs=/usr/include/gdal '
                 'install')
    names = ('ebpub.txt', 'ebdata.txt', 'obadmin.txt', 'openrural.txt')
    for name in names:
        apps = os.path.join(requirements, name)
        venv(base_cmd + ['--requirement %s' % apps])


@task
def update_openblock(branch=None):
    require('environment')
    new_install = False
    if not files.exists(env.openblock_root):
        new_install = True
        project_run('git clone %(openblock_repo)s %(openblock_root)s' % env)
    with cd(env.openblock_root):
        project_run('git pull')
        if branch:
            project_run('git checkout %s' % branch)
    if new_install:
        for name in ('ebpub', 'ebdata', 'obadmin'):
            with settings(warn_only=True):
                venv('pip uninstall -y %s' % name)
            print(yellow('Installing {0}'.format(name)))
            package = os.path.join(env.openblock_root, name)
            with cd(package):
                venv('python setup.py develop --no-deps')


@task
def manage_run(command):
    """Run a Django management command on the remote server."""
    require('environment')
    if '--settings' not in command:
        command = u"%s --settings=%s" % (command, env.settings)
    venv(u'django-admin.py %s' % command)


@task
def manage_shell():
    """Drop into the remote Django shell."""
    manage_run("shell")


@task
def syncdb():
    """Run syncdb and South migrations."""
    manage_run('syncdb --noinput')
    manage_run('migrate --noinput')


@task
def collectstatic():
    """Collect static files."""
    manage_run('collectstatic --noinput')


def match_changes(branch, match):
    changes = run("git diff {0} origin/{0} --stat | grep {1} | cat".format(branch, match))
    return any(changes)


@task
def deploy(branch=None):
    """Deploy to a given environment."""
    require('environment')
    if branch is not None:
        env.branch = branch
    requirements = False
    migrations = False
    # Fetch latest changes
    with cd(env.code_root):
        with settings(user=env.project_user):
            run('git fetch origin')
        # Look for new requirements or migrations
        requirements = match_changes(env.branch, "'requirements\/'")
        migrations = match_changes(env.branch, "'\/migrations\/'")
        if requirements or migrations:
            supervisor_command('stop %(environment)s:*' % env)
        with settings(user=env.project_user):
            run("git reset --hard origin/%(branch)s" % env)
    upload_local_settings()
    update_openblock()
    if requirements:
        update_requirements()
        # New requirements might need new tables/migrations
        syncdb()
    elif migrations:
        syncdb()
    # collectstatic()
    supervisor_command('restart %(environment)s:*' % env)


@task
def get_db_dump(clean=True):
    """Get db dump of remote enviroment."""
    require('environment')
    dump_file = '%(environment)s.sql' % env
    temp_file = os.path.join(env.home, dump_file)
    flags = '-Ox'
    if clean:
        flags += 'c'
    sudo('pg_dump %s %s > %s' % (flags, env.db, temp_file), user=env.project_user)
    get(temp_file, dump_file)


@task
def load_db_dump(dump_file):
    """Load db dump on a remote environment."""
    require('environment')
    temp_file = os.path.join(env.home, '%(environment)s.sql' % env)
    put(dump_file, temp_file, use_sudo=True)
    sudo('psql -d %s -f %s' % (env.db, temp_file), user=env.project_user)


### Local Fabric Functionality ###


def _pip(package='', filename=None, sdists=True):
    """Install packages locally using pip"""
    requirements = os.path.join(PROJECT_ROOT, 'requirements')
    cmd = ['pip install']
    if sdists:
        sdists = os.path.join(requirements, 'sdists')
        sdists = '--no-index --find-links=file://%s' % sdists
        cmd.append(sdists)
    if filename:
        path = os.path.join(requirements, filename)
        cmd.append('-r %s' % path)
    if package:
        cmd.append(package)
    local(' '.join(cmd))


def _develop(repo, index=False):
    """Install OpenBlock in development mode"""
    repo = os.path.abspath(repo)
    for name in ('ebpub', 'ebdata', 'obadmin'):
        print(yellow('Installing {0}'.format(name)))
        package = os.path.join(repo, name)
        os.chdir(package)
        local('python setup.py develop --no-deps')


def _build_local_gdal():
    """Compile GDAL"""
    ve_root = os.environ['VIRTUAL_ENV']
    with settings(warn_only=True):
        local('pip uninstall -y GDAL')
    _pip('--no-install "GDAL>=1.6,<1.7a"')
    gdal = os.path.join(ve_root, 'build', 'GDAL')
    local('rm -f %s' % os.path.join(gdal, 'setup.cfg'))
    os.chdir(gdal)
    cmd = ['python setup.py build_ext',
           '--gdal-config=gdal-config',
           '--library-dirs=/usr/lib',
           '--libraries=gdal1.6.0',
           '--include-dirs=/usr/include/gdal',
           'install']
    local(' '.join(cmd))


@task
def update_ve(bootstrap=False, openblock='../openblock'):
    """Update OpenRural requirements locally"""
    _pip(filename='dev.txt', sdists=False)
    if bootstrap:
        _build_local_gdal()
        os.chdir(PROJECT_ROOT)
        _develop(openblock)
        os.chdir(PROJECT_ROOT)
    _pip(filename='ebpub.txt')
    _pip(filename='ebdata.txt')
    _pip(filename='obadmin.txt')
    _pip(filename='openrural.txt')
