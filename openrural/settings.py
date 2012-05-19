"""
Copy this to settings.py, uncomment the various settings, and
edit them as desired.
"""

from ebpub.settings_default import *

########################
# CORE DJANGO SETTINGS #
########################

ADMINS = (
    ('Open Rural Team', 'openrural-team@caktusgroup.com'),
)

MANAGERS = ADMINS

DEBUG = True
TIME_ZONE = 'US/Eastern'

PROJECT_DIR = os.path.normpath(os.path.dirname(__file__))
INSTALLED_APPS = (
    'djcelery',
    'openrural',
    'gunicorn',
    'seacucumber',
    'openrural.data_dashboard',
) + INSTALLED_APPS
TEMPLATE_DIRS = (os.path.join(PROJECT_DIR, 'templates'), ) + TEMPLATE_DIRS
ROOT_URLCONF = 'openrural.urls'

STATIC_URL = '/'

#########################
# CUSTOM EBPUB SETTINGS #
#########################

# The domain for your site.
EB_DOMAIN = 'localhost'

# This is the short name for your city, e.g. "chicago".
SHORT_NAME = 'whiteville'

# Where to center citywide maps, eg. on homepage.
DEFAULT_MAP_CENTER_LON = -78.700562
DEFAULT_MAP_CENTER_LAT = 34.3389
DEFAULT_MAP_ZOOM = 13

# Metros. You almost certainly only want one dictionary in this list.
# See the configuration docs for more info.
METRO_LIST = (
    {
        # Extent of the region, as a longitude/latitude bounding box.
        'extent': (-79.131456, 33.926189, -78.145433, 34.475916),

        # Whether this region should be displayed to the public.
        'is_public': True,

        # Set this to True if the region has multiple cities.
        # You will also need to set 'city_location_type'.
        'multiple_cities': True,

        # The major city in the region.
        'city_name': 'Whiteville',

        # The SHORT_NAME in the settings file.
        'short_name': SHORT_NAME,

        # The name of the region, as opposed to the city (e.g., "Miami-Dade" instead of "Miami").
        'metro_name': 'Columbus County',

        # USPS abbreviation for the state.
        'state': 'NC',

        # Full name of state.
        'state_name': 'North Carolina',

        # Time zone, as required by Django's TIME_ZONE setting.
        'time_zone': TIME_ZONE,

        # Slug of an ebpub.db.LocationType that represents cities.
        # Only needed if multiple_cities = True.
        'city_location_type': 'cities',
    },
)

# Set both of these to distinct, secret strings that include two instances
# of '%s' each. Example: 'j8#%s%s' -- but don't use that, because it's not
# secret.  And don't check the result in to a public code repository
# or otherwise put it out in the open!
PASSWORD_CREATE_SALT = '%s%s'
PASSWORD_RESET_SALT = '%s%s'

# You probably don't need to override this, the setting in settings.py
# should work out of the box.
#EB_MEDIA_ROOT = '' # necessary for static media versioning.

EB_MEDIA_URL = '' # leave at '' for development

# This is used as a "From:" in e-mails sent to users.
GENERIC_EMAIL_SENDER = 'openblock@' + EB_DOMAIN

# Filesystem location of scraper log.
SCRAPER_LOGFILE_NAME = '/tmp/scraperlog_openrural'

# If this cookie is set with the given value, then the site will give the user
# staff privileges (including the ability to view non-public schemas).
STAFF_COOKIE_NAME = 'obstaff_openrural'
STAFF_COOKIE_VALUE = ''

# What LocationType to redirect to when viewing /locations.
DEFAULT_LOCTYPE_SLUG = 'neighborhoods'

# What kinds of news to show on the homepage.
# This is one or more Schema slugs.
HOMEPAGE_DEFAULT_NEWSTYPES = [u'news-articles']

# How many days of news to show on the homepage, place detail view,
# and elsewhere.
DEFAULT_DAYS = 7

# Edit this if you want to control where
# scraper scripts will put their HTTP cache.
# (Warning, don't put it in a directory encrypted with ecryptfs
# or you'll likely have "File name too long" errors.)
HTTP_CACHE = '/tmp/openblock_scraper_cache_openrural'

CACHES = {
    # Use whatever Django cache backend you like;
    # FileBasedCache is a reasonable choice for low-budget, memory-constrained
    # hosting environments.
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/tmp/openrural_cache'
          # # Use this to disable caching.
          #'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

MAP_BASELAYER_TYPE = 'google.streets'

LOGGING['formatters']['basic'] = {
    'format': '%(asctime)s %(name)-20s %(levelname)-8s %(message)s',
}
LOGGING['loggers'][''] = {'handlers': ['null'], 'level': 'INFO',
                          'propagate': True}
LOGGING['loggers']['openrural'] = {'propagate': True}
LOGGING['loggers']['ebpub'] = {'propagate': True}
LOGGING['loggers']['ebdata'] = {'propagate': True}
LOGGING['loggers']['eb'] = {'propagate': True}
LOGGING['loggers']['data_dashboard'] = {'propagate': True}
LOGGING['loggers']['django'] = {'propagate': True, 'level': 'INFO'}
LOGGING['loggers']['celery'] = {'propagate': True, 'level': 'DEBUG'}
CELERYD_HIJACK_ROOT_LOGGER = False

CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'
