from flask import Flask, render_template, request, redirect, flash, session, url_for, Response
from pymongo import MongoClient
from datetime import datetime, timedelta
import os

app = Flask(Medoplus)
app.secret_key = "your_secret_key"

# MongoDB setup
client = MongoClient("mongodb+srv://survey:medoplus123@cluster0.agfum2y.mongodb.net/")
db = client["AppointmentDB"]
collection = db["Appointments"]
users_collection = db["Users"]  # Collection for storing users

# Auto-create default admin user if not exists
def initialize_admin():
    try:
        if not users_collection.find_one({"username": "Medoplus"}):
            users_collection.insert_one({
                "username": "Medoplus",
                "password": "clinic123",
                "is_admin": True
            })
        print(" Admin user checked/created")
    except Exception as e:
        print(" Failed to initialize admin:", e)

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
            if session.get("lang") == "hi":
                flash("अमान्य उपयोगकर्ता नाम या पासवर्ड।", "error")
            else:
                flash("Invalid username or password.", "error")
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("username", None)
    session.pop("is_admin", None)
    return redirect(url_for("login"))

@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/form", methods=["GET", "POST"])
def form():
    if "username" not in session:
        return redirect(url_for("login"))
    
    if "lang" not in session:
        session["lang"] = "en"

    # Fetch user record from MongoDB
    user = users_collection.find_one({"username": session["username"]})
    entry_by_phone = user.get("phone", "Unknown") 

    if request.method == "POST":
        data = {
            "name": request.form.get("name"),
            "gender": request.form.get("gender"),
            "phone": request.form.get("phone"),
            "discount_coupon": request.form.get("discount_coupon"),
            "coupon_type": request.form.get("coupon_type"),
            "coupon_issue_date": request.form.get("coupon_issue_date"),
            "discount_amount_type": request.form.get("discount_amount_type"),
            "discount_amount_value": request.form.get("discount_amount_value"),
            "tentative_appointment_date": request.form.get("tentative_appointment_date"),
            "entry_done_by": entry_by_phone, 
            "timestamp": datetime.now()
        }

        # Validate required fields
        if not all([data["name"], data["gender"], data["phone"], data["tentative_appointment_date"]]):
            flash("Please fill all required fields.", "error")
            return render_template("form.html", **request.form)
        else:
            collection.insert_one(data)
            if session.get("lang") == "hi":
                flash("अपॉइंटमेंट सफलतापूर्वक सहेजा गया!", "success")
            else:
                flash("Appointment saved successfully!", "success")
            return redirect(url_for("form"))

    return render_template("form.html",
                            name=request.form.get("name", ""),
                            gender=request.form.get("gender", ""),
                            phone=request.form.get("phone", ""),
                            discount_coupon=request.form.get("discount_coupon", ""),
                            coupon_type=request.form.get("coupon_type", ""),
                            coupon_issue_date=request.form.get("coupon_issue_date", ""),
                            discount_amount_type=request.form.get("discount_amount_type", ""),
                            discount_amount_value=request.form.get("discount_amount_value", ""),
                            date=request.form.get("date", "")
)


@app.route("/admin")
def admin():
    if not session.get("is_admin"):
        flash("Unauthorized", "error")
        return redirect(url_for("login"))

    appointments = collection.find().sort("timestamp", -1).limit(10)  # Show 10 most recent appointments
    return render_template("admin.html", appointments=appointments)


@app.route("/create-user", methods=["GET", "POST"])
def create_user():
    if not session.get("is_admin"):
        flash("Unauthorized", "error")
        return redirect(url_for("login"))

    if request.method == "POST":
        new_user = request.form.get("new_user")
        new_pass = request.form.get("new_pass")
        full_name = request.form.get("full_name")
        phone = request.form.get("phone")
        location = request.form.get("location")

        if users_collection.find_one({"username": new_user}):
            flash("User already exists!")
        else:
            users_collection.insert_one({
                "username": new_user,
                "password": new_pass,
                "is_admin": False,
                "full_name": full_name,
                "phone": phone,
                "location": location
            })
            flash("User created successfully!", "success")

        return redirect(url_for("admin"))

    return render_template("create_user.html")

@app.route("/set-language/<lang>")
def set_language(lang):
    if lang in ["en", "hi"]:
        session["lang"] = lang
    return redirect(request.referrer or url_for("form"))


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if not session.get("is_admin"):
        flash("Unauthorized", "error")
        return redirect(url_for("login"))

    users = users_collection.find({}, {"username": 1, "_id": 0})
    usernames = [u["username"] for u in users]

    if request.method == "POST":
        selected_user = request.form.get("username")
        new_pass = request.form.get("new_password")

        result = users_collection.update_one(
            {"username": selected_user},
            {"$set": {"password": new_pass}}
        )

        if result.modified_count:
            flash(f"Password for '{selected_user}' has been reset.", "success")
        else:
            flash("Failed to reset password.", "warning")

        return redirect(url_for("admin"))

    return render_template("reset_password.html", usernames=usernames)



@app.route("/download")
def download():
    if not session.get("is_admin"):
        flash("Unauthorized", "error")
        return redirect(url_for("login"))

    # Read filter parameters
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    filter_flag = request.args.get("filter") == "yes"

    query = {}
    if filter_flag and start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
            query["timestamp"] = {"$gte": start_dt, "$lte": end_dt}
        except Exception as e:
            return f"Date parsing error: {str(e)}"

    appointments = collection.find(query)

    def generate():
        data = [["Name", "Gender", "Phone", "Discount", "Coupon Type", "Coupon Issue Date", "Discount Amount Type", "Discount Amount Value", "Tentative Appointment Date", "Entry By", "Timestamp"]]
        for a in appointments:
            data.append([
                a.get("name", ""),
                a.get("gender", ""),
                a.get("phone", ""),
                a.get("discount_coupon", ""),
                a.get("coupon_type", ""),
                a.get("coupon_issue_date", ""),
                a.get("discount_amount_type", ""),
                a.get("discount_amount_value", ""),
                a.get("tentative_appointment_date", ""),
                a.get("entry_done_by", ""),
                str(a.get("timestamp", ""))
            ])
        for row in data:
            yield ",".join(map(str, row)) + "\n"

    return Response(generate(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=appointments.csv"})


@app.route("/download-users")
def download_users():
    if not session.get("is_admin"):
        flash("Unauthorized", "error")
        return redirect(url_for("login"))

    users = users_collection.find()

    def generate():
        # CSV header
        data = [["Username", "Password", "Full Name", "Phone", "Location", "Is Admin"]]
        for u in users:
            data.append([
                u.get("username", ""),
                u.get("password", ""),
                u.get("full_name", ""),
                u.get("phone", ""),
                u.get("location", ""),
                str(u.get("is_admin", False))
            ])
        for row in data:
            yield ",".join(map(str, row)) + "\n"

    return Response(generate(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=users.csv"})


if __name__ == "__main__":
    initialize_admin()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
