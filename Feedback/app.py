from flask import Flask, render_template, request, redirect, flash
import sqlite3
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

app = Flask(__name__)
app.secret_key = "super-secret-key"

# Email Config
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_FROM = "your_email@gmail.com"
EMAIL_TO = "destination_email@gmail.com"
EMAIL_PASSWORD = "your_app_password"

# Init DB
def init_db():
    with sqlite3.connect("feedback.db") as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                message TEXT NOT NULL,
                sent BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

init_db()
feedback_db = []

# Main Feedback Route
@app.route("/", methods=["GET", "POST"])
def feedback():
    if request.method == "POST":
        name = request.form["name"]
        message = request.form["message"]

        if len(message.strip()) == 0:
            flash("Message can't be empty!", "error")
            return redirect("/")

        if len(message) > 1000:
            flash("Message too long (1000 char max).", "error")
            return redirect("/")

        with sqlite3.connect("feedback.db") as con:
            cur = con.cursor()
            cur.execute("INSERT INTO feedback (name, message) VALUES (?, ?)", (name, message))
            fid = cur.lastrowid

        try:
            msg = MIMEText(f"{message}\n\nFrom: {name}")
            msg["Subject"] = f"Feedback from {name}"
            msg["From"] = EMAIL_FROM
            msg["To"] = EMAIL_TO

            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(EMAIL_FROM, EMAIL_PASSWORD)
                server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())

            with sqlite3.connect("feedback.db") as con:
                con.execute("DELETE FROM feedback WHERE id = ?", (fid,))
            flash("✅ Feedback sent!", "success")

        except Exception as e:
            flash("❌ Could not send email. We'll retry later.", "error")

        return redirect("/")
    return render_template("feedback.html")

# Admin: View unsent feedbacks
@app.route("/unsent")
def unsent():
    with sqlite3.connect("feedback.db") as con:
        rows = con.execute("SELECT * FROM feedback WHERE sent = 0 ORDER BY created_at DESC").fetchall()
    return render_template("unsent.html", feedbacks=rows)

# Retry sending unsent
@app.route("/resend")
def resend():
    with sqlite3.connect("feedback.db") as con:
        rows = con.execute("SELECT * FROM feedback WHERE sent = 0").fetchall()

    for row in rows:
        fid, name, message, sent, created_at = row
        try:
            msg = MIMEText(f"{message}\n\nFrom: {name}")
            msg["Subject"] = f"[Retry] Feedback from {name}"
            msg["From"] = EMAIL_FROM
            msg["To"] = EMAIL_TO

            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(EMAIL_FROM, EMAIL_PASSWORD)
                server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())

            with sqlite3.connect("feedback.db") as con:
                con.execute("DELETE FROM feedback WHERE id = ?", (fid,))
        except:
            pass

    flash("🔁 Retried sending unsent feedback!", "success")
    return redirect("/unsent")


if __name__ == "__main__":
    app.run(debug=True)
