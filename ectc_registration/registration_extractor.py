import logging
_log = logging.getLogger(__name__)

from .gdocs_downloader import GoogleDocsDownloader
import json

class RegistrationExtractor():
    def __init__(self, registration_doc_url, doc_downloader):
        self.doc_url = registration_doc_url
        self.docs_downloader = doc_downloader

    def get_registration_workbooks(self):
        """Gets the registration workbooks in the registration document.

        Returns:
            A list of schools and their registration document URLs.
        """
        sheets = self.docs_downloader.get_sheets(self.doc_url)
        dashboard_url = sheets['Schools']['exportcsv']
        dashboard_body = self.docs_downloader.download_file(dashboard_url)[1]
        dashboard_reader = self.docs_downloader.body_to_csv(dashboard_body)

        next(dashboard_reader) #schools start on the third row
        next(dashboard_reader)

        registered_schools = []
        for row in dashboard_reader:
            school_name = row[0]
            if not school_name: #blank line signals end of schools list
                break
            doc_url = row[1]
            if not doc_url: #no registration document provided
                continue

            registered_schools.append(SchoolRegistrationExtractor(
                    school_name=school_name, registration_doc_url=doc_url,
                    approved=(row[3] == "Yes")))

        return registered_schools

class SchoolRegistrationExtractor():

    TEAM_SHEET_NAMES = ["Mens_A", "Mens_B", "Mens_C", "Womens_A", "Womens_B",
            "Womens_C"]

    def __init__(self, school_name, registration_doc_url, approved=False):
        self.school_name = school_name
        self.registration_doc_url = registration_doc_url
        self.approved = approved

    def extract(self, doc_downloader):
        registration_doc_feed_url = self.registration_doc_url
        sheets = doc_downloader.get_sheets(registration_doc_feed_url)
        self.extract_competitors(self.download_roster_csv(
                sheets, doc_downloader))
        self.extract_teams(sheets, doc_downloader)

    def download_roster_csv(self, sheets, doc_downloader):
        roster_doc_body = doc_downloader.download_file(
                sheets['Weigh-Ins']['exportcsv'])[1]
        return doc_downloader.body_to_csv(roster_doc_body)

    def extract_competitors(self, roster_csv):
        for i in range(10):
            next(roster_csv) #roster starts on 11th row

        self.extracted_competitors=[]
        for row in roster_csv:
            if not row[3]:
                #_log.debug("Skipping empty line")
                continue
            competitor = {}
            competitor['name'] = row[3]
            competitor['rank'] = row[4]
            competitor['sex'] = row[6]
            if not row[20]:
                _log.debug(competitor['name'] + " has empty weight field")
                self.extracted_competitors.append(competitor)
                continue
            try:
                competitor['weight'] = float(row[20])
            except ValueError:
                _log.warning("Failed to parse weight field [%s] for %s" %(
                        row[20], competitor['name']))
            self.extracted_competitors.append(competitor)

    def extract_teams(self, sheets, doc_downloader):
        self.teams = {}
        for sheet_name in self.TEAM_SHEET_NAMES:
            teams = self.extract_division_teams(
                    sheets[sheet_name]['exportcsv'], doc_downloader)
            self.teams[sheet_name] = teams

    def download_division_teams_csv(self, sheet_url, doc_downloader):
        division_teams_body = doc_downloader.download_file(sheet_url)[1]
        return doc_downloader.body_to_csv(division_teams_body)

    def extract_division_teams(self, sheet_url, doc_downloader):
        division_teams_csv = self.download_division_teams_csv(sheet_url,
                doc_downloader)

        for i in range(6):
            next(division_teams_csv) # teams start on 7th line

        return [self.read_team(division_teams_csv) for i in range(10)]

    def read_team(self, division_teams_csv):
        # read lightweight, middleweight, heavyweight, alternate1, alternate2
        members = [next(division_teams_csv)[3] for i in range(5)]
        return members if any(members) else None

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
    downloader = GoogleDocsDownloader(creds)
    reg_extracter = RegistrationExtractor(doc_url, downloader)
    registered_schools = reg_extracter.get_registration_workbooks()
    _log.info("Parsed %d registered schools" %(len(registered_schools)))

    for school in registered_schools:
        _log.info("Importing for %s from %s"
                %(school.school_name, school.registration_doc_url))
        school.extract(downloader)
        _log.info("Parsed %d competitors from %s"
                %(len(school.extracted_competitors), school.school_name))

        for team_sheet_name in SchoolRegistrationExtractor.TEAM_SHEET_NAMES:
            _log.info("Recorded %d teams for %s from sheet %s" %(
                    sum(map(bool,school.teams[team_sheet_name])),
                    school.school_name, team_sheet_name))
