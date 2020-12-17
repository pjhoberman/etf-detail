import requests
from dotenv import load_dotenv
import os
import json
from datetime import datetime, date, timedelta

load_dotenv()


class Stock:
    def __init__(self, symbol):
        self.symbol = symbol
        self.daily = {}
        self.last_updated = None
        self.fill_daily()
        self.generate_change()
    
    def fill_daily(self):
        if self.last_updated and self.last_updated == date.today():
            # do nothing
            pass
        else:
            daily_data = StockAPI().get_time_series_daily(symbol=self.symbol)
            for day, data in daily_data.items():
                self.daily[datetime.strptime(day, "%Y-%m-%d")] = {k[3:]: float(v) for k, v in data.items()}
            self.last_updated = date.today()
            
    def generate_change(self):
        for _date, data in self.daily.items():
            for i in range(1, 5):
                try:
                    previous_day = self.daily[_date - timedelta(days=i)]
                    break
                except KeyError:
                    pass
            else:
                # end of data
                break
            data['change_absolute'] = data['close'] - previous_day['close']
            data['change_percent'] = ((data['close'] - previous_day['close']) / previous_day['close']) * 100
        

class StockAPI:
    def __init__(self):
        self.base_url = "https://www.alphavantage.co"
        self.api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        self.cache_dir = "quotes"
    
    def get_time_series_daily(self, symbol: str):
        # check cache
        symbol = symbol.upper()
        if os.path.isfile(f"{self.cache_dir}/{symbol}.json"):
            with open(f"{symbol}.json") as file:
                data = json.loads(file.read())
            # check last updated
            if data.get('Meta Data').get('3. Last Refreshed') == str(get_last_weekday()):
                return data.get('Time Series (Daily)')
        
        print(f"API call for {symbol}")
        q = f"{self.base_url}/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={self.api_key}"
        response = requests.get(q)
        j = response.json()
        
        with open(f"{self.cache_dir}{symbol}.json", "w") as file:
            file.write(json.dumps(j))
        return j.get('Time Series (Daily)')


def get_last_weekday():
    # todo - ignores holidays
    the_date = date.today()
    while the_date.weekday() > 4:
        the_date -= timedelta(days=1)
    return the_date


if __name__ == '__main__':
    dt = date.today()
    today = datetime.combine(dt, datetime.min.time())
    
    aapl = Stock('AAPL')
    print(aapl.daily)
    print(f"last change was {aapl.daily[today].get('change_absolute')}")
    print(f"last change was {aapl.daily[today].get('change_percent')}")

    tsla = Stock('TSLA')
    print(tsla.daily)
    print(f"last change was {tsla.daily[today].get('change_absolute')}")
    print(f"last change was {tsla.daily[today].get('change_percent')}")
