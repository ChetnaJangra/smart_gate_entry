from flask import Flask, render_template, request, redirect, session
import sqlite3
import random
from datetime import datetime

otp_store = {}
app = Flask(__name__)
app.secret_key = "secret123"
from datetime import datetime, timedelta

@app.route("/guard_login", methods=["GET","POST"])
def guard_login():
    if request.method == "POST":
        phone = request.form["phone"]

        otp = str(random.randint(1000,9999))
        otp_store[phone] = otp

        print("OTP:", otp)  # see in terminal

        return render_template("verify_otp.html", phone=phone)

    return render_template("guard_login.html")

@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    phone = request.form["phone"]
    otp = request.form["otp"]

    if otp_store.get(phone) == otp:
        session["guard"] = phone
        return redirect("/guard")
    else:
        return "❌ Invalid OTP"

def delete_old_entries():
    conn = get_db()
    cur = conn.cursor()

    now = datetime.now()
    one_day_ago = now - timedelta(days=1)

    cur.execute("SELECT id, arrival_time FROM cars")
    cars = cur.fetchall()

    for car in cars:
        car_time = datetime.strptime(car[1], "%Y-%m-%d %H:%M:%S")

        if car_time < one_day_ago:
            cur.execute("DELETE FROM cars WHERE id=?", (car[0],))

    conn.commit()
    conn.close()

def get_db():
    return sqlite3.connect("database.db")

# Database
def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        car_id INTEGER,
        action TEXT,
        guard TEXT,
        time TEXT
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT,
        department TEXT
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS cars (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        car_number TEXT,
        arrival_time TEXT,
        status TEXT,
        faculty TEXT
    )''')

    conn.commit()
    conn.close()

init_db()

# Expired logic
def update_expired():
    conn = get_db()
    cur = conn.cursor()

    now = datetime.now().strftime("%H:%M")

    cur.execute("SELECT id, arrival_time FROM cars WHERE status='Pending'")
    cars = cur.fetchall()

    for car in cars:
        if car[1] < now:
            cur.execute("UPDATE cars SET status='Expired' WHERE id=?", (car[0],))

    conn.commit()
    conn.close()

# Home
@app.route("/")
def index():
    return render_template("index.html")

# Faculty choice
@app.route("/faculty")
def faculty():
    return render_template("faculty_choice.html")

# Register
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        department = request.form["department"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username,password,department) VALUES (?,?,?)",
                    (username,password,department))
        conn.commit()
        conn.close()

        return "✅ Registered Successfully"

    return render_template("register.html")

# Login
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=? AND password=?",
                    (username,password))
        user = cur.fetchone()
        conn.close()

        if user:
            session["user"] = username
            return redirect("/dashboard")
        else:
            return "❌ Invalid Login"

    return render_template("login.html")

# Dashboard
@app.route("/dashboard", methods=["GET","POST"])
def dashboard():
    delete_old_entries()
    if "user" not in session:
        return redirect("/login")

    update_expired()

    if request.method == "POST":
        car_number = request.form.get("car_number")
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db()
        cur = conn.cursor()

        # Duplicate check
        cur.execute("SELECT * FROM cars WHERE car_number=? AND arrival_time=?",
                    (car_number,time))
        exists = cur.fetchone()

        if exists:
            return "❌ Car already added!"

        cur.execute("INSERT INTO cars (car_number,arrival_time,status,faculty) VALUES (?,?,?,?)",
                    (car_number,time,"Pending",session["user"]))

        conn.commit()
        conn.close()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""SELECT cars.car_number, cars.arrival_time, cars.status, logs.guard FROM cars LEFT JOIN logs ON cars.id = logs.car_id WHERE cars.faculty=?
""", (session["user"],))

    cars = cur.fetchall()
    conn.close()

    return render_template("dashboard.html", cars=cars)

# Guard panel
@app.route("/guard")
def guard():
    if "guard" not in session:   # 🔐 ADD THIS LINE
        return redirect("/guard_login")

    delete_old_entries()
    update_expired()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM cars")
    cars = cur.fetchall()
    conn.close()

    return render_template("guard.html", cars=cars)

# Update status
@app.route("/update/<int:id>/<status>")
def update(id,status):
    if "guard" not in session:
        return redirect("/guard_login")

    conn = get_db()
    cur = conn.cursor()

    # update car status
    cur.execute("UPDATE cars SET status=? WHERE id=?", (status,id))

    # save log
    cur.execute("INSERT INTO logs (car_id, action, guard, time) VALUES (?,?,?,?)",
                (id, status, session["guard"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()

    return redirect("/guard")

@app.route("/logs")
def logs():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM logs")
    data = cur.fetchall()
    conn.close()

    return render_template("logs.html", logs=data)

# History
@app.route("/history")
def history():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM cars")
    cars = cur.fetchall()
    conn.close()

    return render_template("history.html", cars=cars)

if __name__ == "__main__":
    app.run()