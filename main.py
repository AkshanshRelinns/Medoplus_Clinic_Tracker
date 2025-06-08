from flask import Flask, render_template, request, redirect, flash, session, url_for
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key"  # required for session

# MongoDB setup
client = MongoClient("mongodb+srv://survey:<medoplus123>@cluster0.agfum2y.mongodb.net/")
db = client["AppointmentDB"]
collection = db["Appointments"]

# Hardcoded user (you can later store in DB)
USER_CREDENTIALS = {
    "Medoplus": "clinic123"  # Change this!
}

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if USER_CREDENTIALS.get(username) == password:
            session["username"] = username
            return redirect(url_for("form"))
        else:
            flash("Invalid username or password")
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

@app.route("/", methods=["GET", "POST"])
def form():
    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        data = {
            "name": request.form.get("name"),
            "gender": request.form.get("gender"),
            "phone": request.form.get("phone"),
            "discount_coupon": request.form.get("discount_coupon"),
            "coupon_type": request.form.get("coupon_type"),
            "tentative_appointment_date": request.form.get("date"),
            "entry_done_by": request.form.get("entry_by"),
            "timestamp": datetime.now()
        }

        if not all([data["name"], data["gender"], data["phone"], data["tentative_appointment_date"], data["entry_done_by"]]):
            flash("Please fill all required fields.", "error")
        else:
            collection.insert_one(data)
            flash("Appointment saved successfully!", "success")

        return redirect(url_for("form"))

    return render_template("form.html")

# ... rest of your Flask code ...

if __name__ == "__main__":
    app.run(debug=True)

