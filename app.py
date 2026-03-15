from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import re
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, date
 
app = Flask(__name__)
CORS(app)
 
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Abhiroot@123",
        database="smartexpense"
    )
 
print("✅ SmartExpense backend ready")
 
def is_valid_email(email):
    return re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email)
 
def is_strong_password(password):
    return re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$", password)
 
def month_label(yr, mo):
    return datetime(int(yr), int(mo), 1).strftime("%b %Y")
 
def month_key(yr, mo):
    return f"{int(yr):04d}-{int(mo):02d}"
 
 
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
    full_name = data["full_name"]; email = data["email"]; password = data["password"]
    if not is_valid_email(email):
        return jsonify({"message": "Invalid email"}), 400
    if not is_strong_password(password):
        return jsonify({"message": "Weak password"}), 400
    db = get_db(); cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("INSERT INTO users (full_name, email, password) VALUES (%s, %s, %s)", (full_name, email, password))
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
    data = request.get_json()
    email = data["email"]; password = data["password"]
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email=%s LIMIT 1", (email,))
    user = cursor.fetchone()
    cursor.close(); db.close()
    if not user or password != user["password"]:
        return jsonify({"message": "Invalid email or password"}), 401
    return jsonify({"message": "Login success", "user": {"id": user["id"], "name": user["full_name"], "email": user["email"]}})
 
@app.get("/profile/<int:user_id>")
def get_profile(user_id):
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT full_name, email, password FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()
    cursor.close(); db.close()
    if not user: return jsonify({"message": "User not found"}), 404
    return jsonify(user)
 
@app.post("/update-profile")
def update_profile():
    data = request.get_json()
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("UPDATE users SET full_name=%s, password=%s WHERE id=%s", (data["name"], data["password"], data["user_id"]))
    db.commit(); cursor.close(); db.close()
    return jsonify({"message": "Profile updated"})
 
 
# ════════════════════════════════════════════════════════
# INCOME
# ════════════════════════════════════════════════════════
 
@app.post("/add-income")
def add_income():
    data = request.get_json()
    db = get_db(); cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("INSERT INTO income (user_id, source, amount, income_date) VALUES (%s, %s, %s, %s)",
                       (data["user_id"], data["source"], data["amount"], data["income_date"]))
        db.commit()
        return jsonify({"message": "Income added", "id": cursor.lastrowid}), 200
    except mysql.connector.Error as err:
        return jsonify({"message": str(err)}), 500
    finally:
        cursor.close(); db.close()
 
@app.get("/get-income/<int:user_id>")
def get_income(user_id):
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM income WHERE user_id=%s ORDER BY income_date DESC", (user_id,))
    rows = cursor.fetchall(); cursor.close(); db.close()
    for r in rows:
        if r.get("income_date"): r["income_date"] = str(r["income_date"])
    return jsonify(rows)
 
@app.delete("/delete-income/<int:income_id>")
def delete_income(income_id):
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("DELETE FROM income WHERE id=%s", (income_id,))
    db.commit(); cursor.close(); db.close()
    return jsonify({"message": "Income deleted"})
 
 
# ════════════════════════════════════════════════════════
# EXPENSES
# ════════════════════════════════════════════════════════
 
@app.post("/add-expense")
def add_expense():
    data = request.get_json()
    db = get_db(); cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("INSERT INTO expenses (user_id, title, category, amount, expense_date) VALUES (%s, %s, %s, %s, %s)",
                       (data["user_id"], data.get("title",""), data["category"], data["amount"], data["expense_date"]))
        db.commit()
        return jsonify({"message": "Expense added", "id": cursor.lastrowid}), 200
    except mysql.connector.Error as err:
        return jsonify({"message": str(err)}), 500
    finally:
        cursor.close(); db.close()
 
@app.get("/get-expenses/<int:user_id>")
def get_expenses(user_id):
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM expenses WHERE user_id=%s ORDER BY expense_date DESC", (user_id,))
    rows = cursor.fetchall(); cursor.close(); db.close()
    for r in rows:
        if r.get("expense_date"): r["expense_date"] = str(r["expense_date"])
        if r.get("created_at"):   r["created_at"]   = str(r["created_at"])
    return jsonify(rows)
 
@app.delete("/delete-expense/<int:expense_id>")
def delete_expense(expense_id):
    db = get_db(); cursor = db.cursor(dictionary=True)
    cursor.execute("DELETE FROM expenses WHERE id=%s", (expense_id,))
    db.commit(); cursor.close(); db.close()
    return jsonify({"message": "Expense deleted"})
 
 
# ════════════════════════════════════════════════════════
# COMPARISON
# ════════════════════════════════════════════════════════
 
@app.post("/save-comparison")
def save_comparison():
    data = request.get_json()
    user_id = data["user_id"]; month = int(data["month"]); year = int(data["year"])
    db = get_db(); cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT COALESCE(SUM(amount),0) AS total FROM income WHERE user_id=%s AND MONTH(income_date)=%s AND YEAR(income_date)=%s", (user_id, month, year))
        total_income = float(cursor.fetchone()["total"])
        cursor.execute("SELECT COALESCE(SUM(amount),0) AS total FROM expenses WHERE user_id=%s AND MONTH(expense_date)=%s AND YEAR(expense_date)=%s", (user_id, month, year))
        total_expense = float(cursor.fetchone()["total"])
        savings = total_income - total_expense
        cursor.execute("""INSERT INTO comparison (user_id, month, year, total_income, total_expense, savings)
               VALUES (%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE total_income=%s, total_expense=%s, savings=%s""",
            (user_id, month, year, total_income, total_expense, savings, total_income, total_expense, savings))
        db.commit()
        return jsonify({"total_income": total_income, "total_expense": total_expense, "savings": savings})
    finally:
        cursor.close(); db.close()
 
 
# ════════════════════════════════════════════════════════
# ⚡ DASHBOARD — granularity-aware (daily or monthly)
# ════════════════════════════════════════════════════════
 
@app.get("/dashboard-data")
def dashboard_data():
    user_id     = request.args.get("user_id", type=int)
    start_date  = request.args.get("start_date")
    end_date    = request.args.get("end_date")
    category    = request.args.get("category", "all")
    granularity = request.args.get("granularity", "monthly")  # "daily" or "monthly"
 
    if not user_id:
        return jsonify({"message": "user_id required"}), 400
 
    today = date.today()
    if not start_date: start_date = today.replace(day=1).strftime("%Y-%m-%d")
    if not end_date:   end_date   = today.strftime("%Y-%m-%d")
 
    db = get_db(); cursor = db.cursor(dictionary=True)
    try:
        # ── Totals ──
        cursor.execute("SELECT COALESCE(SUM(amount),0) AS total FROM income WHERE user_id=%s AND income_date BETWEEN %s AND %s", (user_id, start_date, end_date))
        total_income = float(cursor.fetchone()["total"])
 
        if category != "all":
            cursor.execute("SELECT COALESCE(SUM(amount),0) AS total FROM expenses WHERE user_id=%s AND expense_date BETWEEN %s AND %s AND category=%s", (user_id, start_date, end_date, category))
        else:
            cursor.execute("SELECT COALESCE(SUM(amount),0) AS total FROM expenses WHERE user_id=%s AND expense_date BETWEEN %s AND %s", (user_id, start_date, end_date))
        total_expense = float(cursor.fetchone()["total"])
        balance = total_income - total_expense
 
        # ── Category breakdown ──
        cursor.execute("""SELECT category, COALESCE(SUM(amount),0) AS amount FROM expenses
               WHERE user_id=%s AND expense_date BETWEEN %s AND %s
               GROUP BY category ORDER BY amount DESC""", (user_id, start_date, end_date))
        category_expense = [{"category": r["category"], "amount": float(r["amount"])} for r in cursor.fetchall()]
 
        # ── Trend data: DAILY if granularity=daily, else MONTHLY ──
        # ✅ Build category clause so trend respects the category filter
        if category != "all":
            cat_clause        = "user_id=%s AND expense_date BETWEEN %s AND %s AND category=%s"
            cat_params_base   = (user_id, start_date, end_date, category)
        else:
            cat_clause        = "user_id=%s AND expense_date BETWEEN %s AND %s"
            cat_params_base   = (user_id, start_date, end_date)
 
        if granularity == "daily":
            cursor.execute(f"""SELECT expense_date AS day_key, COALESCE(SUM(amount),0) AS amount
                   FROM expenses WHERE {cat_clause}
                   GROUP BY expense_date ORDER BY expense_date""", cat_params_base)
            monthly_expense = []
            for r in cursor.fetchall():
                d = r["day_key"]
                label = (d.strftime("%d %b") if hasattr(d, 'strftime') else datetime.strptime(str(d), "%Y-%m-%d").strftime("%d %b"))
                monthly_expense.append({"month": label, "amount": float(r["amount"])})
 
            # Daily income vs expense
            cursor.execute("""SELECT income_date AS day_key, COALESCE(SUM(amount),0) AS income
                   FROM income WHERE user_id=%s AND income_date BETWEEN %s AND %s
                   GROUP BY income_date ORDER BY income_date""", (user_id, start_date, end_date))
            ive = {}
            for r in cursor.fetchall():
                d = r["day_key"]
                label = (d.strftime("%d %b") if hasattr(d, 'strftime') else datetime.strptime(str(d), "%Y-%m-%d").strftime("%d %b"))
                key   = str(d)
                ive[key] = {"month": label, "income": float(r["income"]), "expense": 0.0}
 
            cursor.execute("""SELECT expense_date AS day_key, COALESCE(SUM(amount),0) AS expense
                   FROM expenses WHERE user_id=%s AND expense_date BETWEEN %s AND %s
                   GROUP BY expense_date ORDER BY expense_date""", (user_id, start_date, end_date))
            for r in cursor.fetchall():
                d   = r["day_key"]
                key = str(d)
                label = (d.strftime("%d %b") if hasattr(d, 'strftime') else datetime.strptime(str(d), "%Y-%m-%d").strftime("%d %b"))
                if key in ive:
                    ive[key]["expense"] = float(r["expense"])
                else:
                    ive[key] = {"month": label, "income": 0.0, "expense": float(r["expense"])}
 
        else:
            # Monthly expense trend (respects category filter)
            cursor.execute(f"""SELECT YEAR(expense_date) AS yr, MONTH(expense_date) AS mo, COALESCE(SUM(amount),0) AS amount
                   FROM expenses WHERE {cat_clause}
                   GROUP BY YEAR(expense_date), MONTH(expense_date) ORDER BY yr, mo""", cat_params_base)
            monthly_expense = [{"month": month_label(r["yr"], r["mo"]), "amount": float(r["amount"])} for r in cursor.fetchall()]
 
            cursor.execute("""SELECT YEAR(income_date) AS yr, MONTH(income_date) AS mo, COALESCE(SUM(amount),0) AS income
                   FROM income WHERE user_id=%s AND income_date BETWEEN %s AND %s
                   GROUP BY YEAR(income_date), MONTH(income_date) ORDER BY yr, mo""", (user_id, start_date, end_date))
            ive = {}
            for r in cursor.fetchall():
                k = month_key(r["yr"], r["mo"])
                ive[k] = {"month": month_label(r["yr"], r["mo"]), "income": float(r["income"]), "expense": 0.0}
 
            cursor.execute("""SELECT YEAR(expense_date) AS yr, MONTH(expense_date) AS mo, COALESCE(SUM(amount),0) AS expense
                   FROM expenses WHERE user_id=%s AND expense_date BETWEEN %s AND %s
                   GROUP BY YEAR(expense_date), MONTH(expense_date) ORDER BY yr, mo""", (user_id, start_date, end_date))
            for r in cursor.fetchall():
                k = month_key(r["yr"], r["mo"])
                if k in ive:
                    ive[k]["expense"] = float(r["expense"])
                else:
                    ive[k] = {"month": month_label(r["yr"], r["mo"]), "income": 0.0, "expense": float(r["expense"])}
 
        income_vs_expense = [ive[k] for k in sorted(ive.keys())]
 
        # ── Income by source (for when user filters by Income only) ──
        cursor.execute("""SELECT source, COALESCE(SUM(amount),0) AS amount
               FROM income WHERE user_id=%s AND income_date BETWEEN %s AND %s
               GROUP BY source ORDER BY amount DESC""", (user_id, start_date, end_date))
        income_by_source = [{"category": r["source"], "amount": float(r["amount"])} for r in cursor.fetchall()]
 
        # ── Top 5 categories ──
        cursor.execute("""SELECT category, COALESCE(SUM(amount),0) AS amount FROM expenses
               WHERE user_id=%s AND expense_date BETWEEN %s AND %s
               GROUP BY category ORDER BY amount DESC LIMIT 5""", (user_id, start_date, end_date))
        top_categories = [{"category": r["category"], "amount": float(r["amount"])} for r in cursor.fetchall()]
 
        # ── Recent transactions ──
        cursor.execute("""SELECT 'income' AS type, source AS title, source AS category, amount, income_date AS tx_date
               FROM income WHERE user_id=%s AND income_date BETWEEN %s AND %s ORDER BY income_date DESC LIMIT 5""", (user_id, start_date, end_date))
        recent = [{"type":"income","title":r["title"],"category":r["category"],"amount":float(r["amount"]),"tx_date":str(r["tx_date"])} for r in cursor.fetchall()]
 
        cursor.execute("""SELECT 'expense' AS type, COALESCE(title,'') AS title, category, amount, expense_date AS tx_date
               FROM expenses WHERE user_id=%s AND expense_date BETWEEN %s AND %s ORDER BY expense_date DESC LIMIT 5""", (user_id, start_date, end_date))
        for r in cursor.fetchall():
            recent.append({"type":"expense","title":r["title"],"category":r["category"],"amount":float(r["amount"]),"tx_date":str(r["tx_date"])})
 
        recent.sort(key=lambda x: x["tx_date"], reverse=True)
        recent = recent[:10]
 
        return jsonify({
            "balance": balance, "total_income": total_income, "total_expense": total_expense,
            "category_expense": category_expense, "income_by_source": income_by_source,
            "monthly_expense": monthly_expense,
            "income_vs_expense": income_vs_expense, "top_categories": top_categories,
            "recent": recent, "granularity": granularity
        })
 
    except Exception as e:
        print("Dashboard error:", e)
        return jsonify({"message": str(e)}), 500
    finally:
        cursor.close(); db.close()
 
 
# ════════════════════════════════════════════════════════
# FEEDBACK
# ════════════════════════════════════════════════════════
 
@app.post("/send-feedback")
def send_feedback():
    data = request.get_json()
    email_body = f"SmartExpense Feedback\n\nCategory: {data['category']}\nRating: {data['rating']} stars\n\nMessage:\n{data['message']}"
    try:
        msg = MIMEText(email_body)
        msg["Subject"] = "New SmartExpense Feedback"
        msg["From"] = "smartexpense10@gmail.com"
        msg["To"]   = "smartexpense10@gmail.com"
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
