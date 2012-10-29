import datetime

from ebpub.db.models import Schema, SchemaField

from openrural.data_dashboard.scrapers import DashboardMixin
from openrural.retrieval.base.google import GoogleSpreadsheetScraper


class WhitevilleIncidentsScraper(DashboardMixin, GoogleSpreadsheetScraper):

    # Scraper settings.
    logname = 'incidents'
    schema_slugs = ('incidents',)

    # Google Spreadsheets settings.
    spreadsheet_id = '0AhFobZtWx47pdFhEZ204NC1vUkZqTHlkczQwNm8yU1E'
    attribute_names = ('agencyname', 'oca', 'primaryincident',
            'datetimereported')
    match_names = ('oca',)

    def save(self, old_record, list_record, detail_record):
        datetime_format = '%m/%d/%Y %H:%M:%S'
        self.create_or_update(
            old_record=old_record,
            attributes=self._get_attributes(list_record),
            title=list_record.get('primaryincident', 'Incident'),
            item_date=datetime.datetime.strptime(
                list_record['datetimereported'], datetime_format),
            location_name=list_record.get('locationofincidentstreet', None),
            city=list_record.get('locationofincidentcity', None),
            state='NC',
            zipcode=list_record.get('locationofincidentzip', None),
            convert_to_block=True,
        )

    def _create_schema(self):
        """
        Called by DashboardMixin if schema doesn't exist or should be reset.
        """
        slug = self.schema_slugs[0]

        Schema.objects.filter(slug=slug).delete()
        schema = Schema.objects.create(
            name='Incident',
            plural_name='Incidents',
            indefinite_article='an',
            slug=slug,
            last_updated=datetime.datetime.now(),
            date_name='When',
            date_name_plural='When',
            is_public=True,
            has_newsitem_detail=True,
            allow_charting=True,
        )

        SchemaField.objects.filter(schema__slug=slug).delete()
        SchemaField.objects.create(schema=schema,
            pretty_name='Responding Agency',
            pretty_name_plural='Responding Agencies',
            name='agencyname',
            real_name='varchar01',
            display=True,
            is_searchable=False,
            display_order=1,
        )
        SchemaField.objects.create(schema=schema,
            pretty_name='Report Number',
            pretty_name_plural='Report Numbers',
            name='oca',
            real_name='varchar02',
            display=True,
            is_searchable=False,
            display_order=2,
        )
        SchemaField.objects.create(schema=schema,
            pretty_name='Primary Incident',
            pretty_name_plural='Primary Incidents',
            name='primaryincident',
            real_name='varchar03',
            display=True,
            is_searchable=False,
            display_order=3,
        )
        SchemaField.objects.create(schema=schema,
            pretty_name='Time',
            pretty_name_plural='Times',
            name='datetimereported',
            real_name='time01',
            display=False,
            is_searchable=False,
            display_order=5,
        )
