
import csv
import logging
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
    def __init__(self, client, input_dir, output_dir):
        self.client = client
        self.input_dir = input_dir
        self.output_dir = output_dir

        self.output_headers = [
            'BookId',
            'Title',
            'Author',
            'Rating',
            'NlbBranch',
            'NlbStatus',
            'NlbDueDate',
            'NlbCallNo',
            'NlbShelf',
            'ISBN',
            'ISBN13'
        ]
        self.NUM_WORKERS = multiprocessing.cpu_count()
        logging.info(f"Multithreading uses {self.NUM_WORKERS} threads!")
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

        def get_availability(client, row):
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
                            'BookId': row['Book Id'],
                            'Title': row['Title'],
                            'Author': row['Author'],
                            'Rating': row['Average Rating'],
                            'NlbBranch': item.branch_name,
                            'NlbStatus': item.status_desc,
                            'NlbDueDate': (item.due_date if item.status_desc == 'On Loan' else None),
                            'NlbCallNo': item.call_number,
                            'NlbShelf': item.location_desc,
                            'ISBN': row['ISBN'],
                            'ISBN13': row['ISBN13']
                        }                    
                        # print(f'Branch: {item.branch_name}\nStatus: {item.status_desc}\n')
                        output_rows.append(result_dict)
            else:
                pass
            return output_rows


        for row in tqdm(books):
            output_rows = get_availability(client, row)
            out_queue.put(output_rows)
        return

    def start_threads(self, num_books_per_worker):
        threads = []
        row_count = 0
        for i in range(self.NUM_WORKERS):
            args = (self.client, self.filtered_rows[row_count:row_count + num_books_per_worker[i]], self.write_queue)
            t = threading.Thread(name=f"Worker{i}", target=self.worker, args=args)
            row_count += num_books_per_worker[i]
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()

    def write_to_file(self, writer):
        all_output_rows = []
        while not self.write_queue.empty():
            output_rows = self.write_queue.get()
            all_output_rows.extend(output_rows)

        all_output_rows = sorted(all_output_rows, key=lambda row: row['GoodreadsRating'], reverse=True)
        writer.writerows(all_output_rows)

    def process_csv(self, csv_path):
        output_path = self._get_output_path(csv_path)
        with open(str(csv_path),'r') as inputf, open(str(output_path),'w') as outputf:
            reader = csv.DictReader(inputf)
            writer = csv.DictWriter(outputf, fieldnames=self.output_headers)
            writer.writeheader()
            logging.info(f"Reading from {csv_path} \nWriting to {output_path}")
            self.filtered_rows = self.filter_rows(reader)
            num_books_per_worker = self.get_num_objs_per_worker(len(self.filtered_rows))

            self.start_threads(num_books_per_worker)
            self.write_to_file(writer)
            # for row in tqdm(list(reader)):
            #     if row['Bookshelves'] == 'to-read':
            #         output_rows = self.get_availability(row)
            #         writer.writerows(output_rows)


    def process_all(self):
        csv_paths = list(self.input_dir.glob('*.csv'))
        for csv_path in csv_paths:
            self.process_csv(csv_path)
        return csv_paths





    # results = client.search('How China Escaped the Poverty Trap', author='yuen yuen ang', media_code=MediaCode.BOOKS, limit=5)
    # # results = client.search('lord of the rings', author='tolkien', media_code=MediaCode.BOOKS, limit=3)
    # for title in results.titles:
    #     print(f'Title: {title.title_name}\nISBN: {title.isbn}\nPublished: {title.publish_year}\n')

    # availability = client.get_availability_info(isbn='1328915336')
    # for item in availability.items:
    #     pprint(item.__dict__)
    #     # print(f'Branch: {item.branch_name}\nStatus: {item.status_desc}\n')