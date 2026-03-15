from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import re
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
CORS(app)

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Abhiroot@123",
    database="smartexpense"
)

cursor = db.cursor(dictionary=True)

print("✅ Connected to MySQL")


def is_valid_email(email):
    pattern = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    return re.match(pattern, email)


def is_strong_password(password):
    pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$"
    return re.match(pattern, password)


@app.get("/")
def home():
    return "SmartExpense backend running"


# ===============================
# CHECK EMAIL
# ===============================
@app.get("/check-email")
def check_email():

    email = request.args.get("email")

    cursor.execute(
        "SELECT id FROM users WHERE email=%s LIMIT 1",
        (email,)
    )

    user = cursor.fetchone()

    return jsonify({
        "exists": bool(user)
    })


# ===============================
# REGISTER
# ===============================
@app.post("/register")
def register():

    data = request.get_json()

    full_name = data["full_name"]
    email = data["email"]
    password = data["password"]

    if not is_valid_email(email):
        return jsonify({"message": "Invalid email"}), 400

    if not is_strong_password(password):
        return jsonify({"message": "Weak password"}), 400

    try:

        cursor.execute(
            "INSERT INTO users (full_name,email,password) VALUES (%s,%s,%s)",
            (full_name,email,password)
        )

        db.commit()

        return jsonify({"message":"User registered"}),200

    except mysql.connector.Error as err:

        if err.errno == 1062:
            return jsonify({"message":"Email already exists"}),400

        return jsonify({"message":"Database error"}),500


# ===============================
# LOGIN
# ===============================
@app.post("/login")
def login():

    data = request.get_json()

    email = data["email"]
    password = data["password"]

    cursor.execute(
        "SELECT * FROM users WHERE email=%s LIMIT 1",
        (email,)
    )

    user = cursor.fetchone()

    if not user or password != user["password"]:
        return jsonify({"message":"Invalid email or password"}),401

    return jsonify({
        "message":"Login success",
        "user":{
            "id":user["id"],
            "name":user["full_name"],
            "email":user["email"]
        }
    })


# ===============================
# GET PROFILE
# ===============================
@app.get("/profile/<int:user_id>")
def get_profile(user_id):

    cursor.execute(
        "SELECT full_name,email,password FROM users WHERE id=%s",
        (user_id,)
    )

    user = cursor.fetchone()

    if not user:
        return jsonify({"message":"User not found"}),404

    return jsonify(user)


# ===============================
# UPDATE PROFILE
# ===============================
@app.post("/update-profile")
def update_profile():

    data = request.get_json()

    user_id = data["user_id"]
    name = data["name"]
    password = data["password"]

    cursor.execute(
        "UPDATE users SET full_name=%s,password=%s WHERE id=%s",
        (name,password,user_id)
    )

    db.commit()

    return jsonify({"message":"Profile updated"})


# ===============================
# SEND FEEDBACK EMAIL
# ===============================
@app.post("/send-feedback")
def send_feedback():

    data = request.get_json()

    category = data["category"]
    rating = data["rating"]
    message = data["message"]

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
        msg["From"] = "smartexpense10@gmail.com"
        msg["To"] = "smartexpense10@gmail.com"

        server = smtplib.SMTP("smtp.gmail.com",587)
        server.starttls()

        # IMPORTANT → Use Gmail App Password
        server.login("smartexpense10@gmail.com","xjlh jbmd jvkm gbxc")

        server.send_message(msg)

        server.quit()

        return jsonify({"message":"Feedback sent successfully"}),200

    except Exception as e:
        print(e)
        return jsonify({"message":"Failed to send feedback"}),500


if __name__ == "__main__":
    app.run(port=5000,debug=True)