import os
import random
import string
import logging
import tempfile

from getpass import getpass
from fabric.api import *
from fabric.contrib.files import exists, upload_template, append

from argyle import system
from argyle.supervisor import supervisor_command

from fabulaws.api import *

from deployment.server import *

try:
    import fabsecrets
except ImportError:
    fabsecrets = None

logger = logging.getLogger()
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.WARNING)

fabulaws_logger = logging.getLogger('fabulaws')
fabulaws_logger.setLevel(logging.DEBUG)

PROJECT_ROOT = os.path.dirname(__file__)
env.project = 'openrural'
env.deploy_user = 'openrural'
env.webserver_user = 'openrural-web'
env.database_user = 'openrural'
env.database_host = 'localhost'
env.home = '/home/openrural'
env.repo = u'git@github.com:openrural/columbus-county-nc.git'
env.shell = '/bin/bash -c'
env.python = '/usr/bin/python2.6'
env.placements = ['us-east-1a', 'us-east-1b', 'us-east-1d']
env.environments = ['staging', 'production']
env.deployments = ['columbusco',]
env.deployment_dir = os.path.join(os.path.dirname(__file__), 'deployment')
env.templates_dir = os.path.join(env.deployment_dir, 'templates')
env.server_ports = {
    'staging': 8000,
    'production': 8001,
}
env.branches = {
    'staging': 'master',
    'production': 'master',
}
env.instance_types = {
    'staging': 'm1.small',
    'production': 't1.micro',
}


def _get_servers(deployment, environment):
    env.filters = {'tag:environment': environment,
                   'tag:deployment': deployment}
    inst_kwargs = {
        'instance_type': env.instance_types[environment],
        'deploy_user': env.deploy_user,
    }
    servers = ec2_instances(filters=env.filters, cls=OpenRuralInstance,
                            inst_kwargs=inst_kwargs)
    print ec2_instances()
    return [server.hostname for server in servers]


def _setup_path():
    env.root = os.path.join(env.home, 'www', env.environment)
    env.log_dir = os.path.join(env.root, 'log')
    env.code_root = os.path.join(env.root, 'code_root')
    env.project_root = os.path.join(env.code_root, env.project)
    env.virtualenv_root = os.path.join(env.root, 'env')
    env.media_root = os.path.join(env.root, 'media_root')
    env.static_root = os.path.join(env.root, 'static_root')
    env.services = os.path.join(env.home, 'services')
    env.database_name = '%s_%s' % (env.project, env.environment)
    env.vhost = '%s_%s' % (env.project, env.environment)
    env.branch = env.branches[env.environment]
    env.server_port = env.server_ports[env.environment]
    env.local_settings = '%s.local_settings' % env.project
    env.htpasswd = os.path.join(env.services, 'htpasswd')
    if not env.hosts:
        env.hosts = _get_servers(env.deployment_tag, env.environment)


def _random_password(length=8, chars=string.letters + string.digits):
    return ''.join([random.choice(chars) for i in range(length)])


def _load_passwords(names, length=20, generate=False):
    """Retrieve password from the user's home directory, or generate a new random one if none exists"""

    for name in names:
        filename = os.path.join(env.home, name)
        if generate:
            passwd = _random_password(length=length)
            sudo('touch %s' % filename, user=env.deploy_user)
            sudo('chmod 600 %s' % filename, user=env.deploy_user)
            with hide('running'):
                sudo('echo "%s">%s' % (passwd, filename), user=env.deploy_user)
        if fabsecrets and hasattr(fabsecrets, name):
            passwd = getattr(fabsecrets, name)
        elif env.host_string and exists(filename):
            with hide('stdout'):
                passwd = sudo('cat %s' % filename).strip()
        else:
            passwd = getpass('Please enter %s: ' % name)
        setattr(env, name, passwd)


@task
def new_instance(placement, deployment, environment, count=1, **kwargs):
    if placement not in env.placements:
        abort('Choose a valid placement: %s' % ', '.join(env.placements))
    if deployment not in env.deployments:
        abort('Choose a valid deployment: %s' % ', '.join(env.deployments))
    if environment not in env.environments:
        abort('Choose a valid environment: %s' % ', '.join(env.environments))
    count = int(count)
    tags = {
        'environment': environment,
        'deployment': deployment,
        'Name': '_'.join([deployment, environment]),
    }
    env.hosts = []
    env.deployment_tag = deployment
    env.environment = environment
    env.database_password = None
    servers = []
    _load_passwords(['database_password'])
    _setup_path()
    for x in range(count):
        instance_type = env.instance_types[env.environment]
        cls = OpenRuralInstance
        server = cls(instance_type=instance_type, placement=placement,
                     tags=tags, deploy_user=env.deploy_user, **kwargs)
        server.setup()
        env.hosts.append(server.hostname)


@task
def staging(deployment):
    env.deployment_tag = deployment
    env.environment = 'staging'
    _setup_path()


@task
def production():
    abort('No production environment has been configured.')


@task
def update_sysadmin_users():
    """Create sysadmin users on the server"""

    require('environment', provided_by=env.environments)
    instance_type = env.instance_types[env.environment]
    servers = ec2_instances(filters=env.filters, cls=OpenRuralInstance,
                            inst_kwargs={'deploy_user': env.deploy_user,
                                         'instance_type': instance_type})
    for server in servers:
        server.create_users(server._get_users())
        server.update_deployer_keys()


@task
def clone_repo():
    """ clone a new copy of the hg repository """

    with cd(env.root):
        sshagent_run('git clone %(repo)s %(code_root)s' % env,
                     user=env.deploy_user)
    with cd(env.code_root):
        sudo('git checkout %(branch)s' % env, user=env.deploy_user)


@task
def setup_dirs():
    """ create (if necessary) and make writable uploaded media, log, etc. directories """

    require('environment', provided_by=env.environments)
    sudo('mkdir -p %(log_dir)s' % env, user=env.deploy_user)
    sudo('chmod a+w %(log_dir)s' % env )
    sudo('mkdir -p %(services)s/nginx' % env, user=env.deploy_user)
    sudo('mkdir -p %(services)s/supervisor' % env, user=env.deploy_user)
    sudo('mkdir -p %(services)s/gunicorn' % env, user=env.deploy_user)
    sudo('mkdir -p %(media_root)s' % env)
    sudo('chown %(webserver_user)s %(media_root)s' % env)


@task
def link_config_files():
    """Include the nginx and supervisor config files via the Ubuntu standard inclusion directories"""

    with settings(warn_only=True):
        sudo('rm /etc/nginx/sites-enabled/default')
        sudo('rm /etc/nginx/sites-enabled/%(project)s-*.conf' % env)
        sudo('rm /etc/supervisor/conf.d/%(project)s-*.conf' % env)
    sudo('ln -s /%(home)s/services/nginx/%(environment)s.conf /etc/nginx/sites-enabled/%(project)s-%(environment)s.conf' % env)
    sudo('ln -s /%(home)s/services/supervisor/%(environment)s.conf /etc/supervisor/conf.d/%(project)s-%(environment)s.conf' % env)


def _upload_template(filename, destination, **kwargs):
    """Upload template and chown to given user"""
    user = kwargs.pop('user')
    kwargs['use_sudo'] = True
    upload_template(filename, destination, **kwargs)
    sudo('chown %(user)s:%(user)s %(dest)s' % {'user': user, 'dest': destination})


@task
def upload_supervisor_conf():
    """Upload Supervisor configuration from the template."""

    require('environment', provided_by=env.environments)
    template = os.path.join(env.templates_dir, 'supervisor.conf')
    destination = os.path.join(env.services, 'supervisor', '%(environment)s.conf' % env)
    _upload_template(template, destination, context=env, user=env.deploy_user)
    supervisor_command('update')


@task
def upload_nginx_conf():
    """Upload Nginx configuration from the template."""

    require('environment', provided_by=env.environments)
    template = os.path.join(env.templates_dir, 'nginx.conf')
    destination = os.path.join(env.services, 'nginx', '%(environment)s.conf' % env)
    _upload_template(template, destination, context=env, user=env.deploy_user)
    restart_nginx()


@task
def upload_gunicorn_conf():
    """Upload Gunicorn configuration from the template."""

    require('environment', provided_by=env.environments)
    template = os.path.join(env.templates_dir, 'gunicorn.conf')
    destination = os.path.join(env.services, 'gunicorn', '%(environment)s.py' % env)
    _upload_template(template, destination, context=env, user=env.deploy_user)


@task
def update_services():
    """ upload changes to services configurations as nginx """

    upload_supervisor_conf()
    upload_nginx_conf()
    upload_gunicorn_conf()


@task
def set_htpasswd(user, passwd):
    """Set htpasswd"""

    require('environment', provided_by=env.environments)
    cmd = 'htpasswd -cdb {0} {1} {2}'.format(env.htpasswd, user, passwd)
    sudo(cmd, user=env.deploy_user)


@task
def create_virtualenv():
    """ setup virtualenv on remote host """

    require('virtualenv_root', provided_by=env.environments)
    cmd = ['virtualenv', '--clear', '--distribute',
           '--python=%(python)s' % env, env.virtualenv_root]
    sudo(' '.join(cmd), user=env.deploy_user)


@task
def update_requirements():
    """ update external dependencies on remote host """

    require('code_root', provided_by=env.environments)
    requirements = os.path.join(env.code_root, 'requirements')
    sdists = os.path.join(requirements, 'sdists')
    base_cmd = ['pip install']
    base_cmd += ['-q -E %(virtualenv_root)s' % env]
    base_cmd += ['--no-index --find-links=file://%s' % sdists]
    # install GDAL by hand, before anything else that might depend on it
    cmd = base_cmd + ['--no-install "GDAL==1.6.1"']
    sudo(' '.join(cmd), user=env.deploy_user)
    # this directory won't exist if GDAL was already installed
    if exists('%(virtualenv_root)s/build/GDAL' % env):
        sudo('rm -f %(virtualenv_root)s/build/GDAL/setup.cfg' % env, user=env.deploy_user)
        with cd('%(virtualenv_root)s/build/GDAL' % env):
            sudo('%(virtualenv_root)s/bin/python setup.py build_ext '
                 '--gdal-config=gdal-config '
                 '--library-dirs=/usr/lib '
                 '--libraries=gdal1.6.0 '
                 '--include-dirs=/usr/include/gdal '
                 'install' % env, user=env.deploy_user)
    # force reinstallation of OpenBlock every time
    with settings(warn_only=True):
        sudo('pip uninstall -y -E %(virtualenv_root)s ebpub ebdata obadmin' % env)
    for file_name in ['ebpub.txt', 'ebdata.txt', 'obadmin.txt', 'openrural.txt']:
        apps = os.path.join(requirements, file_name)
        cmd = base_cmd + ['--requirement %s' % apps]
        sudo(' '.join(cmd), user=env.deploy_user)


@task
def update_local_settings():
    """ create local_settings.py on the remote host """

    require('environment', provided_by=env.environments)
    _load_passwords(['database_password'])
    destination = os.path.join(env.project_root, 'local_settings.py')
    _upload_template('local_settings.py', destination, context=env,
                     user=env.deploy_user, use_jinja=True,
                     template_dir=env.templates_dir)


@task
def trust_github():
    user = env.deploy_user
    file_ = '{0}/.ssh/config'.format(env.home)
    if exists(file_):
        sudo('rm {0}'.format(file_), user=user)
    sudo('touch {0}'.format(file_), user=user)
    append(file_, "Host github.com\n\tStrictHostKeyChecking no\n", use_sudo=True)


@task
def bootstrap():
    """ initialize remote host environment (virtualenv, deploy, update) """

    require('environment', provided_by=env.environments)

    sudo('mkdir -p %(root)s' % env, user=env.deploy_user)
    trust_github()
    clone_repo()
    setup_dirs()
    link_config_files()
    update_services()
    create_virtualenv()
    update_requirements()


@task
def update_source():
    """Checkout the latest code from repo."""

    require('environment', provided_by=env.environments)
    with cd(env.code_root):
        sshagent_run('git pull', user=env.deploy_user)
        sudo('git checkout %(branch)s' % env, user=env.deploy_user)


@task
def manage(cmd):
    """Run the given management command on the remote server."""

    require('environment', provided_by=env.environments)
    env.command = cmd
    base = ['PYTHONPATH=%(code_root)s ' % env,
            'DJANGO_SETTINGS_MODULE=openrural.local_settings ' % env,
            '%(virtualenv_root)s/bin/django-admin.py %(command)s' % env]
    sudo(' '.join(base), user=env.deploy_user)


@task
def syncdb():
    """Run syncdb and South migrations."""

    require('environment', provided_by=env.environments)
    manage('syncdb --noinput')
    manage('migrate --noinput')


@task
def collectstatic():
    """Collect static files."""

    require('environment', provided_by=env.environments)
    manage('collectstatic --noinput')


@task
def createsuperuser():
    """Collect static files."""

    require('environment', provided_by=env.environments)
    manage('createsuperuser')


@task
def restart_nginx():
    """Restart Nginx."""

    require('environment', provided_by=env.environments)
    system.restart_service('nginx')


@task
def supervisor(command, process=None):
    """Restart Supervisor controlled process(es).  If no process is specified, all the given command is run on all processes."""

    require('environment', provided_by=env.environments)
    env.supervisor_command = command
    if process:
        env.supervisor_process = process
        supervisor_command('%(supervisor_command)s %(environment)s:%(environment)s-%(supervisor_process)s' % env)
    else:
        supervisor_command('%(supervisor_command)s %(environment)s:*' % env)


@task
def restart_all():
    """Restart Nginx and Supervisor controlled processes."""

    restart_nginx()
    supervisor('restart')


@task
def deploy():
    """Deploy to a given environment."""

    require('environment', provided_by=env.environments)
    update_source()
    update_requirements()
    update_local_settings()
    syncdb()
    collectstatic()
    supervisor('restart')


@task
def update_passwords():
    """Manually copy the current master database to the slaves."""

    require('environment', provided_by=env.environments)
    passnames = ['database_password']
    _load_passwords(passnames)
    with cd(env.home):
        for passname in passnames:
            passwd = getattr(env, passname)
            sudo('echo "{0}" > {1}'.format(passwd, passname), user=env.deploy_user)
            sudo('chmod 600 {0}'.format(passname), user=env.deploy_user)


@task
def reset_local_db(db_name):
    """ Replace the local database with the remote database """

    require('environment', provided_by=env.environments)
    answer = prompt('Are you sure you want to reset the local database {0} '
                    'with a copy of the {1} database?'.format(db_name,
                                                              env.environment),
                    default='n')
    if answer != 'y':
        abort('Aborted.')
    with settings(warn_only=True):
        local('dropdb {0}'.format(db_name))
    local('createdb {0}'.format(db_name))
    cmd = 'ssh -C {user}@{host} pg_dump -Ox {db_name} | '.format(
        user=env.deploy_user,
        host=env.host_string,
        db_name=env.database_name,
    )
    cmd += 'psql {0}'.format(db_name)
    local(cmd)
