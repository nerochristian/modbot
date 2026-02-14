# services/crypto_service.py

from __future__ import annotations
import random
import string
import json
from typing import Dict, Tuple, Optional
from datetime import datetime, timezone

from data.crypto_assets import CRYPTO_ASSETS, CRYPTO_NEWS_EVENTS


class CryptoService:
    """Cryptocurrency price management and trading service."""

    def __init__(self, db):
        self.db = db
        self.current_prices: Dict[str, float] = {}
        self.last_update: Optional[datetime] = None
        self.init_prices()

    def init_prices(self) -> None:
        """Initialize crypto prices from base data."""
        for symbol, data in CRYPTO_ASSETS.items():
            self.current_prices[symbol] = data["price"]
        self.last_update = datetime.now(timezone.utc)

    def get_current_price(self, symbol: str) -> float:
        """Get current price for a crypto asset."""
        if not self.current_prices:
            self.init_prices()
        return self.current_prices.get(symbol, 0.0)

    def get_all_prices(self) -> Dict[str, float]:
        """Get all current crypto prices."""
        if not self.current_prices:
            self.init_prices()
        return self.current_prices.copy()

    def update_prices(self) -> Dict[str, float]:
        """
        Update all crypto prices (called periodically).
        Returns dict of price changes.
        """
        if not self.current_prices:
            self.init_prices()

        changes = {}

        # Random chance for news event
        if random.random() < 0.05:  # 5% chance
            event = random.choice(CRYPTO_NEWS_EVENTS)
            for symbol in event["affected"]:
                if symbol in self.current_prices:
                    old_price = self.current_prices[symbol]
                    self.current_prices[symbol] *= (1 + event["effect"])
                    self.current_prices[symbol] = max(0.00001, self.current_prices[symbol])
                    changes[symbol] = ((self.current_prices[symbol] - old_price) / old_price) * 100

        # Normal volatility for all assets
        for symbol, data in CRYPTO_ASSETS.items():
            if symbol not in self.current_prices:
                continue

            volatility = data["volatility"]
            change_pct = random.uniform(-volatility, volatility)

            old_price = self.current_prices[symbol]
            self.current_prices[symbol] *= (1 + change_pct)
            self.current_prices[symbol] = max(0.00001, self.current_prices[symbol])

            if symbol not in changes:  # Don't override news event change
                changes[symbol] = ((self.current_prices[symbol] - old_price) / old_price) * 100

        self.last_update = datetime.now(timezone.utc)
        return changes

    def tick_prices(self) -> Dict[str, float]:
        """Alias for update_prices for backward compatibility."""
        return self.update_prices()

    def new_wallet_address(self) -> str:
        """Generate a random wallet address."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

    def get_portfolio(self, userdata: dict) -> Dict[str, float]:
        """Get user's crypto portfolio as dict."""
        try:
            portfolio_str = userdata.get("crypto_portfolio", "{}")
            if isinstance(portfolio_str, dict):
                return portfolio_str
            return json.loads(portfolio_str)
        except:
            return {}

    def save_portfolio(self, userid: str, portfolio: Dict[str, float]) -> None:
        """Save user's crypto portfolio."""
        portfolio_str = json.dumps(portfolio)
        self.db.updatestat(userid, "crypto_portfolio", portfolio_str)

    def calculate_portfolio_value(self, portfolio: Dict[str, float]) -> float:
        """Calculate total USD value of portfolio."""
        total = 0.0
        for symbol, amount in portfolio.items():
            price = self.get_current_price(symbol)
            total += amount * price
        return total

    def buy_crypto(self, userid: str, symbol: str, usd_amount: int) -> Tuple[float, float, float]:
        """
        Buy crypto with USD.

        Returns:
            (amount_bought, price_per_unit, new_portfolio_value)
        """
        price = self.get_current_price(symbol)
        if price <= 0:
            raise ValueError(f"Invalid price for {symbol}")

        amount = usd_amount / price

        # Get portfolio
        u = self.db.getuser(userid)
        portfolio = self.get_portfolio(u)

        # Add to portfolio
        portfolio[symbol] = portfolio.get(symbol, 0.0) + amount

        # Save
        self.save_portfolio(userid, portfolio)
        self.db.removebalance(userid, usd_amount)

        new_value = self.calculate_portfolio_value(portfolio)

        return amount, price, new_value

    def sell_crypto(self, userid: str, symbol: str, amount: float) -> Tuple[int, float, float]:
        """
        Sell crypto for USD.

        Returns:
            (usd_received, price_per_unit, new_portfolio_value)
        """
        price = self.get_current_price(symbol)
        if price <= 0:
            raise ValueError(f"Invalid price for {symbol}")

        usd_value = int(amount * price)

        # Get portfolio
        u = self.db.getuser(userid)
        portfolio = self.get_portfolio(u)

        # Remove from portfolio
        portfolio[symbol] = max(0.0, portfolio.get(symbol, 0.0) - amount)
        if portfolio[symbol] == 0:
            portfolio.pop(symbol, None)

        # Save
        self.save_portfolio(userid, portfolio)
        self.db.addbalance(userid, usd_value)

        new_value = self.calculate_portfolio_value(portfolio)

        return usd_value, price, new_value

    def calculate_profit_loss(self, portfolio: Dict[str, float], initial_investment: int) -> Tuple[float, float]:
        """
        Calculate profit/loss.

        Returns:
            (profit_usd, profit_percentage)
        """
        current_value = self.calculate_portfolio_value(portfolio)
        profit = current_value - initial_investment
        profit_pct = (profit / initial_investment) * 100 if initial_investment > 0 else 0.0

        return profit, profit_pct

    def get_asset_info(self, symbol: str) -> Optional[dict]:
        """Get information about a crypto asset."""
        return CRYPTO_ASSETS.get(symbol)

    def get_all_assets(self) -> Dict[str, dict]:
        """Get all available crypto assets."""
        return CRYPTO_ASSETS.copy()

    def get_market_data(self) -> list:
        """
        Get formatted market data for all cryptos.
        
        Returns list of dicts with symbol, price, and asset info.
        """
        market_data = []
        for symbol, asset_info in CRYPTO_ASSETS.items():
            current_price = self.get_current_price(symbol)
            market_data.append({
                "symbol": symbol,
                "name": asset_info["name"],
                "price": current_price,
                "emoji": asset_info["emoji"],
                "volatility": asset_info["volatility"],
                "description": asset_info.get("description", "")
            })
        return market_data


# Backward compatibility: global functions that use a singleton instance
_service_instance: Optional[CryptoService] = None


def _get_service():
    """Get or create singleton service instance."""
    global _service_instance
    if _service_instance is None:
        raise RuntimeError("CryptoService not initialized. Call init_crypto_service(db) first.")
    return _service_instance


def init_crypto_service(db) -> CryptoService:
    """Initialize the global crypto service instance."""
    global _service_instance
    _service_instance = CryptoService(db)
    return _service_instance


def get_current_price(symbol: str) -> float:
    """Backward compatibility wrapper."""
    return _get_service().get_current_price(symbol)


def tick_prices() -> Dict[str, float]:
    """Backward compatibility wrapper."""
    return _get_service().tick_prices()


def new_wallet_address() -> str:
    """Backward compatibility wrapper."""
    return _get_service().new_wallet_address()


def get_portfolio(userdata: dict) -> Dict[str, float]:
    """Backward compatibility wrapper."""
    return _get_service().get_portfolio(userdata)


def save_portfolio(db, userid: str, portfolio: Dict[str, float]) -> None:
    """Backward compatibility wrapper."""
    return _get_service().save_portfolio(userid, portfolio)


def calculate_portfolio_value(portfolio: Dict[str, float]) -> float:
    """Backward compatibility wrapper."""
    return _get_service().calculate_portfolio_value(portfolio)


def buy_crypto(db, userid: str, symbol: str, usd_amount: int) -> Tuple[float, float, float]:
    """Backward compatibility wrapper."""
    return _get_service().buy_crypto(userid, symbol, usd_amount)


def sell_crypto(db, userid: str, symbol: str, amount: float) -> Tuple[int, float, float]:
    """Backward compatibility wrapper."""
    return _get_service().sell_crypto(userid, symbol, amount)


def calculate_profit_loss(portfolio: Dict[str, float], initial_investment: int) -> Tuple[float, float]:
    """Backward compatibility wrapper."""
    return _get_service().calculate_profit_loss(portfolio, initial_investment)
