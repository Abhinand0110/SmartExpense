from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import re
import smtplib
from email.mime.text import MIMEText
 
app = Flask(__name__)
CORS(app)
 
# ✅ Function instead of global connection — fresh connection every request
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Abhiroot@123",
        database="smartexpense"
    )
 
print("✅ SmartExpense backend ready")
 
 
# ── helpers ──────────────────────────────────────────────
def is_valid_email(email):
    return re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email)
 
def is_strong_password(password):
    return re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$", password)
 
 
# ── ROOT ─────────────────────────────────────────────────
@app.get("/")
def home():
    return "SmartExpense backend running"
 
 
# ════════════════════════════════════════════════════════
# AUTH
# ════════════════════════════════════════════════════════
 
@app.get("/check-email")
def check_email():
    email = request.args.get("email")
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id FROM users WHERE email=%s LIMIT 1", (email,))
    user = cursor.fetchone()
    cursor.close(); db.close()
    return jsonify({"exists": bool(user)})
 
 
@app.post("/register")
def register():
    data = request.get_json()
    full_name = data["full_name"]
    email     = data["email"]
    password  = data["password"]
 
    if not is_valid_email(email):
        return jsonify({"message": "Invalid email"}), 400
    if not is_strong_password(password):
        return jsonify({"message": "Weak password"}), 400
 
    db = get_db(); cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            "INSERT INTO users (full_name, email, password) VALUES (%s, %s, %s)",
            (full_name, email, password)
        )
        db.commit()
        return jsonify({"message": "User registered"}), 200
    except mysql.connector.Error as err:
        if err.errno == 1062:
            return jsonify({"message": "Email already exists"}), 400
        return jsonify({"message": "Database error"}), 500
    finally:
        cursor.close(); db.close()
 
 
@app.post("/login")
def login():
    data     = request.get_json()
    email    = data["email"]
    password = data["password"]
 
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email=%s LIMIT 1", (email,))
    user = cursor.fetchone()
    cursor.close(); db.close()
 
    if not user or password != user["password"]:
        return jsonify({"message": "Invalid email or password"}), 401
 
    return jsonify({
        "message": "Login success",
        "user": {
            "id":    user["id"],
            "name":  user["full_name"],
            "email": user["email"]
        }
    })
 
 
@app.get("/profile/<int:user_id>")
def get_profile(user_id):
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT full_name, email, password FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()
    cursor.close(); db.close()
    if not user:
        return jsonify({"message": "User not found"}), 404
    return jsonify(user)
 
 
@app.post("/update-profile")
def update_profile():
    data = request.get_json()
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute(
        "UPDATE users SET full_name=%s, password=%s WHERE id=%s",
        (data["name"], data["password"], data["user_id"])
    )
    db.commit()
    cursor.close(); db.close()
    return jsonify({"message": "Profile updated"})
 
 
# ════════════════════════════════════════════════════════
# INCOME
# ════════════════════════════════════════════════════════
 
@app.post("/add-income")
def add_income():
    data    = request.get_json()
    user_id = data["user_id"]
    source  = data["source"]
    amount  = data["amount"]
    date    = data["income_date"]
 
    db = get_db(); cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            "INSERT INTO income (user_id, source, amount, income_date) VALUES (%s, %s, %s, %s)",
            (user_id, source, amount, date)
        )
        db.commit()
        return jsonify({"message": "Income added", "id": cursor.lastrowid}), 200
    except mysql.connector.Error as err:
        return jsonify({"message": str(err)}), 500
    finally:
        cursor.close(); db.close()
 
 
@app.get("/get-income/<int:user_id>")
def get_income(user_id):
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM income WHERE user_id=%s ORDER BY income_date DESC",
        (user_id,)
    )
    rows = cursor.fetchall()
    cursor.close(); db.close()
    for r in rows:
        if r.get("income_date"):
            r["income_date"] = str(r["income_date"])
    return jsonify(rows)
 
 
@app.delete("/delete-income/<int:income_id>")
def delete_income(income_id):
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("DELETE FROM income WHERE id=%s", (income_id,))
    db.commit()
    cursor.close(); db.close()
    return jsonify({"message": "Income deleted"})
 
 
# ════════════════════════════════════════════════════════
# EXPENSES
# ════════════════════════════════════════════════════════
 
@app.post("/add-expense")
def add_expense():
    data     = request.get_json()
    user_id  = data["user_id"]
    title    = data.get("title", "")
    category = data["category"]
    amount   = data["amount"]
    date     = data["expense_date"]
 
    db = get_db(); cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            "INSERT INTO expenses (user_id, title, category, amount, expense_date) VALUES (%s, %s, %s, %s, %s)",
            (user_id, title, category, amount, date)
        )
        db.commit()
        return jsonify({"message": "Expense added", "id": cursor.lastrowid}), 200
    except mysql.connector.Error as err:
        return jsonify({"message": str(err)}), 500
    finally:
        cursor.close(); db.close()
 
 
@app.get("/get-expenses/<int:user_id>")
def get_expenses(user_id):
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM expenses WHERE user_id=%s ORDER BY expense_date DESC",
        (user_id,)
    )
    rows = cursor.fetchall()
    cursor.close(); db.close()
    for r in rows:
        if r.get("expense_date"):
            r["expense_date"] = str(r["expense_date"])
        if r.get("created_at"):
            r["created_at"] = str(r["created_at"])
    return jsonify(rows)
 
 
@app.delete("/delete-expense/<int:expense_id>")
def delete_expense(expense_id):
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("DELETE FROM expenses WHERE id=%s", (expense_id,))
    db.commit()
    cursor.close(); db.close()
    return jsonify({"message": "Expense deleted"})
 
 
# ════════════════════════════════════════════════════════
# COMPARISON
# ════════════════════════════════════════════════════════
 
@app.post("/save-comparison")
def save_comparison():
    data    = request.get_json()
    user_id = data["user_id"]
    month   = int(data["month"])
    year    = int(data["year"])
 
    db = get_db(); cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT COALESCE(SUM(amount), 0) AS total FROM income
               WHERE user_id=%s AND MONTH(income_date)=%s AND YEAR(income_date)=%s""",
            (user_id, month, year)
        )
        total_income = float(cursor.fetchone()["total"])
 
        cursor.execute(
            """SELECT COALESCE(SUM(amount), 0) AS total FROM expenses
               WHERE user_id=%s AND MONTH(expense_date)=%s AND YEAR(expense_date)=%s""",
            (user_id, month, year)
        )
        total_expense = float(cursor.fetchone()["total"])
        savings = total_income - total_expense
 
        cursor.execute(
            """INSERT INTO comparison (user_id, month, year, total_income, total_expense, savings)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
               total_income=%s, total_expense=%s, savings=%s""",
            (user_id, month, year, total_income, total_expense, savings,
             total_income, total_expense, savings)
        )
        db.commit()
        return jsonify({
            "total_income":  total_income,
            "total_expense": total_expense,
            "savings":       savings
        })
    finally:
        cursor.close(); db.close()
 
 
@app.get("/get-comparison/<int:user_id>")
def get_comparison(user_id):
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM comparison WHERE user_id=%s ORDER BY year, month",
        (user_id,)
    )
    rows = cursor.fetchall()
    cursor.close(); db.close()
    return jsonify(rows)
 
 
# ════════════════════════════════════════════════════════
# FEEDBACK
# ════════════════════════════════════════════════════════
 
@app.post("/send-feedback")
def send_feedback():
    data     = request.get_json()
    category = data["category"]
    rating   = data["rating"]
    message  = data["message"]
 
    email_body = f"""
SmartExpense Feedback
 
Category: {category}
Rating: {rating} stars
 
Message:
{message}
"""
    try:
        msg = MIMEText(email_body)
        msg["Subject"] = "New SmartExpense Feedback"
        msg["From"]    = "smartexpense10@gmail.com"
        msg["To"]      = "smartexpense10@gmail.com"
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login("smartexpense10@gmail.com", "xjlh jbmd jvkm gbxc")
        server.send_message(msg)
        server.quit()
        return jsonify({"message": "Feedback sent successfully"}), 200
    except Exception as e:
        print(e)
        return jsonify({"message": "Failed to send feedback"}), 500
 
 
if __name__ == "__main__":
    app.run(port=5000, debug=True)
