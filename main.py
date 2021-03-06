import requests
from dotenv import load_dotenv
import os
import json
from datetime import datetime, date, timedelta
import time
from bs4 import BeautifulSoup
import yfinance as yf

load_dotenv()

API_LAST_CALL = None


class ETF:
    def __init__(self, symbol):
        self.symbol = symbol
        self.holdings = {}
        self.generate_holdings()
    
    def generate_holdings(self):
        symbols = scrape_etf_db(self.symbol)
        for symbol, percent in symbols.items():
            self.holdings[symbol] = {"stock": Stock(symbol), "percent": percent}
        
    def last_day_change(self):
        print("% change vs previous day")
        for holding in self.holdings:
            last_change = self.holdings[holding].get('stock').get_last_change()
            if last_change:
                last_change = f"{round(last_change, 2)}%"
            print(f"{holding}:{' '*(10-len(holding))}{last_change}")
    
    def today(self):
        print("changes today")
        etf_quote = Stock(self.symbol)
        
        print("{:>15}{:>15}{:>15}{:>15}{:>15}{:>15}{:>15}".format("Ticker",
                                                      "Current Price",
                                                      "Day Change",
                                                      "%",
                                                      "weight",
                                                      "weighted amount",
                                                      "weighted %"))

        print("{:>15}{:>15}{:>15}{:>15}{:>15}{:>15}{:>15}".format(etf_quote.symbol,
                                                      etf_quote.current_price,
                                                      round(float(etf_quote.day_change_amount), 2),
                                                      round(float(etf_quote.day_change_percent) * 100, 2) if etf_quote.day_change_percent else '',
                                                      "100%",
                                                      "-",
                                                      "-"
                                                      )
              )
        print("\n")
        for ticker, stock in self.holdings.items():
            stock, weight = stock.values()
            day_change_amount = float(stock.day_change_amount) if stock.day_change_amount else None
            day_change_percent = float(stock.day_change_percent) if stock.day_change_percent else None
            weight_float = float(weight.replace("%", "")) / 100
            weighted_amount = round(day_change_amount * weight_float, 4) if day_change_amount else None
            weighted_percent = round(day_change_percent * weight_float * 100, 4) if day_change_percent else None
            print("{:>15}{:>15}{:>15}{:>15}{:>15}{:>15}{:>15}".format(ticker,
                                                                      stock.current_price,
                                                                      day_change_amount or '',
                                                                      f"{round(day_change_percent * 100, 2)}%" or '',
                                                                      weight,
                                                                      weighted_amount or '',
                                                                      f"{round(weighted_percent, 2)}%" or '',
                                                                      ))
            
        
class Stock:
    def __init__(self, symbol):
        self.symbol = symbol
        self.daily = {}
        self.last_updated = None
        # self.fill_daily()
        # self.generate_change()
        self.current_price = ""
        self.current_price_last_updated = ""
        self.day_change_percent = ""
        self.day_change_amount = ""
        self.get_current_price()
    
    def __str__(self):
        return self.symbol
    
    def __repr__(self):
        return self.symbol
    
    def fill_daily(self):
        if self.last_updated and self.last_updated == date.today():
            # do nothing
            pass
        else:
            daily_data = AlphaVantage().get_time_series_daily(symbol=self.symbol)
            if not daily_data:
                return
            for day, data in daily_data.items():
                self.daily[day] = {k[3:]: float(v) for k, v in data.items()}
            self.last_updated = date.today()
    
    def generate_change(self):
        for _date, data in self.daily.items():
            for i in range(1, 5):
                try:
                    year, month, day = [int(d) for d in _date.split("-")]
                    dt = date(year=year, month=month, day=day)
                    previous_day = self.daily[str(dt - timedelta(days=i))]
                    break
                except KeyError:
                    pass
            else:
                # end of data
                break
            self.daily[_date]['change_absolute'] = data['close'] - previous_day['close']
            self.daily[_date]['change_percent'] = ((data['close'] - previous_day['close']) / previous_day['close']) * 100
    
    def get_last_change(self, percent=True):
        # todo: check if there's any data
        try:
            if percent:
                return self.daily[str(get_last_weekday())].get('change_percent')
            return self.daily[str(get_last_weekday())].get('change_absolute')
        except KeyError:
            return None
    
    def get_current_price(self):
        iex = IexCloud()
        quote = iex.get_quote(self.symbol)
        if quote:
            self.current_price = quote.get('latestPrice')
            self.day_change_amount = quote.get('change')
            self.day_change_percent = quote.get('changePercent')
            self.current_price_last_updated = datetime.now()
            
            if not quote.get("change"):
                self.day_change_amount = self.current_price - quote.get("previousClose")
            
            if not quote.get("changePercent"):
                self.day_change_percent = (self.current_price - quote.get("previousClose")) / quote.get("previousClose")


class AlphaVantage:
    def __init__(self):
        self.base_url = "https://www.alphavantage.co"
        self.api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        self.cache_dir = "quotes"
    
    def get_price(self, symbol: str):
        global API_LAST_CALL
        
        symbol = symbol.upper()
        q = f"{self.base_url}/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={self.api_key}"
        while API_LAST_CALL and datetime.now() <= API_LAST_CALL + timedelta(seconds=(60/5)):
            time.sleep(1)
        API_LAST_CALL = datetime.now()
        response = requests.get(q)
        print(response.json())
    
    def get_time_series_daily(self, symbol: str):
        global API_LAST_CALL
        
        # check cache
        symbol = symbol.upper()
        if os.path.isfile(f"{self.cache_dir}/{symbol}.json"):
            with open(f"{self.cache_dir}/{symbol}.json") as file:
                data = json.loads(file.read())
            # check last updated
            if not data or not data.get('Meta Data'):
                return None
            if data.get('Meta Data').get('3. Last Refreshed') == str(get_last_weekday()):
                return data.get('Time Series (Daily)')
        
        print(f"API call for {symbol}")
        q = f"{self.base_url}/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={self.api_key}"
        while API_LAST_CALL and datetime.now() <= API_LAST_CALL + timedelta(seconds=(60/5)):
            time.sleep(1)
        response = requests.get(q)
        API_LAST_CALL = datetime.now()
        print(response)
        print(response.status_code)
        if response.status_code == 503:
            print(response.content)
            print(response.reason)
            return None
        j = response.json()
        print(j)
        if "Note" in j and "Thank you for using Alpha Vantage!" in j.get("Note"):
            API_LAST_CALL += timedelta(minutes=1)
            self.get_time_series_daily(symbol)
            symbol = symbol.upper()
            if os.path.isfile(f"{self.cache_dir}/{symbol}.json"):
                with open(f"{self.cache_dir}/{symbol}.json") as file:
                    data = json.loads(file.read())
                # check last updated
                if not data or not data.get('Meta Data'):
                    return None
                if data.get('Meta Data').get('3. Last Refreshed') == str(get_last_weekday()):
                    return data.get('Time Series (Daily)')
            
        
        with open(f"{self.cache_dir}/{symbol}.json", "w") as file:
            file.write(json.dumps(j))
        return j.get('Time Series (Daily)')


def scrape_etf_db(etf_symbol: str, force: bool = False):
    etf_symbol = etf_symbol.upper()
    fn = f"etfs/{etf_symbol}.json"
    if os.path.isfile(fn) and not force:
        with open(fn) as file:
            return json.loads(file.read())
    
    print(f"scraping etfdb for {etf_symbol}")
    res = requests.get(f"https://etfdb.com/etf/{etf_symbol}")
    soup = BeautifulSoup(res.content, 'html.parser')
    data = {}
    table = soup.find('table', {'id': 'etf-holdings'})
    for row in table.find('tbody').find_all('tr'):
        symbol, name, percent = row.find_all('td')
        href = symbol.find('a')['href'].split("/")
        symbol = href[-1] if href[-1] else href[-2]  # '/stock/LSCC/' - dealing with trailing /
        percent = percent.text
        if ":" in symbol:
            ticker, exchange = symbol.split(":")
            symbol = f"{exchange}:{ticker}"
        print(symbol)
        data[symbol] = percent
    
    with open(fn, "w") as file:
        file.write(json.dumps(data))
    return data


def get_last_weekday(dt=False):
    # todo - ignores holidays
    the_date = date.today()
    if dt:
        the_date = datetime.combine(date.today(), datetime.min.time())
    while the_date.weekday() > 4:
        the_date -= timedelta(days=1)
    return the_date

    
class IexCloud:
    def __init__(self, sandbox=False):
        self.endpoint = "https://sandbox.iexapis.com/stable" if sandbox else "https://cloud.iexapis.com/stable"
        self.api_key = os.getenv("IEX_CLOUD_SANDBOX_API_KEY") if sandbox else os.getenv('IEX_CLOUD_API_KEY')
        self.params = {"token": self.api_key}
    
    def get_quote(self, symbol):
        url = self.endpoint + f'/stock/{symbol}/quote/'
        res = requests.get(url, params={"token": self.api_key})
        if res.status_code != 200:
            print(f"{symbol} - {res.status_code}: {res.reason}")
            return None
        # print(res.json())
        return res.json()
    
    def get_price(self, symbol):
        url = self.endpoint + f'/stock/{symbol}/price/'
        res = requests.get(url, params=self.params)
        print(res.json())
        return res.json()
    
    def get_news(self, symbol, last=10):
        url = self.endpoint + f"/stock/{symbol}/news/last/{last}"
        res = requests.get(url, params=self.params)
        return res.json()
        

if __name__ == '__main__':
    dt = date.today()
    today = datetime.combine(dt, datetime.min.time())
    etf = ETF('btec')
    etf.today()
    # iex = IexCloud()
    # iex.get_quote('aapl')
    #
    # aapl = Stock('AAPL')
    # print(aapl.daily)
    # print(f"last change was {aapl.daily[today].get('change_absolute')}")
    # print(f"last change was {aapl.daily[today].get('change_percent')}")
    #
    # tsla = Stock('TSLA')
    # print(tsla.daily)
    # print(f"last change was {tsla.daily[today].get('change_absolute')}")
    # print(f"last change was {tsla.daily[today].get('change_percent')}")
    
    # scrape an etf
    # ETF('qtum').last_day_change()
    
    # my etfs
    # etfs = ["driv", "tan", "lit", "arkk", "qtum", "btec", "dtec", "psct"]
    # for etf in etfs:
    #     ETF(etf).last_day_change()
    # ETF("TAN").last_day_change()