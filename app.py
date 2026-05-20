from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from datetime import datetime
import pandas as pd
import os

# =========================
# LOAD ENV
# =========================

load_dotenv()

# =========================
# APP CONFIG
# =========================

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "secret123")

# SUPABASE POSTGRESQL DATABASE
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# =========================
# MODELS
# =========================

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(200),
        nullable=False
    )

    mobile = db.Column(
        db.String(20)
    )

    address = db.Column(
        db.Text
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


class TiffinEntry(db.Model):
    __tablename__ = "tiffin_entries"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    tiffin_date = db.Column(
        db.Date,
        nullable=False
    )

    day_tiffin = db.Column(
        db.Boolean,
        default=False
    )

    night_tiffin = db.Column(
        db.Boolean,
        default=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    user = db.relationship("User")


# =========================
# CREATE TABLES
# =========================

with app.app_context():
    db.create_all()

# =========================
# DASHBOARD
# =========================

@app.route("/")
def dashboard():

    total_users = User.query.count()

    total_day = TiffinEntry.query.filter_by(
        day_tiffin=True
    ).count()

    total_night = TiffinEntry.query.filter_by(
        night_tiffin=True
    ).count()

    recent_entries = TiffinEntry.query.order_by(
        TiffinEntry.tiffin_date.desc()
    ).limit(10).all()

    return render_template(
        "dashboard.html",
        total_users=total_users,
        total_day=total_day,
        total_night=total_night,
        recent_entries=recent_entries
    )


# =========================
# USERS
# =========================

@app.route("/users", methods=["GET", "POST"])
def users():

    if request.method == "POST":

        name = request.form.get("name")
        mobile = request.form.get("mobile")
        address = request.form.get("address")

        user = User(
            name=name,
            mobile=mobile,
            address=address
        )

        db.session.add(user)
        db.session.commit()

        flash(
            "User added successfully",
            "success"
        )

        return redirect(url_for("users"))

    all_users = User.query.order_by(
        User.id.desc()
    ).all()

    return render_template(
        "users.html",
        users=all_users
    )


# =========================
# TIFFIN ENTRIES
# =========================

@app.route("/entries", methods=["GET", "POST"])
def entries():

    users = User.query.all()

    if request.method == "POST":

        user_id = request.form.get("user_id")

        tiffin_date = request.form.get(
            "tiffin_date"
        )

        day_tiffin = True if request.form.get(
            "day_tiffin"
        ) else False

        night_tiffin = True if request.form.get(
            "night_tiffin"
        ) else False

        existing = TiffinEntry.query.filter_by(
            user_id=user_id,
            tiffin_date=tiffin_date
        ).first()

        if existing:

            existing.day_tiffin = day_tiffin
            existing.night_tiffin = night_tiffin

            flash(
                "Entry updated successfully",
                "success"
            )

        else:

            entry = TiffinEntry(
                user_id=user_id,

                tiffin_date=datetime.strptime(
                    tiffin_date,
                    "%Y-%m-%d"
                ).date(),

                day_tiffin=day_tiffin,

                night_tiffin=night_tiffin
            )

            db.session.add(entry)

            flash(
                "Entry added successfully",
                "success"
            )

        db.session.commit()

        return redirect(url_for("entries"))

    all_entries = TiffinEntry.query.order_by(
        TiffinEntry.tiffin_date.desc()
    ).all()

    return render_template(
        "entries.html",
        users=users,
        entries=all_entries
    )


# =========================
# REPORTS
# =========================

@app.route("/reports")
def reports():

    start_date = request.args.get(
        "start_date"
    )

    end_date = request.args.get(
        "end_date"
    )

    query = TiffinEntry.query

    if start_date and end_date:

        query = query.filter(
            TiffinEntry.tiffin_date.between(
                start_date,
                end_date
            )
        )

    entries = query.order_by(
        TiffinEntry.tiffin_date.desc()
    ).all()

    total_day = sum(
        1 for x in entries if x.day_tiffin
    )

    total_night = sum(
        1 for x in entries if x.night_tiffin
    )

    return render_template(
        "reports.html",
        entries=entries,
        total_day=total_day,
        total_night=total_night
    )


# =========================
# DOWNLOAD EXCEL REPORT
# =========================

@app.route("/download-report")
def download_report():

    start_date = request.args.get(
        "start_date"
    )

    end_date = request.args.get(
        "end_date"
    )

    query = TiffinEntry.query

    if start_date and end_date:

        query = query.filter(
            TiffinEntry.tiffin_date.between(
                start_date,
                end_date
            )
        )

    entries = query.order_by(
        TiffinEntry.tiffin_date.desc()
    ).all()

    data = []

    total_day = 0
    total_night = 0

    for item in entries:

        if item.day_tiffin:
            total_day += 1

        if item.night_tiffin:
            total_night += 1

        data.append({
            "Name": item.user.name,

            "Date": item.tiffin_date.strftime(
                "%d-%m-%Y"
            ),

            "Day Tiffin": (
                "Yes"
                if item.day_tiffin
                else "No"
            ),

            "Night Tiffin": (
                "Yes"
                if item.night_tiffin
                else "No"
            )
        })

    # TOTAL ROW
    data.append({
        "Name": "TOTAL",
        "Date": "",
        "Day Tiffin": total_day,
        "Night Tiffin": total_night
    })

    df = pd.DataFrame(data)

    file_name = "tiffin_report.xlsx"

    df.to_excel(
        file_name,
        index=False
    )

    return send_file(
        file_name,
        as_attachment=True
    )


# =========================
# RUN APP
# =========================

if __name__ == "__main__":
    app.run(debug=True)