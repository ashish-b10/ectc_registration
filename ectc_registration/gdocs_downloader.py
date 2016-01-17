import logging
_log = logging.getLogger(__name__)

import httplib2
import json
import xml.etree.ElementTree as etree
from urllib.parse import urlparse

from oauth2client.client import SignedJwtAssertionCredentials
import csv

SCOPES = 'https://www.googleapis.com/auth/drive.readonly'

def spreadsheet_feed_url(doc_url):
    """Returns the URL for the feed for a spreadsheet."""
    doc_key = urlparse(doc_url).path.split('/')[3]
    return ("https://spreadsheets.google.com/feeds/worksheets/" + doc_key +
            "/private/full")

class GoogleDocsDownloader():
    def __init__(self, json_creds):
        creds = json.loads(json_creds)
        client_email = creds['client_email']
        private_key = creds['private_key']

        self.http_creds = SignedJwtAssertionCredentials(client_email,
                private_key, SCOPES)
        self.http_client = self.http_creds.authorize(httplib2.Http())

    def download_file(self, url):
        """Downloads a file using authenticated credentials."""
        head, body = self.http_client.request(url)
        status_code = int(head['status'])
        if status_code >= 400 or status_code < 200:
            _log.warn("Received status code %d accessing %s"
                    %(status_code, url))
        else:
            _log.info("Successfully downloaded %d bytes from %s" %(
                    len(body), url))
        return head, body

    def get_sheets(self, doc_url):
        """Gets the names and URLs of the sheets of a Google Docs
        spreadsheet.

        Keyword arguments:
        doc_url -- The URL of the Google Docs object
        """
        body = self.download_file(doc_url)[1]
        if not body:
            raise Exception("Request for %s returned empty body"
                    %(doc_feed_url))

        return self.parse_spreadsheet_feed(body)

    def parse_spreadsheet_feed(self, feed_body):
        """Parses the body of a spreadsheet feed.

        Keyword attributes:
        feed_body -- the body of the feed to parse.

        Returns a dict of feeds for each sheet.
        """
        atom_ns = '{http://www.w3.org/2005/Atom}'
        feed_tree = etree.fromstring(feed_body)
        feed_entries = feed_tree.findall(atom_ns + 'entry')
        entries_dict = {}
        for entry in feed_entries:
            sheet_name = entry.find(atom_ns + 'title').text
            sheet_dict = {}
            for link in entry.findall(atom_ns + 'link'):
                fragment = urlparse(link.attrib['rel']).fragment
                if not fragment:
                    continue
                sheet_dict[fragment] = link.attrib['href']

            entries_dict[sheet_name] = sheet_dict
        return entries_dict

    @staticmethod
    def body_to_csv(body):
        body_str = body.decode('utf-8')
        return csv.reader(body_str.splitlines())

if __name__ == "__main__":
    from .argparser import parser
    args = parser.parse_args()
    credential_file = args.credential_file
    doc_url = args.doc_url
    verbose = args.verbose is None

    import sys
    logging_format = '%(levelname)-5s %(name)s:%(lineno)4s - %(message)s'
    if verbose:
        logging.basicConfig(level=logging.DEBUG, stream=sys.stdout,
                format=logging_format)
    else:
        logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                format=logging_format)

    _log.info("Attempting to import from %s" %(doc_url))
    with open(credential_file) as creds_fh:
        creds = creds_fh.read()
    client = GoogleDocsDownloader(creds)

    test_book_sheets = client.get_sheets(spreadsheet_feed_url(doc_url=doc_url))
    _log.info("Workbook %s has sheets %s" %(doc_url,
            ', '.join(test_book_sheets.keys())))
