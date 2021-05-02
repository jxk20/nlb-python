DESCRIPTION = """
This script will look at all the csvs in 'inputs'
Gets all 'to-read' books
Outputs their availability into 'outputs'
"""
import argparse
import csv
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from pprint import pprint

from dotenv import load_dotenv
from nlbsg import Client, MediaCode
from nlbsg.catalogue import STAGING_URL, PRODUCTION_URL
from tqdm import tqdm



INPUT_DIR = Path('inputs')
OUTPUT_DIR = Path('outputs')



class NlbChecker():
    def __init__(self, client, input_dir, output_dir):
        self.client = client
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.output_headers = [
            'GoodreadsBookId',
            'Title',
            'Author',
            'AuthorLF',
            'NlbBranch',
            'NlbStatus',
            'NlbDueDate',
            'NlbCallNo',
            'NlbShelf',
            'GoodreadsRating',
            'ISBN',
            'ISBN13'
        ]

    def get_output_path(self, csv_path):
        stem = csv_path.stem
        suffix = csv_path.suffix
        parent = csv_path.parent
        return self.output_dir / f"{stem}-caa{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.csv"    

    def get_availability(self, row):
        """
        1) Use ISBN to search,
        2) Else, Use title and author (TODO)
        """
        output_rows = []
        isbn = re.sub("[^0-9]", "", row['ISBN'])
        if isbn != '':
            availability = client.get_availability_info(isbn=isbn)
            if availability.items:
                for item in availability.items:
                    result_dict = {
                        'GoodreadsBookId': row['Book Id'],
                        'Title': row['Title'],
                        'Author': row['Author'],
                        'AuthorLF': row['Author l-f'],
                        'NlbBranch': item.branch_name,
                        'NlbStatus': item.status_desc,
                        'NlbDueDate': (item.due_date if item.status_desc == 'On Loan' else None),
                        'NlbCallNo': item.call_number,
                        'NlbShelf': item.location_desc,
                        'GoodreadsRating': row['Average Rating'],
                        'ISBN': row['ISBN'],
                        'ISBN13': row['ISBN13']
                    }                    
                    print(f'Branch: {item.branch_name}\nStatus: {item.status_desc}\n')
                    output_rows.append(result_dict)
        else:
            pass
        return output_rows

    def process_csv(self, csv_path):
        output_path = self.get_output_path(csv_path)
        with open(str(csv_path),'r') as inputf, open(str(output_path),'w') as outputf:
            reader = csv.DictReader(inputf)
            writer = csv.DictWriter(outputf, fieldnames=self.output_headers)
            writer.writeheader()
            logging.info(f"Reading from {csv_path}")
            logging.info(f"Writing to {output_path}")
            for row in tqdm(list(reader)):
                if row['Bookshelves'] == 'to-read':
                    output_rows = self.get_availability(row)
                    writer.writerows(output_rows)


    def process_all(self):
        for csv_path in self.input_dir.glob('*.csv'):
            self.process_csv(csv_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument(
        "--config", help="Config file", type=str, default='config.env'
    )
    args = parser.parse_args()

    env_path = Path('.') / args.config
    load_dotenv(dotenv_path=env_path, verbose=True, override=True)

    API_KEY = os.environ.get(API_KEY)

    client = Client(PRODUCTION_URL, API_KEY)
    nlb_checker = NlbChecker(client=client, input_dir=INPUT_DIR, output_dir=OUTPUT_DIR)
    nlb_checker.process_all()




    # results = client.search('How China Escaped the Poverty Trap', author='yuen yuen ang', media_code=MediaCode.BOOKS, limit=5)
    # # results = client.search('lord of the rings', author='tolkien', media_code=MediaCode.BOOKS, limit=3)
    # for title in results.titles:
    #     print(f'Title: {title.title_name}\nISBN: {title.isbn}\nPublished: {title.publish_year}\n')

    # availability = client.get_availability_info(isbn='1328915336')
    # for item in availability.items:
    #     pprint(item.__dict__)
    #     # print(f'Branch: {item.branch_name}\nStatus: {item.status_desc}\n')
