__all__ = ["parser"]
import argparse
parser = argparse.ArgumentParser(prog="gdocs_downloader")
parser.add_argument('-c', '--credential-file', required=True,
        help='JSON-formatted file with Google account credentials')
parser.add_argument('-u', '--doc-url', required=True,
        help='URL of the document to download')
parser.add_argument('-v', '--verbose', required=False,
        help='Enable verbose (debug) logging')
