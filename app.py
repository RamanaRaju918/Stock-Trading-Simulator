from cs50 import SQL
from flask import Flask, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv

from helpers import apology, login_required, lookup, usd

# Load environment variables from .env when running locally
load_dotenv()

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    id = session["user_id"]
    yours = db.execute("SELECT symbol, shares FROM owned WHERE user_id = ?", id)
    balance = db.execute("SELECT cash FROM users WHERE id = ?", id)
    sum = 0
    quotes = []

    for row in yours:
        quote = lookup(row["symbol"])
        quote["shares"] = row["shares"]
        quote["total"] = row["shares"] * quote["price"]
        sum += quote["total"]
        quotes.append(quote)

    return render_template("index.html", quotes=quotes, balance=balance[0]["cash"], sum=sum)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")

        check = lookup(symbol)

        if check is None:
            return apology("must provide valid symbol", 400)

        shares = request.form.get("shares")

        if not shares or not shares.isdigit():
            return apology("must provide postive integer", 400)

        shares = int(shares)

        if shares <= 0:
            return apology("must provide value greater than 0", 400)

        cost = shares * check["price"]
        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]

        if cost > cash:
            return apology("must have enough balance to buy", 403)

        db.execute("UPDATE users SET cash = cash - ? WHERE id = ?", cost, session["user_id"])

        db.execute("INSERT INTO transactions (user_id, shares, symbol, stock_price, amount, type) VALUES (?, ?, ?, ?, ?, 'Buy')",
                   session["user_id"], shares, check["symbol"], check["price"], cost)

        row = db.execute("SELECT shares FROM owned WHERE user_id = ? AND symbol = ?",
                         session["user_id"], check["symbol"])

        if row:
            db.execute("UPDATE owned SET shares = shares + ? WHERE user_id = ? AND symbol = ?",
                       shares, session["user_id"], check["symbol"])
        else:
            db.execute("INSERT INTO owned (user_id, symbol, shares) VALUES (?, ?, ?)",
                       session["user_id"], check["symbol"], shares)

        return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    transactions = db.execute(
        "SELECT * FROM transactions WHERE user_id = ? ORDER BY timestamp DESC",
        session["user_id"]
    )
    return render_template("history.html", transactions=transactions)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        symbol = request.form.get("symbol")

        if not symbol:
            return apology("must provide symbol", 400)

        quote = lookup(symbol)

        if quote is None:
            return apology("must provide valid symbol", 400)

        return render_template("quoted.html", quote=quote)

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirmation")

        if not username:
            return apology("must provide username", 400)

        elif not password:
            return apology("must provide password", 400)

        elif not confirm_password:
            return apology("must provide confirmation password", 400)

        if password != confirm_password:
            return apology("must provide same passwords", 400)

        rows = db.execute("SELECT * FROM users WHERE username = ?", username)

        if rows:
            return apology("must provide unique username", 400)
        else:
            hashed_password = generate_password_hash(password)
            db.execute("INSERT INTO users (username, hash, cash) VALUES (?, ?, ?)",
                       username, hashed_password, 10000)
            return redirect("/login")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""
    if request.method == "POST":
        user_id = session["user_id"]
        symbol = (request.form.get("symbol") or "").strip().upper()
        shares_input = request.form.get("shares")

        if not symbol:
            return apology("must provide stock symbol", 400)

        if not shares_input or not shares_input.isdigit():
            return apology("must provide a positive integer", 400)

        shares = int(shares_input)
        if shares <= 0:
            return apology("must provide a value greater than 0", 400)

        owned = db.execute(
            "SELECT shares FROM owned WHERE symbol = ? AND user_id = ?",
            symbol, user_id
        )

        if not owned:
            return apology("you do not own this stock", 400)

        if shares > owned[0]["shares"]:
            return apology("cannot sell more shares than you own", 400)

        quote = lookup(symbol)
        if quote is None:
            return apology("could not retrieve current stock price", 400)

        earning = shares * quote["price"]

        db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", earning, user_id)
        db.execute(
            "UPDATE owned SET shares = shares - ? WHERE user_id = ? AND symbol = ?",
            shares, user_id, symbol
        )
        db.execute(
            "INSERT INTO transactions (user_id, shares, symbol, stock_price, amount, type) VALUES (?, ?, ?, ?, ?, 'Sell')",
            user_id, shares, symbol, quote["price"], earning
        )

        remaining = db.execute(
            "SELECT shares FROM owned WHERE user_id = ? AND symbol = ?",
            user_id, symbol
        )
        if remaining and remaining[0]["shares"] == 0:
            db.execute(
                "DELETE FROM owned WHERE user_id = ? AND symbol = ?",
                user_id, symbol
            )

        return redirect("/")

    stocks = db.execute(
        "SELECT symbol FROM owned WHERE user_id = ? AND shares > 0",
        session["user_id"]
    )
    return render_template("sell.html", stocks=stocks)

@app.route("/changepassword", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        if not request.form.get("oldpassword"):
            return apology("must provide password", 403)
        elif not request.form.get("newpassword"):
            return apology("must provide new password", 403)
        elif not request.form.get("newconfirmation"):
            return apology("must provide confirmation", 403)

        if request.form.get("newpassword") != request.form.get("newconfirmation"):
            return apology("must provide same passwords", 403)

        rows = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])

        if not check_password_hash(rows[0]["hash"], request.form.get("oldpassword")):
            return apology("must provide correct password", 403)
        else:
            hashed_password = generate_password_hash(request.form.get("newpassword"))
            db.execute("UPDATE users SET hash = ? WHERE id = ?",
                       hashed_password, session["user_id"])
            session.clear()
            return redirect("/login")
    else:
        return render_template("changepassword.html")
