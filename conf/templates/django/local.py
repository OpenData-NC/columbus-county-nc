from openrural.settings.{{ environment }} import *

MEDIA_ROOT = "{{ media_root }}"
STATIC_ROOT = "{{ static_root }}"
DJANGO_STATIC_SAVE_PREFIX = "{{ static_root }}"
EMAIL_SUBJECT_PREFIX = '[ColumbusCo {{ environment }}] '

if 'gelf' in LOGGING['handlers']:
    LOGGING['handlers']['gelf']['extra_fields']['environment'] = '{{ environment }}'

BROKER_URL = "amqp://{{ project_user }}:{{ broker_password }}@localhost:5672/{{ vhost }}"
BROKER_CONNECTION_TIMEOUT = 15

EB_DOMAIN = '{{ server_name }}'

PASSWORD_CREATE_SALT = '{{ password_create_salt }}%s%s'
PASSWORD_RESET_SALT = '{{ password_reset_salt }}%s%s'

DEBUG = {% if debug %}True{% else %}False{% endif %}

GOOGLE_PASSWORD = '{{ google_password }}'

if not PROJECT_TEMPLATES:
    path = os.path.join(PROJECT_DIR, 'templates')
    dirs = list(TEMPLATE_DIRS)
    dirs.remove(path)
    TEMPLATE_DIRS = tuple(dirs)
