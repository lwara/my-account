import os
from flask import Flask, render_template, request, redirect, url_for, flash, session

from db import create_user, verify_password
from db import (
    save_profile,
    get_profile,
    create_fitting,
    list_fittings,
    get_fitting,
    update_fitting_status,
)
from functools import wraps
from datetime import datetime


def create_app():
     # Initialize Flask app
    app = Flask(__name__)
    # Set secret key for session management
    app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret-key-change-me")

    # now the routes start from here 
    @app.route("/")
    def home():
        # Get current user from session
        user = session.get("username")
        return render_template("home.html", user=user)

    # Registration route
    @app.route("/register", methods=["GET", "POST"])
    def register():
        # Handle form submission
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            if not username or not password:
                flash("Username and password are required.")
                return redirect(url_for("register"))
            ok = create_user(username, password)
            if ok:
                flash("Account created. Please log in.")
                return redirect(url_for("login"))
            else:
                flash("User already exists.")
                return redirect(url_for("register"))
        return render_template("register.html")

    #` Login route`
    @app.route("/login", methods=["GET", "POST"])
    def login():
        # Handle form submission
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            if verify_password(username, password):
                session["username"] = username
                flash("Logged in successfully.")
                # once the user is logged in, redirect to dashboard home
                return redirect(url_for("dashboard_root")) # got to dashboard root function 
            else:
                flash("Invalid username or password.")
                return redirect(url_for("login"))
        return render_template("login.html")
    # Logout route
    @app.route("/logout")
    def logout():
        session.pop("username", None)
        flash("Logged out.")
        return redirect(url_for("home"))


    def login_required(f):
        # Decorator to require login for certain routes
        @wraps(f)
        def wrapped(*a, **kw): # wrap the function
            if not session.get("username"):
                flash("Please log in to access that page.")
                return redirect(url_for("login"))
            return f(*a, **kw)
        return wrapped


    # Dashboard routes (displayed when signed in)
    @app.route("/dashboard")
    @login_required
    def dashboard_root():
        # default to Getting Started
        return redirect(url_for("dashboard_view", section="getting-started"))


    @app.route("/dashboard/<section>")
    @login_required
    def dashboard_view(section):
        # allowed sections
        allowed = {
            "getting-started": "dashboard/getting_started.html",
            "schedule-swing": "dashboard/schedule_swing.html",
            "schedule-fitting": "dashboard/schedule_fitting.html",
            "fitting-progress": "dashboard/fitting_progress.html",
            "account-history": "dashboard/account_history.html",
            "profile": "dashboard/profile.html",
             
        }
        if section not in allowed:
            flash("Unknown section")
            return redirect(url_for("dashboard_view", section="getting-started"))

        username = session.get("username")
        profile = get_profile(username)

        # Some sections need additional data
        data = {}
        if section in ("fitting-progress", "account-history"):
            data["fittings"] = list_fittings(username)

        return render_template("dashboard.html", content_template=allowed[section], active=section, profile=profile, **data)


    # Schedule handlers: handle POST submissions from schedule forms
    @app.route("/dashboard/schedule-swing", methods=["POST"])
    @login_required
    def schedule_swing_post():
        username = session.get("username")
        date = request.form.get("date")
        time = request.form.get("time")
        comments = request.form.get("comments")
        if not date or not time:
            flash("Please provide date and time.")
            return redirect(url_for("dashboard_view", section="schedule-swing"))
        # combine to ISO
        scheduled_at = f"{date}T{time}"
        fid = create_fitting(username, "swing", scheduled_at, comments)
        if fid:
            flash("Swing analysis scheduled.")
            return redirect(url_for("dashboard_view", section="fitting-progress"))
        else:
            flash("Could not schedule.")
            return redirect(url_for("dashboard_view", section="schedule-swing"))


    @app.route("/dashboard/schedule-fitting", methods=["POST"])
    @login_required
    def schedule_fitting_post():
        username = session.get("username")
        date = request.form.get("date")
        time = request.form.get("time")
        comments = request.form.get("comments")
        if not date or not time:
            flash("Please provide date and time.")
            return redirect(url_for("dashboard_view", section="schedule-fitting"))
        scheduled_at = f"{date}T{time}"
        fid = create_fitting(username, "fitting", scheduled_at, comments)
        if fid:
            flash("Fitting scheduled.")
            return redirect(url_for("dashboard_view", section="fitting-progress"))
        else:
            flash("Could not schedule.")
            return redirect(url_for("dashboard_view", section="schedule-fitting"))


    @app.route("/dashboard/profile", methods=["POST"])
    @login_required
    def profile_post():
        username = session.get("username")
        full_name = request.form.get("full_name")
        address = request.form.get("address")
        email = request.form.get("email")
        phone = request.form.get("phone")
        club_size = request.form.get("club_size")
        ok = save_profile(username, full_name, address, email, phone, club_size)
        if ok:
            flash("Profile updated.")
        else:
            flash("Could not update profile.")
        return redirect(url_for("dashboard_view", section="profile"))

    return app


if __name__ == "__main__":
    # Create and run the Flask app
    app = create_app()
    # Run the app on localhost:5000 with debug mode enabled
    app.run(host="127.0.0.1", port=5000, debug=True)
