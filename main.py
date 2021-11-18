DESCRIPTION = """
This script will look at all the csvs in 'inputs'
Gets all 'to-read' books
Outputs their availability into 'outputs'
"""

import argparse
import os
import logging
logger = logging.Logger('Main Logger')
from pathlib import Path

from dotenv import load_dotenv
from nlbsg import Client
from nlbsg.catalogue import PRODUCTION_URL
from utils.gdrive_uploader import Uploader
from utils.nlb_checker import NlbChecker


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument(
        "--config", help="Config file", type=str, default='config.env'
    )
    parser.add_argument(
        "--inputs", help="Input folder", type=str, default='inputs'
    )
    parser.add_argument(
        "--outputs", help="Output folder", type=str, default='outputs'
    )
    parser.add_argument(
        "-u", "--upload-gdrive", help="Flag on whether to write to GoogleDrive", action="store_true"
    )
    parser.add_argument(
        "-n", "--num-threads", help="Number of threads. Max is 1.", type=int, default=1
    )
    args = parser.parse_args()


    INPUT_DIR = Path(args.inputs)
    OUTPUT_DIR = Path(args.outputs)


    env_path = Path('.') / args.config
    load_dotenv(dotenv_path=env_path, verbose=True, override=True)

    API_KEY = os.environ.get('API_KEY')

    logger.info("Starting!")

    client = Client(PRODUCTION_URL, API_KEY)
    nlb_checker = NlbChecker(client=client, input_dir=INPUT_DIR, output_dir=OUTPUT_DIR, num_threads=args.num_threads)
    csv_paths = nlb_checker.process_all()

    if args.upload_gdrive:
        assert len(csv_paths) == 1, f"There should only be 1 CSV in the inputs folder! Currently there are {len(csv_paths)}."
        nlb_uploader = Uploader(csv_paths[0])
        nlb_uploader.upload()