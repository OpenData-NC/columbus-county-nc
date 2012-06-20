from openrural.settings.base import *

DEBUG = False

# Graylog2 logging handler
LOGGING['handlers']['gelf'] = {
    'class': 'openrural.data_dashboard.handlers.CustomGELFHandler',
    'host': 'monitor2.caktusgroup.com',
    'port': 12201,
    'extra_fields': {
        'deployment': 'columbusco',
        'environment': 'unknown', # overridden in local_settings.py
    },
}
LOGGING['loggers'][''] = {'handlers': ['gelf'], 'level': 'DEBUG',
                          'propagate': True}
