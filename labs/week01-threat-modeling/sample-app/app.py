"""
Tiny sample web app for Week 1 threat modeling.
You will NOT exploit this in Week 1 — you will draw a data-flow diagram
and apply STRIDE to its components (web client, app, SQLite DB, /upload).
"""
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import sqlite3, os

app = Flask(__name__)
DB = "notes.db"
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def init_db():
    con = sqlite3.connect(DB)
    con.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, owner TEXT, body TEXT)")
    con.commit(); con.close()

@app.route("/notes", methods=["GET", "POST"])
def notes():
    con = sqlite3.connect(DB)
    if request.method == "POST":
        owner = request.json.get("owner", "anon")
        body = request.json.get("body", "")
        con.execute("INSERT INTO notes (owner, body) VALUES (?, ?)", (owner, body))
        con.commit()
    rows = con.execute("SELECT id, owner, body FROM notes").fetchall()
    con.close()
    return jsonify(rows)

ALLOWED_EXTENSIONS = {"txt", "png", "jpg", "jpeg", "gif", "md"}


def allowed_file(name):
    return "." in name and name.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/upload", methods=["POST"])
def upload():
    f = request.files["file"]
    # Class fix: no client-supplied string ever becomes a path component.
    # secure_filename() strips directory separators/"..", then the allowlist
    # caps what kind of file may be stored at all.
    name = secure_filename(f.filename or "")
    if not name or not allowed_file(name):
        return jsonify(error="filename rejected"), 400
    f.save(os.path.join(UPLOAD_DIR, name))
    return {"saved": name}

@app.route("/files/<name>")
def files(name):
    return send_from_directory(UPLOAD_DIR, name)

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
