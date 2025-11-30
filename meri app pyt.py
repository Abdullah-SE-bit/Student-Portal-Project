

# ---------- FILE UPLOAD HELPER (local, not Firebase) ----------

UPLOAD_ROOT = os.path.join(os.path.dirname(__file__), "static", "uploads")
os.makedirs(UPLOAD_ROOT, exist_ok=True)

def save_uploaded_file(file_storage, subfolder="announcements"):
    """Save an uploaded file under static/uploads and return metadata dict."""
    if not file_storage or file_storage.filename == "":
        return None

    safe_name = secure_filename(file_storage.filename)
    ext = os.path.splitext(safe_name)[1]
    unique = f"{uuid.uuid4().hex}{ext}"

    folder = os.path.join(UPLOAD_ROOT, subfolder)
    os.makedirs(folder, exist_ok=True)

    path = os.path.join(folder, unique)
    file_storage.save(path)

    rel_url = f"/static/uploads/{subfolder}/{unique}"
    return {
        "filename": safe_name,
        "url": rel_url,
        "mime_type": file_storage.mimetype or "application/octet-stream",
    }


@app.route('/')
def home():
    return render_template('main.html')  # your first "What are you?" page

    
# ========== TEACHER ANNOUNCEMENTS (SQLite) ==========

@app.route("/teacher/announcements", methods=["GET"])
def teacher_announcements():
    if 'user' not in session or session.get('user_type') != 'teacher':
        return redirect(url_for('teacher_login'))

    tid = session['user']

    # courses from flake.db
    conn_main = get_db()
    curm = conn_main.cursor()
    curm.execute("""
        SELECT Course_Code, Course_Name, Department
        FROM teachers
        WHERE Teacher_ID = ?
    """, (tid,))
    rows = curm.fetchall()
    conn_main.close()

    courses = []
    for r in rows:
        courses.append({
            'code': r['Course_Code'],
            'name': r['Course_Name'],
            'department': r['Department']
        })

    selected_course = request.args.get('course')
    if not selected_course and courses:
        selected_course = courses[0]['code']

    announcements = []
    if selected_course:
        conn = get_ann_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM announcements
            WHERE course_code = ?
            ORDER BY datetime(created_at) DESC
            LIMIT 30
        """, (selected_course,))
        announcements = [dict(r) for r in cur.fetchall()]
        conn.close()

    return render_template(
        "Announcement_T.html",
        user=tid,
        user_name=session.get('user_name'),
        courses=courses,
        selected_course=selected_course,
        announcements=announcements
    )


@app.route("/teacher/announcements/create", methods=["POST"])
def teacher_announcements_create():
    if 'user' not in session or session.get('user_type') != 'teacher':
        return redirect(url_for('teacher_login'))

    title   = request.form.get('title', '').strip()
    body    = request.form.get('body', '').strip()
    course  = request.form.get('course_code')
    kind    = request.form.get('type', 'text')   # text | assignment
    due_str = request.form.get('due_at', '').strip()

    if not title or not body or not course:
        flash("Title, body and course are required.", "danger")
        return redirect(url_for('teacher_announcements', course=course or ""))

    due_iso = None
    if kind == 'assignment' and due_str:
        try:
            dt = datetime.fromisoformat(due_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            due_iso = dt.isoformat()
        except ValueError:
            flash("Invalid due date/time.", "danger")
            return redirect(url_for('teacher_announcements', course=course))

    conn = get_ann_db()
    cur = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()

    cur.execute("""
        INSERT INTO announcements
        (title, body, created_by, created_by_role, created_at,
         audience_role, batch, department, section, course_code, type, due_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        title, body,
        session['user'], 'teacher', now_iso,
        'student', None, None, None, course,
        kind, due_iso
    ))
    ann_id = cur.lastrowid

    if 'files' in request.files:
        for file in request.files.getlist('files'):
            meta = save_uploaded_file(file, subfolder="teacher")
            if meta:
                cur.execute("""
                    INSERT INTO announcement_attachments
                    (announcement_id, filename, url, mime_type)
                    VALUES (?, ?, ?, ?)
                """, (ann_id, meta['filename'], meta['url'], meta['mime_type']))

    conn.commit()
    conn.close()

    flash("Announcement created.", "success")
    return redirect(url_for('teacher_announcements', course=course))


# ========== STUDENT ANNOUNCEMENTS (SQLite) ==========

def parse_student_batch_dept_section(roll_no: str):
    parts = roll_no.split('-')
    batch = parts[1] if len(parts) > 1 else None
    section = parts[2] if len(parts) > 2 else None
    dept = None
    return batch, dept, section


@app.route("/student/announcements", methods=["GET"])
def student_announcements():
    if 'user' not in session or session.get('user_type') != 'student':
        return redirect(url_for('student_login'))

    sid = session['user']

    conn_main = get_db()
    conn_main.row_factory = sqlite3.Row
    curm = conn_main.cursor()
    curm.execute("SELECT Roll_No, Name FROM students WHERE Roll_No = ?", (sid,))
    stu = curm.fetchone()
    conn_main.close()
    if not stu:
        flash("Student not found.", "danger")
        return redirect(url_for('student_home'))

    roll_no = stu['Roll_No']
    batch, dept, section = parse_student_batch_dept_section(roll_no)

    conn = get_ann_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM announcements
        WHERE audience_role IN ('student','all')
        ORDER BY datetime(created_at) DESC
        LIMIT 50
    """)
    rows = cur.fetchall()
    conn.close()

    announcements = []
    for r in rows:
        data = dict(r)
        ok = True
        if data.get('batch') and batch and data['batch'] != batch:
            ok = False
        if data.get('department') and dept and data['department'] != dept:
            ok = False
        if data.get('section') and section and data['section'] != section:
            ok = False
        if ok:
            announcements.append(data)

    return render_template(
        "Announcement_S.html",
        user=sid,
        user_name=stu['Name'],
        announcements=announcements
    )


# ========== ADMIN ANNOUNCEMENTS (SQLite) ==========

@app.route("/admin/announcements", methods=["GET"])
def admin_announcements():
    if 'user' not in session or session.get('user_type') != 'admin':
        return redirect(url_for('admin_login'))

    audience = request.args.get('audience', 'students')
    batch    = request.args.get('batch') or None
    dept     = request.args.get('department') or None
    section  = request.args.get('section') or None

    conn = get_ann_db()
    cur = conn.cursor()

    sql = """
        SELECT * FROM announcements
        WHERE 1=1
    """
    params = []

    if audience == 'students':
        sql += " AND audience_role IN ('student','all')"
    elif audience == 'teachers':
        sql += " AND audience_role IN ('teacher','all')"

    if batch:
        sql += " AND batch = ?"
        params.append(batch)
    if dept:
        sql += " AND department = ?"
        params.append(dept)
    if section:
        sql += " AND section = ?"
        params.append(section)

    sql += " ORDER BY datetime(created_at) DESC LIMIT 30"

    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()

    announcements = [dict(r) for r in rows]

    # simple lists; replace from flake.db if you want
    batches     = ["M-22", "M-23"]
    departments = ["SE", "CS", "EE"]
    sections    = ["A", "B", "C"]

    return render_template(
        "Announcement_A.html",
        user=session['user'],
        user_name="Admin",
        announcements=announcements,
        batches=batches,
        departments=departments,
        sections=sections,
        current_audience=audience,
        current_batch=batch or "",
        current_department=dept or "",
        current_section=section or "",
    )


@app.route("/admin/announcements/create", methods=["POST"])
def admin_announcements_create():
    if 'user' not in session or session.get('user_type') != 'admin':
        return redirect(url_for('admin_login'))

    title    = request.form.get('title', '').strip()
    body     = request.form.get('body', '').strip()
    audience = request.form.get('audience', 'students')
    batch    = request.form.get('batch') or None
    dept     = request.form.get('department') or None
    section  = request.form.get('section') or None

    if not title or not body:
        flash("Title and body are required.", "danger")
        return redirect(url_for('admin_announcements'))

    audience_role = 'all'
    if audience == 'students':
        audience_role = 'student'
    elif audience == 'teachers':
        audience_role = 'teacher'

    # save announcement
    conn = get_ann_db()
    cur = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()

    cur.execute("""
        INSERT INTO announcements
        (title, body, created_by, created_by_role, created_at,
         audience_role, batch, department, section, course_code, type, due_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        title, body,
        session['user'], 'admin', now_iso,
        audience_role, batch, dept, section, None,
        'text', None
    ))
    ann_id = cur.lastrowid

    # attachments
    if 'files' in request.files:
        for file in request.files.getlist('files'):
            meta = save_uploaded_file(file, subfolder="admin")
            if meta:
                cur.execute("""
                    INSERT INTO announcement_attachments
                    (announcement_id, filename, url, mime_type)
                    VALUES (?, ?, ?, ?)
                """, (ann_id, meta['filename'], meta['url'], meta['mime_type']))

    conn.commit()
    conn.close()

    flash("Announcement created.", "success")
    return redirect(url_for('admin_announcements'))

# ========== ANNOUNCEMNT ROUTES ========

@app.route("/announcements/<int:ann_id>/comments", methods=["GET", "POST"])
def announcement_comments(ann_id):
    if 'user' not in session:
        return jsonify({"error": "not_authenticated"}), 401

    conn = get_ann_db()
    cur = conn.cursor()

    if request.method == "GET":
        cur.execute("""
            SELECT * FROM announcement_comments
            WHERE announcement_id = ?
            ORDER BY datetime(created_at) ASC
        """, (ann_id,))
        rows = cur.fetchall()
        conn.close()
        comments = [dict(r) for r in rows]
        return jsonify(comments)

    # POST
    data = request.get_json(force=True)
    text = (data.get('text') or "").strip()
    if not text:
        conn.close()
        return jsonify({"error": "empty"}), 400

    now_iso = datetime.now(timezone.utc).isoformat()
    cur.execute("""
        INSERT INTO announcement_comments
        (announcement_id, author_id, author_role, text, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (ann_id, session['user'], session.get('user_type', 'student'), text, now_iso))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/announcements/<int:ann_id>/submit", methods=["POST"])
def announcement_submit(ann_id):
    if 'user' not in session or session.get('user_type') != 'student':
        return jsonify({"error": "not_allowed"}), 403

    conn = get_ann_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM announcements WHERE id = ?", (ann_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "not_found"}), 404

    ann = dict(row)
    if ann.get('type') != 'assignment':
        conn.close()
        return jsonify({"error": "not_assignment"}), 400

    now = datetime.now(timezone.utc)
    due_at = ann.get('due_at')
    if due_at:
        try:
            due_dt = datetime.fromisoformat(due_at)
            if due_dt.tzinfo is None:
                due_dt = due_dt.replace(tzinfo=timezone.utc)
            if now > due_dt:
                conn.close()
                return jsonify({"error": "late", "message": "Deadline has passed."}), 400
        except ValueError:
            # bad stored date; allow teacher to fix later
            pass

    file = request.files.get('submission_file')
    if not file or file.filename == "":
        conn.close()
        return jsonify({"error": "no_file"}), 400

    meta = save_uploaded_file(file, subfolder="submissions")
    if not meta:
        conn.close()
        return jsonify({"error": "upload_failed"}), 500

    now_iso = now.isoformat()
    cur.execute("""
        INSERT INTO announcement_submissions
        (announcement_id, student_id, filename, url, mime_type, submitted_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (ann_id, session['user'],
          meta['filename'], meta['url'], meta['mime_type'], now_iso))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

