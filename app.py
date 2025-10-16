from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Needed for session handling

@app.route('/')
def home():
    return render_template('main.html')  # your first "What are you?" page

# ---------- TEACHER LOGIN ----------
@app.route('/login_T.html', methods=['GET', 'POST'])
def teacher_login():
    if request.method == 'POST':
        tid = request.form['teacher_id']
        password = request.form['password']

        conn = sqlite3.connect('flake.db')
        cur = conn.cursor()
        cur.execute("SELECT * FROM teachers WHERE teacher_id=? AND password=?", (tid, password))
        teacher = cur.fetchone()
        conn.close()

        if teacher:
            session['user'] = tid
            return redirect(url_for('teacher_dashboard'))
        else:
            flash("Invalid ID or Password", "danger")

    return render_template('login_T.html')


# ---------- STUDENT LOGIN ----------
@app.route('/login_S.html', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        sid = request.form['student_id']
        password = request.form['password']

        conn = sqlite3.connect('flake.db')
        cur = conn.cursor()
        cur.execute("SELECT * FROM students WHERE student_id=? AND password=?", (sid, password))
        student = cur.fetchone()
        conn.close()

        if student:
            session['user'] = sid
            return redirect(url_for('student_dashboard'))
        else:
            flash("Invalid ID or Password", "danger")

    return render_template('login_S.html')


# ---------- ADMIN LOGIN ----------
@app.route('/login_A.html', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        aid = request.form['admin_id']
        password = request.form['password']

        conn = sqlite3.connect('flake.db')
        cur = conn.cursor()
        cur.execute("SELECT * FROM admins WHERE admin_id=? AND password=?", (aid, password))
        admin = cur.fetchone()
        conn.close()

        if admin:
            session['user'] = aid
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid ID or Password", "danger")

    return render_template('login_A.html')



@app.route('/teacher_dashboard')
def teacher_dashboard():
    return render_template('teacher_dashboard.html', user=session.get('user'))

@app.route('/student_dashboard')
def student_dashboard():
    return render_template('student_dashboard.html', user=session.get('user'))

@app.route('/admin_dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html', user=session.get('user'))



# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))


# ------------------ RUN SERVER ------------------
if __name__ == "__main__":
    app.run(debug=True)