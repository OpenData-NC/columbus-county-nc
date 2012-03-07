from openrural.settings_{{ deployment_tag }} import *

DEBUG = False

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': '{{ database_name }}',
        'USER': '{{ database_user }}',
        'PASSWORD': '{{ database_password }}',
        'HOST': '{{ database_host }}',
        'PORT': '',
    }
}

MEDIA_ROOT = "{{ media_root }}"

STATIC_ROOT = "{{ static_root }}"

ADMIN_MEDIA_PREFIX = "/media/admin/"

DJANGO_STATIC_SAVE_PREFIX = "{{ static_root }}"
DJANGO_STATIC_NAME_PREFIX = "/static/"

# Set both of these to distinct, secret strings that include two instances
# of '%%s' each. Example: 'j8#%%s%%s' -- but don't use that, because it's not
# secret.  And don't check the result in to a public code repository
# or otherwise put it out in the open!
PASSWORD_CREATE_SALT = '%%s%%s'
PASSWORD_RESET_SALT = '%%s%%s'

# If this cookie is set with the given value, then the site will give the user
# staff privileges (including the ability to view non-public schemas).
STAFF_COOKIE_NAME = 'obstaff_openrural'
STAFF_COOKIE_VALUE = ''
