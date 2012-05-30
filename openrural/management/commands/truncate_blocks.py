from django.core.management.base import BaseCommand
from django.db import connection, transaction


class Command(BaseCommand):
    help = 'Truncate OpenBlock geocoder tables'

    def handle(self, *args, **options):
        cursor = connection.cursor()
        cursor.execute("""TRUNCATE TABLE blocks CASCADE;""")
        cursor.execute("""TRUNCATE TABLE streets CASCADE;""")
        cursor.execute("""TRUNCATE TABLE db_location CASCADE;""")
        transaction.commit_unless_managed()
