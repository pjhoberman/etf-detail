# ETF Detail

Very much a proof of concept work in progress.

## Installation
1. Clone the repo
1. Set up a virtual env
1. `pip install -r requirements.txt`
1. In `main.py`, edit your etfs at the very end. Start with one or two.
1. Get an API key from [AlphaVantage](https://www.alphavantage.co/support/#api-key), edit `sample.env` and move the file to `.env`
1. Run it! In pycharm, `ctrl` + `r`

Note: It'll take a long time to run the first time. The script caches calls so it'll be faster the next time around, but, the api is limited to 5 calls per minute, and the script implements that limit. 
