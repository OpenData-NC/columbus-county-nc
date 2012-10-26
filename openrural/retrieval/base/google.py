from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper

from gdata.spreadsheet.service import SpreadsheetsService


class GoogleScraperException(Exception):
    pass


class GoogleSpreadsheetScraper(NewsItemListDetailScraper):
    """Uses the gdata library to scrape data from a Google Spreadsheet.

    Subclasses are required to set the 'spreadsheet_id' and 'worksheet_id'
    attributes.
    """
    # Scraper settings.
    has_detail = False

    # Google Spreadsheet settings.
    # Must be set in subclass.
    spreadsheet_id = None
    worksheet_id = None
    username = None
    password = None

    def __init__(self, *args, **kwargs):
        self._connected = False

        if not (self.spreadsheet_id and self.worksheet_id and
                self.username and self.password):
            raise GoogleScraperException('Subclasses must specify '
                    'spreadsheet_id, worksheet_id, username, and password.')

        self._client = SpreadsheetsService()
        self._connect(username=self.username, password=self.password)
        if not self._connected:
            raise GoogleScraperException('There was an error in connecting.')
        super(GoogleSpreadsheetScraper, self).__init__(*args, **kwargs)

    def _connect(self, username=None, password=None):
        username = username or self.username
        password = password or self.password
        self._connected = False
        try:
            self._client.ClientLogin(username, password)
        except:
            pass
        else:
            self._connected = True

    def list_pages(self):
        """Iterator that yields list pages as strings."""
        if not self._connected:
            raise GoogleScraperException('Not connected to an account.')
        yield self._client.GetListFeed(self.spreadsheet_id,
                self.worksheet_id).entry

    def parse_list(self, page):
        """
        Given a page, yields a dictionary of data for each record on the page.
        """
        for r in page:
            row = {}
            for key in r.custom.keys():
                row[key] = r.custom[key].text
            yield row
