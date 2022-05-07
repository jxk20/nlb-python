import csv
import logging

logger = logging.getLogger(__name__)
import re
from datetime import datetime

from tqdm import tqdm

EMPTY_STR = ""


class NlbChecker:
    def __init__(
        self,
        client,
        input_dir,
        output_dir,
    ):
        self.client = client
        self.input_dir = input_dir
        self.output_dir = output_dir

        self.output_headers = [
            "BookId",
            "Title",
            "Author",
            "NlbCallNo",
            "Rating",
            "NlbBranch",
            "NlbStatus",
            "NlbDueDate",
            "NlbShelf",
            "ISBN",
            "ISBN13",
        ]
        self.num_books = 0
        self.num_available_books = 0
        self.filtered_rows = []
        self.all_output_rows = []

    def _get_output_path(self, csv_path):
        stem = csv_path.stem
        return (
            self.output_dir
            / f"{stem}-caa{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.csv"
        )

    @staticmethod
    def filter_rows(reader):
        return [row for row in reader if row["Exclusive Shelf"] == "to-read"]

    @staticmethod
    def get_due_date(item):
        """Return due date if item is not on loan."""
        if item.status_desc != "Not on Loan":
            return item.due_date
        else:
            return None

    def get_availability(self, client, row):
        """
        1) Use ISBN to search,
        2) Else, Use title and author (TODO)
        """
        output_rows = []
        isbn = re.sub("[^a-zA-Z0-9]", EMPTY_STR, row["ISBN"])
        isbn13 = re.sub("[^a-zA-Z0-9]", EMPTY_STR, row["ISBN13"])
        if isbn != EMPTY_STR or isbn13 != EMPTY_STR:
            self.num_books += 1
            isbn_to_search = isbn if isbn != EMPTY_STR else isbn13
            availability = client.get_availability_info(isbn=isbn_to_search)
            if availability.items:
                self.num_available_books += 1
                for item in availability.items:
                    result_dict = {
                        "BookId": row["Book Id"],
                        "Title": row["Title"],
                        "Author": row["Author"],
                        "NlbCallNo": item.call_number,
                        "Rating": row["Average Rating"],
                        "NlbBranch": item.branch_name,
                        "NlbStatus": item.status_desc,
                        "NlbDueDate": self.get_due_date(item),
                        "NlbShelf": item.location_desc,
                        "ISBN": row["ISBN"],
                        "ISBN13": row["ISBN13"],
                    }
                    output_rows.append(result_dict)
            else:
                result_dict = {
                    "BookId": row["Book Id"],
                    "Title": row["Title"],
                    "Author": row["Author"],
                    "NlbCallNo": EMPTY_STR,
                    "Rating": row["Average Rating"],
                    "NlbBranch": EMPTY_STR,
                    "NlbStatus": EMPTY_STR,
                    "NlbDueDate": EMPTY_STR,
                    "NlbShelf": EMPTY_STR,
                    "ISBN": row["ISBN"],
                    "ISBN13": row["ISBN13"],
                }
                output_rows.append(result_dict)
        return output_rows

    def write_to_file(self, writer):
        """Write results to CSV file"""
        logger.info("Writing to file!")
        sorted_output_rows = sorted(
            self.all_output_rows, key=lambda row: row["Rating"], reverse=True
        )
        writer.writerows(sorted_output_rows)
        percentage_availability = 100 * self.num_available_books / self.num_books
        with open("test.txt", "w") as f:
            f.write(
                f"Available books: {self.num_available_books}/{self.num_books}={percentage_availability:.2f}%"
            )

    def process_csv(self, csv_path):
        output_path = self._get_output_path(csv_path)
        with open(str(csv_path), "r", encoding="utf8") as inputf, open(
            str(output_path), "w", newline=""
        ) as outputf:
            reader = csv.DictReader(inputf)
            writer = csv.DictWriter(outputf, fieldnames=self.output_headers)
            writer.writeheader()
            logger.info(f"Reading from {csv_path} \nWriting to {output_path}")
            self.filtered_rows = self.filter_rows(reader)
            for row in tqdm(self.filtered_rows):
                output_rows = self.get_availability(self.client, row)
                self.all_output_rows.extend(output_rows)
            self.write_to_file(writer)

    def process_all(self):
        csv_paths = list(self.input_dir.glob("*.csv"))
        for csv_path in csv_paths:
            self.process_csv(csv_path)
        return csv_paths
