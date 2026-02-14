# data/crypto.py

from __future__ import annotations

import random
from typing import Dict, List
from datetime import datetime, timezone


# ============= CRYPTO DATA =============

CRYPTOCURRENCIES = {
    "btc": {
        "name": "Bitcoin",
        "symbol": "BTC",
        "emoji": "₿",
        "base_price": 50000,
        "volatility": 0.05,  # 5% price swings
        "description": "The original cryptocurrency",
        "color": 0xF7931A,
    },
    "eth": {
        "name": "Ethereum",
        "symbol": "ETH",
        "emoji": "Ξ",
        "base_price": 3000,
        "volatility": 0.06,
        "description": "Smart contract platform",
        "color": 0x627EEA,
    },
    "doge": {
        "name": "Dogecoin",
        "symbol": "DOGE",
        "emoji": "🐕",
        "base_price": 0.15,
        "volatility": 0.15,  # Very volatile
        "description": "Much wow, very crypto",
        "color": 0xC2A633,
    },
    "ada": {
        "name": "Cardano",
        "symbol": "ADA",
        "emoji": "🔷",
        "base_price": 0.50,
        "volatility": 0.08,
        "description": "Research-driven blockchain",
        "color": 0x0033AD,
    },
    "sol": {
        "name": "Solana",
        "symbol": "SOL",
        "emoji": "◎",
        "base_price": 100,
        "volatility": 0.10,
        "description": "High-performance blockchain",
        "color": 0x14F195,
    },
    "xrp": {
        "name": "Ripple",
        "symbol": "XRP",
        "emoji": "💧",
        "base_price": 0.60,
        "volatility": 0.07,
        "description": "Digital payment protocol",
        "color": 0x23292F,
    },
    "bnb": {
        "name": "Binance Coin",
        "symbol": "BNB",
        "emoji": "🔶",
        "base_price": 300,
        "volatility": 0.06,
        "description": "Binance exchange token",
        "color": 0xF3BA2F,
    },
    "matic": {
        "name": "Polygon",
        "symbol": "MATIC",
        "emoji": "🟣",
        "base_price": 0.80,
        "volatility": 0.09,
        "description": "Ethereum scaling solution",
        "color": 0x8247E5,
    },
    "shib": {
        "name": "Shiba Inu",
        "symbol": "SHIB",
        "emoji": "🐶",
        "base_price": 0.000010,
        "volatility": 0.20,  # Meme coin, very volatile
        "description": "Doge killer meme coin",
        "color": 0xFFA409,
    },
    "pepe": {
        "name": "Pepe",
        "symbol": "PEPE",
        "emoji": "🐸",
        "base_price": 0.0000015,
        "volatility": 0.25,  # Extremely volatile
        "description": "Meme coin phenomenon",
        "color": 0x3D9970,
    },
}


# ============= PRICE SIMULATION =============

class CryptoPriceSimulator:
    """Simulate crypto prices with realistic volatility."""
    
    def __init__(self):
        self.prices: Dict[str, float] = {}
        self.price_history: Dict[str, List[float]] = {}
        self.trends: Dict[str, str] = {}  # "up", "down", "stable"
        
        # Initialize prices
        for crypto_id, crypto_data in CRYPTOCURRENCIES.items():
            self.prices[crypto_id] = crypto_data["base_price"]
            self.price_history[crypto_id] = [crypto_data["base_price"]]
            self.trends[crypto_id] = "stable"
    
    def update_prices(self):
        """Update all crypto prices."""
        for crypto_id, crypto_data in CRYPTOCURRENCIES.items():
            current_price = self.prices[crypto_id]
            volatility = crypto_data["volatility"]
            
            # Random price change
            change_percent = random.uniform(-volatility, volatility)
            new_price = current_price * (1 + change_percent)
            
            # Ensure price doesn't go negative or too crazy
            base_price = crypto_data["base_price"]
            new_price = max(base_price * 0.1, min(new_price, base_price * 10))
            
            self.prices[crypto_id] = new_price
            
            # Update history (keep last 24 data points)
            if crypto_id not in self.price_history:
                self.price_history[crypto_id] = []
            self.price_history[crypto_id].append(new_price)
            if len(self.price_history[crypto_id]) > 24:
                self.price_history[crypto_id].pop(0)
            
            # Determine trend
            if len(self.price_history[crypto_id]) >= 2:
                if new_price > self.price_history[crypto_id][-2]:
                    self.trends[crypto_id] = "up"
                elif new_price < self.price_history[crypto_id][-2]:
                    self.trends[crypto_id] = "down"
                else:
                    self.trends[crypto_id] = "stable"
    
    def get_price(self, crypto_id: str) -> float:
        """Get current price of a crypto."""
        return self.prices.get(crypto_id, 0)
    
    def get_24h_change(self, crypto_id: str) -> float:
        """Get 24h price change percentage."""
        history = self.price_history.get(crypto_id, [])
        if len(history) < 2:
            return 0
        
        old_price = history[0]
        current_price = history[-1]
        
        return ((current_price - old_price) / old_price) * 100
    
    def get_trend(self, crypto_id: str) -> str:
        """Get current trend (up/down/stable)."""
        return self.trends.get(crypto_id, "stable")
    
    def get_price_chart(self, crypto_id: str, width: int = 20) -> str:
        """Generate ASCII price chart."""
        history = self.price_history.get(crypto_id, [])
        if len(history) < 2:
            return "📊 Insufficient data"
        
        # Normalize prices to fit in chart
        min_price = min(history)
        max_price = max(history)
        price_range = max_price - min_price
        
        if price_range == 0:
            return "📈" * width
        
        # Create simple chart
        chart = []
        for price in history[-width:]:
            normalized = (price - min_price) / price_range
            
            if normalized >= 0.75:
                chart.append("📈")
            elif normalized >= 0.5:
                chart.append("📊")
            elif normalized >= 0.25:
                chart.append("📉")
            else:
                chart.append("📉")
        
        return "".join(chart)


# Global price simulator instance
price_simulator = CryptoPriceSimulator()
