DESCRIPTION = """
This script will upload the CSV to Gdrive
"""


import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from utils.gdrive_uploader import Uploader


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument(
        "csvfile", help="CSV file to upload", type=str
    )
    parser.add_argument(
        "--config", help="Config file", type=str, default='config.env'
    )
    args = parser.parse_args()

    env_path = Path('.') / args.config
    load_dotenv(dotenv_path=env_path, verbose=True, override=True)

    nlb_uploader = Uploader(args.csvfile)
    nlb_uploader.upload()