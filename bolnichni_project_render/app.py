from flask import Flask, render_template, request, redirect, session, flash
import sqlite3, os, tempfile
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.permanent_session_lifetime = timedelta(minutes=10)
app.secret_key = 'secret_key'
mail = Mail(app)

app.config['MAIL_SERVER'] = os.getenv("MAIL_SERVER")
app.config['MAIL_PORT'] = int(os.getenv("MAIL_PORT"))
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_USE_TLS'] = True

mail.init_app(app)

def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (personal_number,)).fetchone()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['email']
            session['name'] = user['name']
            return redirect('/home')
        flash("Грешен персонален номер или парола")
    return render_template("login.html")

@app.route('/home', methods=['GET', 'POST'])
def home():
    if 'user_id' not in session: return redirect('/')
    if request.method == 'POST':
        from_date = request.form['from_date']
        to_date = request.form['to_date']
        days = request.form['days']
        note = request.form['note']
        file = request.files['file']

        if not file: flash("Няма избран файл."); return redirect('/home')
        filename = file.filename
        db = get_db()
        hr_email = db.execute("SELECT hr_email FROM settings WHERE id = 1").fetchone()['hr_email']
        user = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            file.save(tmp.name)
            try:
                msg = Message("Болничен от " + user['name'],
                              sender=app.config['MAIL_USERNAME'],
                              recipients=[hr_email])
                msg.body = f"Служител: {user['name']}\nПериод: {from_date} - {to_date}\nДни: {days}\nЗабележка: {note}"
                with open(tmp.name, 'rb') as f:
                    msg.attach(filename, file.content_type, f.read())
                mail.send(msg)
                flash("Болничният беше изпратен успешно.")
            finally:
                os.remove(tmp.name)
        return redirect('/home')
    return render_template("index.html", name=session['name'])

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'user_id' not in session: return redirect('/')
    if request.method == 'POST':
        new_pass = request.form['new_password']
        confirm_pass = request.form['confirm_password']
        if new_pass != confirm_pass:
            flash("Паролите не съвпадат.")
            return redirect('/change_password')
        db = get_db()
        db.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                   (generate_password_hash(new_pass), session['user_id']))
        db.commit()
        flash("Паролата е променена успешно.")
        return redirect('/home')
    return render_template("change_password.html")

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session.get('username') != 'admin': return redirect('/')
    db = get_db()
    if request.method == 'POST':
        hr_email = request.form['hr_email']
        db.execute("UPDATE settings SET hr_email = ? WHERE id = 1", (hr_email,))
        db.commit()
        flash("HR имейлът е обновен.")
    users = db.execute("SELECT * FROM users WHERE personal_number != 'admin'").fetchall()
    current_hr_email = db.execute("SELECT hr_email FROM settings WHERE id = 1").fetchone()['hr_email']
    return render_template("admin.html", users=users, current_hr_email=current_hr_email)


@app.route('/logout')
def logout():
    session.clear()
    flash("Излязохте от системата.")
    return redirect('/')
