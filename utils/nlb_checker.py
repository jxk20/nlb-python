
import csv
import logging
logger = logging.getLogger(__name__)
import multiprocessing
import os
import re
import threading
from datetime import datetime
from pathlib import Path
from pprint import pprint
from queue import Queue

from nlbsg import Client, MediaCode
from tqdm import tqdm


class NlbChecker():
    def __init__(self, client, input_dir, output_dir, num_threads=multiprocessing.cpu_count()):
        self.client = client
        self.input_dir = input_dir
        self.output_dir = output_dir

        self.output_headers = [
            'BookId',
            'Title',
            'Author',
            'NlbCallNo',
            'Rating',
            'NlbBranch',
            'NlbStatus',
            'NlbDueDate',
            'NlbShelf',
            'ISBN',
            'ISBN13'
        ]
        self.NUM_WORKERS = min(4,num_threads)
        logger.info(f"Multithreading uses {self.NUM_WORKERS} threads!")
        self.filtered_rows = []
        self.write_queue = Queue()

    def _get_output_path(self, csv_path):
        stem = csv_path.stem
        suffix = csv_path.suffix
        parent = csv_path.parent
        return self.output_dir / f"{stem}-caa{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.csv"    

    @staticmethod
    def filter_rows(reader):
        return [row for row in reader if row['Bookshelves'] == 'to-read']

    def get_num_objs_per_worker(self, num):
        num_objs_per_worker = (num % self.NUM_WORKERS) * [int(num // self.NUM_WORKERS) + 1]
        num_objs_per_worker.extend((self.NUM_WORKERS - num % self.NUM_WORKERS) * [int(num // self.NUM_WORKERS)])
        return num_objs_per_worker

    @staticmethod
    def worker(client, books, out_queue):

        def get_due_date(item):
            if item.status_desc != 'Not on Loan':
                return item.due_date
            else:
                return None

        def get_availability(client, row):
            """
            1) Use ISBN to search,
            2) Else, Use title and author (TODO)
            """
            output_rows = []
            isbn = re.sub("[^a-zA-Z0-9]", "", row['ISBN'])
            isbn13 = re.sub("[^a-zA-Z0-9]", "", row['ISBN13'])
            if isbn != '' or isbn13 != '':
                if isbn != '':
                    isbn_to_search = isbn
                else: 
                    isbn_to_search = isbn13
                availability = client.get_availability_info(isbn=isbn_to_search)
                if availability.items:
                    for item in availability.items:
                        result_dict = {
                            'BookId': row['Book Id'],
                            'Title': row['Title'],
                            'Author': row['Author'],
                            'NlbCallNo': item.call_number,
                            'Rating': row['Average Rating'],
                            'NlbBranch': item.branch_name,
                            'NlbStatus': item.status_desc,
                            'NlbDueDate': get_due_date(item),
                            'NlbShelf': item.location_desc,
                            'ISBN': row['ISBN'],
                            'ISBN13': row['ISBN13']
                        }                    
                        output_rows.append(result_dict)
                else:
                    result_dict = {
                        'BookId': row['Book Id'],
                        'Title': row['Title'],
                        'Author': row['Author'],
                        'NlbCallNo': '',
                        'Rating': row['Average Rating'],
                        'NlbBranch': '',
                        'NlbStatus': '',
                        'NlbDueDate': '',
                        'NlbShelf': '',
                        'ISBN': row['ISBN'],
                        'ISBN13': row['ISBN13']
                    }                    
                    output_rows.append(result_dict)

            else:
                pass
            return output_rows

        for row in tqdm(books):
            output_rows = get_availability(client, row)
            out_queue.put(output_rows)
        return

    def start_threads(self, num_books_per_worker):
        logger.info("Requesting from NLB!")
        threads = []
        row_count = 0
        logging.info(f"Searching availbility for {len(self.filtered_rows)} books!")
        for i in range(self.NUM_WORKERS):
            args = (self.client, self.filtered_rows[row_count:row_count + num_books_per_worker[i]], self.write_queue)
            t = threading.Thread(name=f"Worker{i}", target=self.worker, args=args)
            row_count += num_books_per_worker[i]
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()

    def write_to_file(self, writer):
        logger.info("Writing to file!")
        all_output_rows = []
        num_books = 0
        num_available_books = 0
        while not self.write_queue.empty():
            output_rows = self.write_queue.get()
            all_output_rows.extend(output_rows)
            num_books += 1
            if len(output_rows) == 1 and output_rows[0]['NlbStatus'] == '':
                num_available_books += 1

        all_output_rows = sorted(all_output_rows, key=lambda row: row['Rating'], reverse=True)
        writer.writerows(all_output_rows)
        with open("test.txt",'w') as f:
            f.write(f"Available books: {num_available_books}/{num_books}={100*num_available_books/num_books:.2f}%")

    def process_csv(self, csv_path):
        output_path = self._get_output_path(csv_path)
        with open(str(csv_path),'r',encoding="utf8") as inputf, open(str(output_path),'w', newline='') as outputf:
            reader = csv.DictReader(inputf)
            writer = csv.DictWriter(outputf, fieldnames=self.output_headers)
            writer.writeheader()
            logger.info(f"Reading from {csv_path} \nWriting to {output_path}")
            self.filtered_rows = self.filter_rows(reader)
            num_books_per_worker = self.get_num_objs_per_worker(len(self.filtered_rows))

            self.start_threads(num_books_per_worker)
            self.write_to_file(writer)


    def process_all(self):
        csv_paths = list(self.input_dir.glob('*.csv'))
        for csv_path in csv_paths:
            self.process_csv(csv_path)
        return csv_paths





