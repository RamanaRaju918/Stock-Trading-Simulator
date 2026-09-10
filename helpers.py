from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")

import requests
from flask import redirect, render_template, session
from functools import wraps


def apology(message, code=400):
    """Render message to user."""

    def escape(s):
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """Decorate routes to require login."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def lookup(symbol):
    """Look up a stock quote using Alpha Vantage."""
    symbol = (symbol or "").strip().upper()
    api_key = os.environ.get("ALPHAVANTAGE_API_KEY")

    if not symbol or not api_key:
        return None

    url = "https://www.alphavantage.co/query"

    try:
        response = requests.get(
            url,
            params={
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": api_key,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        quote = data.get("Global Quote", {})
        price = quote.get("05. price")
        returned_symbol = quote.get("01. symbol", symbol)

        if not price:
            return None

        return {
            "name": returned_symbol,
            "price": float(price),
            "symbol": returned_symbol,
        }

    except (requests.RequestException, ValueError, TypeError):
        return None


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"
