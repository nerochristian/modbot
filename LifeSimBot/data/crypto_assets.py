# data/crypto_assets.py
from __future__ import annotations
import random

# Crypto assets with realistic-ish starting prices
CRYPTO_ASSETS = {
    "BTC": {
        "name": "Bitcoin",
        "symbol": "BTC",
        "price": 45000.0,
        "volatility": 0.05,  # 5% price swing
        "description": "The original cryptocurrency",
        "emoji": "₿",
        "color": 0xF7931A
    },
    "ETH": {
        "name": "Ethereum",
        "symbol": "ETH",
        "price": 2500.0,
        "volatility": 0.07,
        "description": "Smart contract platform",
        "emoji": "Ξ",
        "color": 0x627EEA
    },
    "BNB": {
        "name": "Binance Coin",
        "symbol": "BNB",
        "price": 300.0,
        "volatility": 0.06,
        "description": "Binance exchange token",
        "emoji": "💰",
        "color": 0xF3BA2F
    },
    "SOL": {
        "name": "Solana",
        "symbol": "SOL",
        "price": 100.0,
        "volatility": 0.10,
        "description": "High-speed blockchain",
        "emoji": "◎",
        "color": 0x14F195
    },
    "ADA": {
        "name": "Cardano",
        "symbol": "ADA",
        "price": 0.50,
        "volatility": 0.08,
        "description": "Research-driven blockchain",
        "emoji": "₳",
        "color": 0x0033AD
    },
    "DOGE": {
        "name": "Dogecoin",
        "symbol": "DOGE",
        "price": 0.08,
        "volatility": 0.15,
        "description": "The meme coin",
        "emoji": "🐕",
        "color": 0xC2A633
    },
    "DOT": {
        "name": "Polkadot",
        "symbol": "DOT",
        "price": 7.0,
        "volatility": 0.09,
        "description": "Multichain protocol",
        "emoji": "⬤",
        "color": 0xE6007A
    },
    "MATIC": {
        "name": "Polygon",
        "symbol": "MATIC",
        "price": 0.80,
        "volatility": 0.10,
        "description": "Ethereum scaling solution",
        "emoji": "🟣",
        "color": 0x8247E5
    },
    "SHIB": {
        "name": "Shiba Inu",
        "symbol": "SHIB",
        "price": 0.00001,
        "volatility": 0.20,
        "description": "Doge killer meme coin",
        "emoji": "🐕",
        "color": 0xFFA409
    },
    "AVAX": {
        "name": "Avalanche",
        "symbol": "AVAX",
        "price": 35.0,
        "volatility": 0.09,
        "description": "Fast smart contracts platform",
        "emoji": "🔺",
        "color": 0xE84142
    }
}

# Crypto news events that affect prices
CRYPTO_NEWS_EVENTS = [
    {
        "event": "Major exchange hack reported",
        "effect": -0.15,
        "affected": ["BTC", "ETH", "BNB"]
    },
    {
        "event": "Government regulation announced",
        "effect": -0.10,
        "affected": ["BTC", "ETH", "SOL"]
    },
    {
        "event": "Major company adopts crypto",
        "effect": 0.20,
        "affected": ["BTC", "ETH"]
    },
    {
        "event": "Celebrity endorsement",
        "effect": 0.30,
        "affected": ["DOGE", "SHIB"]
    },
    {
        "event": "Network upgrade successful",
        "effect": 0.15,
        "affected": ["ETH", "SOL", "ADA"]
    },
    {
        "event": "Mining difficulty increases",
        "effect": 0.05,
        "affected": ["BTC"]
    },
    {
        "event": "Whale moves large amount",
        "effect": -0.08,
        "affected": ["BTC", "ETH"]
    },
    {
        "event": "DeFi protocol exploit",
        "effect": -0.12,
        "affected": ["ETH", "MATIC", "AVAX"]
    },
    {
        "event": "Partnership announced",
        "effect": 0.18,
        "affected": ["DOT", "MATIC", "AVAX"]
    },
    {
        "event": "Market correction",
        "effect": -0.10,
        "affected": ["BTC", "ETH", "SOL", "ADA"]
    }
]

# Stock market assets
STOCK_ASSETS = {
    "AAPL": {
        "name": "Apple Inc.",
        "symbol": "AAPL",
        "price": 180.0,
        "volatility": 0.02,
        "sector": "Technology",
        "dividend_yield": 0.005,
        "emoji": "🍎"
    },
    "MSFT": {
        "name": "Microsoft",
        "symbol": "MSFT",
        "price": 380.0,
        "volatility": 0.02,
        "sector": "Technology",
        "dividend_yield": 0.008,
        "emoji": "💻"
    },
    "GOOGL": {
        "name": "Google",
        "symbol": "GOOGL",
        "price": 140.0,
        "volatility": 0.03,
        "sector": "Technology",
        "dividend_yield": 0.0,
        "emoji": "🔍"
    },
    "AMZN": {
        "name": "Amazon",
        "symbol": "AMZN",
        "price": 160.0,
        "volatility": 0.03,
        "sector": "E-commerce",
        "dividend_yield": 0.0,
        "emoji": "📦"
    },
    "TSLA": {
        "name": "Tesla",
        "symbol": "TSLA",
        "price": 250.0,
        "volatility": 0.08,
        "sector": "Automotive",
        "dividend_yield": 0.0,
        "emoji": "🚗"
    },
    "META": {
        "name": "Meta Platforms",
        "symbol": "META",
        "price": 350.0,
        "volatility": 0.04,
        "sector": "Social Media",
        "dividend_yield": 0.0,
        "emoji": "📱"
    },
    "NVDA": {
        "name": "NVIDIA",
        "symbol": "NVDA",
        "price": 500.0,
        "volatility": 0.06,
        "sector": "Technology",
        "dividend_yield": 0.002,
        "emoji": "🎮"
    },
    "DIS": {
        "name": "Disney",
        "symbol": "DIS",
        "price": 90.0,
        "volatility": 0.03,
        "sector": "Entertainment",
        "dividend_yield": 0.0,
        "emoji": "🏰"
    },
    "KO": {
        "name": "Coca-Cola",
        "symbol": "KO",
        "price": 60.0,
        "volatility": 0.015,
        "sector": "Beverages",
        "dividend_yield": 0.03,
        "emoji": "🥤"
    },
    "MCD": {
        "name": "McDonald's",
        "symbol": "MCD",
        "price": 280.0,
        "volatility": 0.02,
        "sector": "Fast Food",
        "dividend_yield": 0.022,
        "emoji": "🍔"
    }
}
