# Stock Trading Simulator

A Flask-based stock trading simulator with user authentication, stock quotes, buying, selling, portfolio tracking, transaction history, and password changes.

## Features

- User registration and login
- Password hashing
- $10,000 starting cash for every new user
- Stock quote lookup using Alpha Vantage
- Buy and sell stocks
- Portfolio tracking
- Transaction history
- Change password
- SQLite database using the CS50 SQL library

## Requirements

Python 3 and an Alpha Vantage API key.

## Run locally

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the project folder:

```text
ALPHAVANTAGE_API_KEY=your_api_key_here
```

Never commit `.env` to GitHub. It is included in `.gitignore`.

3. Start the application:

```bash
flask run
```

Open the local URL shown by Flask, normally `http://127.0.0.1:5000`.

## Database

`finance.db` is included as a clean starter database containing the required tables but no user accounts. It can therefore be committed to GitHub safely as a starter database. Do not commit a database containing real or personal user data.

## Stock API

The project uses Alpha Vantage's `GLOBAL_QUOTE` endpoint for stock prices. The API key is loaded from the `ALPHAVANTAGE_API_KEY` environment variable.

The free Alpha Vantage service has request limits and its standard quote endpoint may not provide real-time US quotes.
