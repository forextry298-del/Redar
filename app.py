import os, re, secrets, sqlite3
from functools import wraps
from decimal import Decimal, InvalidOperation
from flask import Flask, g, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash

ROOT = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("DATABASE_PATH", os.path.join(ROOT, "hdar.db"))
WELCOME_BONUS_UGX = 3000
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "local-dev-change-this-secret-before-deploying")

def db():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    c.execute("PRAGMA busy_timeout=30000")
    return c

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT NOT NULL UNIQUE COLLATE NOCASE,
          full_name TEXT NOT NULL,
          phone TEXT NOT NULL UNIQUE,
          country TEXT NOT NULL,
          password_hash TEXT NOT NULL,
          referral_code TEXT NOT NULL UNIQUE,
          referred_by TEXT,
          balance_ugx INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY(referred_by) REFERENCES users(referral_code)
        );
        CREATE INDEX IF NOT EXISTS idx_users_referred_by ON users(referred_by);
        CREATE TABLE IF NOT EXISTS ledger(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL REFERENCES users(id),
          amount_ugx INTEGER NOT NULL,
          entry_type TEXT NOT NULL,
          note TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """)

def get_user():
    uid = session.get("user_id")
    if not uid:
        return None
    with db() as c:
        return c.execute(
            "SELECT id,username,full_name,phone,country,referral_code,referred_by,balance_ugx,created_at FROM users WHERE id=?",
            (uid,)
        ).fetchone()

@app.before_request
def load_user():
    g.user = get_user()

def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not g.user:
            flash("Please log in first.", "error")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapped

@app.context_processor
def common():
    return {"welcome_bonus": WELCOME_BONUS_UGX}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/registration", methods=["GET", "POST"])
@app.route("/register", methods=["GET", "POST"])
def register():
    ref = (request.values.get("ref") or request.values.get("referral_code") or "").strip().upper()[:32]
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()[:80]
        username = request.form.get("username", "").strip()[:30]
        phone = re.sub(r"[\s\-()]", "", request.form.get("phone", "").strip())[:24]
        country = request.form.get("country", "Uganda").strip()[:50]
        password = request.form.get("password", "")
        ref = request.form.get("referral_code", "").strip().upper()[:32]
        if len(full_name) < 2:
            flash("Enter your full name.", "error")
        elif len(username) < 3:
            flash("Username must contain at least 3 characters.", "error")
        elif not re.fullmatch(r"\+?[0-9]{9,16}", phone):
            flash("Enter a valid mobile number.", "error")
        elif len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
        elif country not in ("Uganda", "Kenya", "Tanzania", "Rwanda", "Other"):
            flash("Choose a valid country.", "error")
        else:
            with db() as c:
                parent = c.execute("SELECT referral_code FROM users WHERE referral_code=?", (ref,)).fetchone() if ref else None
                code = secrets.token_hex(5).upper()
                try:
                    cur = c.execute(
                        """INSERT INTO users(username,full_name,phone,country,password_hash,referral_code,referred_by,balance_ugx)
                           VALUES(?,?,?,?,?,?,?,?)""",
                        (username, full_name, phone, country, generate_password_hash(password), code,
                         parent["referral_code"] if parent else None, WELCOME_BONUS_UGX)
                    )
                    c.execute("INSERT INTO ledger(user_id,amount_ugx,entry_type,note) VALUES(?,?,?,?)",
                              (cur.lastrowid, WELCOME_BONUS_UGX, "welcome_bonus",
                               "Demo welcome bonus. This is a local prototype credit, not withdrawable cash."))
                    session.clear()
                    session["user_id"] = cur.lastrowid
                    session["show_welcome"] = True
                    flash("HDAR account created successfully.", "success")
                    return redirect(url_for("dashboard"))
                except sqlite3.IntegrityError:
                    flash("That username or mobile number is already registered.", "error")
    return render_template("register.html", ref=ref)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identity = request.form.get("identity", "").strip()
        with db() as c:
            user = c.execute(
                "SELECT * FROM users WHERE username=? COLLATE NOCASE OR phone=?",
                (identity, identity)
            ).fetchone()
        if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))
        flash("Incorrect username/mobile number or password.", "error")
    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    with db() as c:
        directs = c.execute(
            "SELECT username,full_name,created_at FROM users WHERE referred_by=? ORDER BY id DESC",
            (g.user["referral_code"],)
        ).fetchall()
        ledger = c.execute(
            "SELECT amount_ugx,entry_type,note,created_at FROM ledger WHERE user_id=? ORDER BY id DESC LIMIT 10",
            (g.user["id"],)
        ).fetchall()
    invite = request.url_root.rstrip("/") + url_for("register", ref=g.user["referral_code"])
    return render_template("dashboard.html", directs=directs, ledger=ledger, invite=invite)

@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/health")
def health():
    return {"status": "ok"}

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
