import datetime

from ebpub.db.models import NewsItem, Schema, SchemaField

from openrural.data_dashboard.scrapers import DashboardMixin
from openrural.retrieval.base.google import GoogleSpreadsheetScraper


class WhitevilleSchoolsScraper(DashboardMixin, GoogleSpreadsheetScraper):

    # Scraper settings.
    logname = 'schools'
    schema_slugs = ('schools',)

    # Google Spreadsheets settings.
    spreadsheet_id = '0AhFobZtWx47pdEIwTWZCcEVTbE82TXNlNkRZMW5iTHc'
    attribute_names = ('leaname', 'schoolname', 'gradespan', 'expectedgrowth',
            'metalltargetsforannualmeasurableobjectives', 'highgrowth',
            'performancecomposite', 'abcstatus')
    match_names = ('leaname', 'schoolname')

    # Date that the schools data was initially made available.
    # All school NewsItems will share this item_date.
    item_date = datetime.datetime(2012, 8, 2)

    def save(self, old_record, list_record, detail_record):
        self.create_or_update(
            old_record=old_record,
            attributes=self._get_attributes(list_record),
            title=list_record.get('schoolname', ''),
            item_date=self.item_date,
            url=list_record.get('moreinformation', None),
            location_name=list_record.get('address', ''),
            city=list_record.get('city', None),
            state='NC',
            zipcode=list_record.get('zip', None),
        )

    def _create_schema(self):
        """
        Called by DashboardMixin if schema does not exist or should be reset.
        """
        slug = self.schema_slugs[0]

        Schema.objects.filter(slug=slug).delete()
        schema = Schema.objects.create(
            name='School',
            plural_name='Schools',
            indefinite_article='a',
            slug=slug,
            last_updated=datetime.datetime.now(),
            is_public=True,
            has_newsitem_detail=True,
            allow_charting=True,
        )

        SchemaField.objects.filter(schema__slug=slug).delete()
        SchemaField.objects.create(schema=schema,
            pretty_name='LEA Name',
            pretty_name_plural='LEA Names',
            name='leaname',
            real_name='varchar05',
            display=True,
            is_searchable=False,
            display_order=1,
        )
        SchemaField.objects.create(schema=schema,
            pretty_name='School Name',
            pretty_name_plural='School Names',
            name='schoolname',
            real_name='varchar01',
            display=True,
            is_searchable=False,
            display_order=2,
        )
        SchemaField.objects.create(schema=schema,
            pretty_name='Grade Span',
            pretty_name_plural='Grade Spans',
            name='gradespan',
            real_name='varchar03',
            display=True,
            is_searchable=False,
            display_order=3,
        )
        SchemaField.objects.create(schema=schema,
            pretty_name='Performance Composite Score',
            pretty_name_plural='Performance Composite Scores',
            name='performancecomposite',
            real_name='varchar02',
            display=True,
            is_searchable=False,
            display_order=4,
        )
        SchemaField.objects.create(schema=schema,
            pretty_name='Met Annual Targets',
            pretty_name_plural='Met Annual Targets',
            name='metalltargetsforannualmeasurableobjectives'[:32],
            real_name='bool03',
            display=True,
            is_searchable=False,
            display_order=5,
        )
        SchemaField.objects.create(schema=schema,
            pretty_name='Expected Growth',
            pretty_name_plural='Expected Growth',
            name='expectedgrowth',
            real_name='bool01',
            display=True,
            is_searchable=False,
            display_order=6,
        )
        SchemaField.objects.create(schema=schema,
            pretty_name='High Growth',
            pretty_name_plural='High Growth',
            name='highgrowth',
            real_name='bool02',
            display=True,
            is_searchable=False,
            display_order=7,
        )
        SchemaField.objects.create(schema=schema,
            pretty_name='ABC status',
            pretty_name_plural='ABC statuses',
            name='abcstatus',
            real_name='varchar04',
            display=True,
            is_searchable=False,
            display_order=8,
        )
