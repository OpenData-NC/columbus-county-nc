from openrural.settings.{{ environment }} import *

MEDIA_ROOT = "{{ media_root }}"

STATIC_ROOT = "{{ static_root }}"

ADMIN_MEDIA_PREFIX = "/media/admin/"

DJANGO_STATIC_SAVE_PREFIX = "{{ static_root }}"
DJANGO_STATIC_NAME_PREFIX = "/static/"
