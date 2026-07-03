"""Optional login/logout, active only when RCDB_PASSWORD is set."""
import secrets

from flask import Blueprint, redirect, render_template, request, session, url_for

from ..config import AUTH_PASSWORD
from ..security import clear_failures, is_locked, record_failure

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    # If auth is disabled there is nothing to log into.
    if not AUTH_PASSWORD:
        return redirect(url_for("pages.index"))

    error = None
    if request.method == "POST":
        ip = request.remote_addr or "?"
        if is_locked(ip):
            error = "Too many attempts. Please wait a few minutes and try again."
        elif secrets.compare_digest(request.form.get("password", ""), AUTH_PASSWORD):
            session.clear()
            session["authed"] = True
            session.permanent = True
            clear_failures(ip)
            nxt = request.args.get("next", "")
            if not nxt.startswith("/") or nxt.startswith("//"):
                nxt = url_for("pages.index")
            return redirect(nxt)
        else:
            record_failure(ip)
            error = "Incorrect password."

    return render_template("login.html", error=error), (401 if error else 200)


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
