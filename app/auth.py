from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from . import db, utcnow
from .models import User, Event

auth_bp = Blueprint("auth", __name__)

@auth_bp.get("/")
def home():
    if session.get("user_id"):
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("auth.login", role="tenant"))

@auth_bp.route("/login/<role>", methods=["GET", "POST"])
def login(role):
    if role not in {"admin", "owner", "tenant"}:
        return "Invalid role", 404
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email, role=role, active=True).first()
        if user and check_password_hash(user.password_hash, password):
            session.clear()
            session["user_id"] = user.id
            session["role"] = user.role
            db.session.add(Event(actor_id=user.id, event_type="auth.login",
                                 entity_type="user", entity_id=user.id,
                                 message=f"{role} login"))
            db.session.commit()
            return redirect(url_for("main.dashboard"))
        flash("Invalid email, password, or role.", "error")
    return render_template("login.html", selected_role=role)

@auth_bp.post("/logout")
def logout():
    uid = session.get("user_id")
    if uid:
        db.session.add(Event(actor_id=uid, event_type="auth.logout",
                             entity_type="user", entity_id=uid, message="Logout"))
        db.session.commit()
    session.clear()
    return redirect(url_for("auth.login", role="tenant"))
