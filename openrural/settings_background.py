from openrural.settings import *

# Disable default logging config, because a bug in django-background-task
# means that any existing logging config overrides the command-line options.
# See https://github.com/lilspikey/django-background-task/issues/2

del(LOGGING)
