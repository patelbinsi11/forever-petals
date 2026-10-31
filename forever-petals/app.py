import sqlite3
from flask import Flask, render_template, request, redirect, session, g, flash, abort

app = Flask(__name__)
app.secret_key = "change-this-secret-key"
DB = "shop.db"
ADMIN_KEY = "petal123"          # admin URL: /admin?key=petal123
UPI_ID = "yourname@upi"         # tamaro UPI ID
WRAP = {"Plain": 0, "Paper wrap": 40, "Gift box": 120}

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e):
    d = g.pop("db", None)
    if d:
        d.close()

def init_db():
    con = sqlite3.connect(DB)
    con.executescript("""
    CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY, name TEXT, category TEXT,
        price INTEGER, emoji TEXT, description TEXT);
    CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY, name TEXT, phone TEXT, address TEXT,
        payment TEXT, txn TEXT, total INTEGER, items TEXT,
        created TEXT DEFAULT CURRENT_TIMESTAMP);
    """)
    if con.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        con.executemany(
            "INSERT INTO products(name,category,price,emoji,description) VALUES(?,?,?,?,?)",
            [("Rose (1 stem)", "Flower", 59, "🌹", "Handmade pipe cleaner rose"),
             ("Sunflower (1 stem)", "Flower", 79, "🌻", "Bright sunflower"),
             ("Tulip (1 stem)", "Flower", 59, "🌷", "Soft tulip"),
             ("Lily (1 stem)", "Flower", 89, "🪷", "Elegant lily"),
             ("Red Rose Bouquet (12)", "Bouquet", 699, "💐", "12 roses with wrap and ribbon"),
             ("Sunflower Bouquet (6)", "Bouquet", 549, "💐", "6 sunflowers with wrap and ribbon"),
             ("Pastel Mixed Bouquet", "Bouquet", 499, "💐", "Tulip, gerbera and lily in pastel wrap"),
             ("Blue Tulip & Lily Bouquet", "Bouquet", 479, "💐", "Blue tulip, lily and flowers in wrap"),
             ("Grand Pink Bouquet", "Bouquet", 849, "💐", "Large pink tulip and lily bouquet"),
             ("Flower Keychain", "Gift", 99, "🔑", "Cute flower keychain"),
             ("Mini Flower Pot", "Gift", 249, "🪴", "Potted flower with heart design")])
    con.commit()
    con.close()

@app.route("/")
def index():
    cat = request.args.get("cat")
    if cat:
        items = db().execute("SELECT * FROM products WHERE category=?", (cat,)).fetchall()
    else:
        items = db().execute("SELECT * FROM products").fetchall()
    return render_template("index.html", items=items, cat=cat)

def add_item(name, price, qty=1, note=""):
    cart = session.get("cart", [])
    for it in cart:
        if it["name"] == name and it["note"] == note:
            it["qty"] += qty
            break
    else:
        cart.append({"name": name, "price": price, "qty": qty, "note": note})
    session["cart"] = cart

@app.route("/add/<int:pid>")
def add(pid):
    p = db().execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    if not p:
        abort(404)
    add_item(p["name"], p["price"])
    flash(p["name"] + " cart ma add thayu ✅")
    return redirect(request.referrer or "/")

@app.route("/custom", methods=["GET", "POST"])
def custom():
    flowers = db().execute("SELECT * FROM products WHERE category='Flower'").fetchall()
    if request.method == "POST":
        f = db().execute("SELECT * FROM products WHERE id=?", (request.form["flower"],)).fetchone()
        stems = max(1, int(request.form["stems"]))
        wrap = request.form["wrap"]
        color = request.form["color"]
        msg = request.form.get("message", "")
        price = f["price"] * stems + WRAP[wrap]
        note = f"{color}, {wrap}, Msg: {msg}"
        add_item(f"Custom: {f['name']} x{stems}", price, 1, note)
        flash("Custom bouquet cart ma add thayu 💐")
        return redirect("/cart")
    return render_template("custom.html", flowers=flowers, wraps=WRAP)

@app.route("/cart")
def cart():
    items = session.get("cart", [])
    total = sum(i["price"] * i["qty"] for i in items)
    return render_template("cart.html", items=items, total=total)

@app.route("/remove/<int:i>")
def remove(i):
    cart = session.get("cart", [])
    if 0 <= i < len(cart):
        cart.pop(i)
        session["cart"] = cart
    return redirect("/cart")

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    items = session.get("cart", [])
    if not items:
        return redirect("/")
    total = sum(i["price"] * i["qty"] for i in items)
    if request.method == "POST":
        f = request.form
        text = "; ".join(f"{i['name']} x{i['qty']} ({i['note']})" for i in items)
        cur = db().execute(
            "INSERT INTO orders(name,phone,address,payment,txn,total,items) VALUES(?,?,?,?,?,?,?)",
            (f["name"], f["phone"], f["address"], f["payment"], f.get("txn", ""), total, text))
        db().commit()
        session["cart"] = []
        return redirect(f"/success/{cur.lastrowid}")
    return render_template("checkout.html", total=total, upi=UPI_ID)

@app.route("/success/<int:oid>")
def success(oid):
    return render_template("success.html", oid=oid)

@app.route("/admin")
def admin():
    if request.args.get("key") != ADMIN_KEY:
        abort(403)
    orders = db().execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    return render_template("success.html", oid=None, orders=orders)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
