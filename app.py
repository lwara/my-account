import os
from flask import Flask, render_template, request, redirect, url_for, flash, session

from db import create_user, verify_password


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
                return redirect(url_for("home"))
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

    return app


if __name__ == "__main__":
    # Create and run the Flask app
    app = create_app()
    # Run the app on localhost:5000 with debug mode enabled
    app.run(host="127.0.0.1", port=5000, debug=True)
