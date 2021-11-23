# nlb-python

Checks the availability of the books in your Goodreads library in NLB.

## Setup

1. Create a virtualenv or conda environment using the `requirements.txt` file. E.g.

```
conda create --name nlb --file requirements.txt
```

2. Create a `config.env` file. You make take reference to `config-example.env`.

- `API_KEY` refers to your NLB API key. You may get one from [here](https://www.nlb.gov.sg/GetInvolved/ContributeCreate/NLBlabs.aspx)
- `SPREADSHEET_ID` refers to your Google Sheet spreadsheet ID if you wish to upload your output CSV there. Note that this functionality may not work all the time.

## Usage

1. Log into your Goodreads account and go to https://www.goodreads.com/review/import. Download your library as a CSV file by clicking the "Export Library" button.
2. Save your library CSV file into the `inputs` folder.
3. Activate your `nlb` conda or virtualenv environment
4. Run `./run.sh` in your command line.
5. Go to `outputs` to view retrieve the output CSV file.
