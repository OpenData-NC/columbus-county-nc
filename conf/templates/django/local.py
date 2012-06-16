from openrural.settings.{{ environment }} import *

MEDIA_ROOT = "{{ media_root }}"
STATIC_ROOT = "{{ static_root }}"
DJANGO_STATIC_SAVE_PREFIX = "{{ static_root }}"

if 'gelf' in LOGGING['handlers']:
    LOGGING['handlers']['gelf']['extra_fields']['environment'] = '{{ environment }}'
