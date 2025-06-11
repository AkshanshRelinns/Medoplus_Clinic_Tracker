from flask import Flask, render_template, request, redirect, flash, session, url_for, Response
from pymongo import MongoClient
from datetime import datetime
import os
import csv

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Change this to a strong secret key

# MongoDB setup
client = MongoClient("mongodb+srv://survey:medoplus123@cluster0.agfum2y.mongodb.net/?retryWrites=true&w=majority")
db = client["AppointmentDB"]
collection = db["Appointments"]
users_collection = db["Users"]  # New collection for storing users


admin_user = {
    "username": "Medoplus",
    "password": "clinic123",
    "is_admin": True
}

if not users_collection.find_one({"username": admin_user["username"]}):
    users_collection.insert_one(admin_user)
    print("Admin user inserted.")
else:
    print("Admin user already exists.")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = users_collection.find_one({"username": username})
        if user and user["password"] == password:
            session["username"] = username
            session["is_admin"] = user.get("is_admin", False)
            return redirect(url_for("admin" if user.get("is_admin") else "form"))
        else:
            flash("Invalid username or password")
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("username", None)
    session.pop("is_admin", None)
    return redirect(url_for("login"))

@app.route("/")
def home():
    return redirect(url_for("form"))

@app.route("/form", methods=["GET", "POST"])
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

@app.route("/admin")
def admin():
    if not session.get("is_admin"):
        flash("Unauthorized", "error")
        return redirect(url_for("login"))
    return render_template("admin.html")

@app.route("/create-user", methods=["GET", "POST"])
def create_user():
    if not session.get("is_admin"):
        flash("Unauthorized", "error")
        return redirect(url_for("login"))

    if request.method == "POST":
        new_user = request.form.get("new_user")
        new_pass = request.form.get("new_pass")

        if users_collection.find_one({"username": new_user}):
            flash("User already exists!")
        else:
            users_collection.insert_one({
                "username": new_user,
                "password": new_pass,
                "is_admin": False
            })
            flash("User created successfully!")

        return redirect(url_for("admin"))

    return render_template("create_user.html")

@app.route("/download")
def download():
    if not session.get("is_admin"):
        flash("Unauthorized", "error")
        return redirect(url_for("login"))

    appointments = collection.find()

    def generate():
        data = [["Name", "Gender", "Phone", "Discount", "Coupon Type", "Date", "Entry By", "Timestamp"]]
        for a in appointments:
            data.append([
                a.get("name", ""),
                a.get("gender", ""),
                a.get("phone", ""),
                a.get("discount_coupon", ""),
                a.get("coupon_type", ""),
                a.get("tentative_appointment_date", ""),
                a.get("entry_done_by", ""),
                str(a.get("timestamp", ""))
            ])

        for row in data:
            yield ",".join(row) + "\n"

    return Response(generate(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=appointments.csv"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
