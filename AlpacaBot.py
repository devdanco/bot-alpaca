import os

from dotenv import load_dotenv
from lumibot.brokers import Alpaca
from lumibot.strategies.strategy import Strategy
from timedelta import Timedelta
from alpaca.data.historical.news import NewsClient
from alpaca.data.requests import NewsRequest
from finbert_utils import estimate_sentiment
from lumibot.traders import Trader
load_dotenv()


BASE_URL = "https://paper-api.alpaca.markets/v2"
ALPACA_CREDS = {
    "API_KEY": os.getenv("API_KEY"),
    "API_SECRET": os.getenv("API_SECRET"),
    "PAPER": True
}


class MLTrader(Strategy):
    def initialize(self, symbol: str = "SPY", cash_at_risk: float = .2):
        self.symbol = symbol
        self.sleeptime = "24H"
        self.last_trade = None
        self.cash_at_risk = cash_at_risk

    def get_dates(self):
        today = self.get_datetime()
        three_days_prior = today - Timedelta(days=3)
        return today.strftime('%Y-%m-%d'), three_days_prior.strftime('%Y-%m-%d')

    def get_sentiment(self):
        today, three_days_prior = self.get_dates()
        news_client = NewsClient(api_key=os.getenv("API_KEY"), secret_key=os.getenv("API_SECRET"))
        news_list = news_client.get_news(NewsRequest(symbol="SPY", start=three_days_prior, end=today))
        headlines = [news.headline for news in news_list.news]
        probability, sentiment = estimate_sentiment(headlines)
        return probability, sentiment

    def position_sizing(self):
        cash = self.get_cash()
        last_price = self.get_last_price(self.symbol)
        quantity = round(cash * self.cash_at_risk / last_price, 0)
        return cash, last_price, quantity

    def on_trading_iteration(self):
        cash, last_price, quantity = self.position_sizing()
        probability, sentiment = self.get_sentiment()

        if cash > last_price:
            if sentiment == "positive" and probability > .999:
                if self.last_trade == "sell":
                    self.sell_all()
                order = self.create_order(
                    self.symbol,
                    quantity,
                    "buy",
                    type="bracket",
                    take_profit_price=last_price * 1.15,
                    stop_loss_price=last_price * .95
                )
                self.submit_order(order)
                self.last_trade = "buy"
            elif sentiment == "negative" and probability > .999:
                if self.last_trade == "buy":
                    self.sell_all()
                order = self.create_order(
                    self.symbol,
                    quantity,
                    "sell",
                    type="bracket",
                    take_profit_price=last_price * .85,
                    stop_loss_price=last_price * 1.05
                )
                self.submit_order(order)
                self.last_trade = "sell"


trader = Trader()
broker = Alpaca(ALPACA_CREDS)
strategy = MLTrader(broker=broker)

trader.add_strategy(strategy)
trader.run_all()

