from openrural.settings.base import *

DEBUG = True

CELERY_ALWAYS_EAGER = True
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
CELERYD_HIJACK_ROOT_LOGGER = False

# enable for local logging
# LOGGING['handlers']['file'] = {
#         'level': 'DEBUG',
#         'class': 'logging.FileHandler',
#         'formatter': 'basic',
#         'filename': os.path.join(PROJECT_DIR, 'openrural.log'),
# }
# LOGGING['loggers'][''] = {'handlers': ['file'], 'level': 'DEBUG',
#                           'propagate': True}
