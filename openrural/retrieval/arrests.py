import datetime

from ebpub.db.models import Schema, SchemaField

from openrural.data_dashboard.scrapers import DashboardMixin
from openrural.retrieval.base.google import GoogleSpreadsheetScraper


class WhitevilleArrestsScraper(DashboardMixin, GoogleSpreadsheetScraper):

    # Scraper settings.
    logname = 'arrests'
    schema_slugs = ('arrests',)

    # Google Spreadsheets settings
    spreadsheet_id = '0AhFobZtWx47pdHYyMGp1cTFEcDJudjRpM2lKd09ZaWc'
    match_names = ('oca',)
    attribute_names = ('oca', 'age', 'consumeddrugalcohol',
            'ifarmedtypeofweapon', 'primarycharge', 'felony', 'agencyname')

    def save(self, old_record, list_record, detail_record):
        datetime_format = '%m/%d/%Y %H:%M:%S'
        name = ' '.join([list_record[f] for f in
                ('namefirst', 'namemiddle', 'namelast')])
        attributes = self._get_attributes(list_record)
        attributes['name'] = name
        self.create_or_update(
            old_record=old_record,
            attributes=attributes,
            title=name,
            item_date=datetime.datetime.strptime(
                list_record['datetimeofarrest'], datetime_format),
            location_name=list_record['currentaddressstreet'],
            city=list_record['currentaddresscity'],
            state=list_record['currentaddressstate'],
            zipcode=list_record['currentaddresszip'],
        )

    def _create_schema(self):
        """
        Called by DashboardMixin if schema doesn't exist or should be reset.
        """
        slug = self.schema_slugs[0]

        Schema.objects.filter(slug=slug).delete()
        schema = Schema.objects.create(
            name='Arrest',
            plural_name='Arrests',
            indefinite_article='an',
            slug=slug,
            last_updated=datetime.datetime.now(),
            date_name='Arrest Date',
            date_name_plural='Arrest Dates',
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
            pretty_name='Name',
            pretty_name_plural='Names',
            name='name',
            real_name='varchar03',
            display=False,
            is_searchable=False,
            display_order=3,
        )
        SchemaField.objects.create(schema=schema,
            pretty_name='Age',
            pretty_name_plural='Ages',
            name='age',
            real_name='int01',
            display=True,
            is_searchable=False,
            display_order=4,
        )
        SchemaField.objects.create(schema=schema,
            pretty_name='Primary Charge',
            pretty_name_plural='Primary Charges',
            name='primarycharge',
            real_name='text01',
            display=True,
            is_searchable=False,
            display_order=6,
        )
        SchemaField.objects.create(schema=schema,
            pretty_name='Drug Involvement',
            pretty_name_plural='Drug Involvement',
            name='consumeddrugalcohol',
            real_name='bool01',
            display=True,
            is_searchable=False,
            display_order=7,
        )
        SchemaField.objects.create(schema=schema,
            pretty_name='Weapons',
            pretty_name_plural='Weapons',
            name='ifarmedtypeofweapon',
            real_name='varchar05',
            display=True,
            is_searchable=False,
            display_order=8,
        )
        SchemaField.objects.create(schema=schema,
            pretty_name='Felony',
            pretty_name_plural='Felonies',
            name='felony',
            real_name='bool02',
            display=True,
            is_searchable=False,
            display_order=9,
        )
