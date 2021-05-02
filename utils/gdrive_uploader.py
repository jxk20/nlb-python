import os
from datetime import datetime

import gspread


class Uploader():
    def __init__(self, input_csv):
        self.SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')
        self.content = self._read_csv(input_csv)
        self.gc = self._authenticate()

    @staticmethod
    def _read_csv(input_csv):
        return open(input_csv,'r').read()

    @staticmethod
    def _authenticate():
        return gspread.oauth()

    def upload(self):
        self.gc.import_csv(self.SPREADSHEET_ID, self.content.encode('utf-8'))
        wks = self.gc.open_by_key(self.SPREADSHEET_ID).get_worksheet(0)
        wks.update_title(f"caa{datetime.now().strftime('%Y%m%d-%H%M%S')}")
