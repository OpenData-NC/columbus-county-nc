from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from ebpub.db.models import Schema


class Command(BaseCommand):
    args = "<schema_slug schema_slug ...>"
    help = "Sets public = False on the specified schemas."
    default_option = make_option('--default', action='store_true',
            dest='default', default=False,
            help="Use default choices: local-news, open311-service-requests")
    option_list = BaseCommand.option_list + (default_option,)

    def handle(self, *args, **options):
        default_slugs = ('local-news', 'open311-service-requests')
        if options['default']:
            print "Using default slug choices."
            slugs = default_slugs
        else:
            slugs = args

        if slugs:
            msg = "Setting public = False on {0} schemas with the following " \
                    "slugs: \n  {1}".format(len(slugs), "\n  ".join(slugs))
            print msg
            schemas = Schema.objects.filter(slug__in=slugs)
            num_updated = schemas.update(is_public=False)
            msg = "Updated {0} schemas.".format(num_updated)
            print msg
        else:
            msg = "Updated 0 schemas."
            print msg
