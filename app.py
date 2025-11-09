from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
from datetime import datetime
import re
from flask_socketio import SocketIO, emit, join_room

def get_db():
    """Create a database connection with row factory for dictionary-like access"""
    conn = sqlite3.connect('flake.db')
    conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    return conn

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
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
        cur.execute("SELECT Name, Teacher_ID FROM teachers WHERE Teacher_ID=?", (tid,))
        teacher = cur.fetchone()
        conn.close()

        if teacher:
            real_pass = ''.join([ch for ch in tid if ch.isdigit()])[-4:]
            if password == real_pass:
                session['user'] = tid
                session['user_name'] = teacher[0]
                session['Teacher_ID'] = teacher[1]   # ✅ FIX ADDED
                return redirect(url_for('teacher_home'))
            else:
                flash("Invalid ID or Password", "danger")
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
        cur.execute("SELECT Name FROM students WHERE Roll_No=? AND password=?", (sid, password))
        student = cur.fetchone()
        conn.close()

        if student:
            session['user'] = sid
            session['user_name'] = student[0]  # store name in session
            return redirect(url_for('student_home'))
        else:
            flash("Invalid ID or Password", "danger")

    return render_template('login_S.html')


# ---------- ADMIN LOGIN ----------
@app.route('/login_A.html', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        aid = request.form['admin_id'].strip()
        password = request.form['password'].strip()

        conn = sqlite3.connect('flake.db')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM admins WHERE admin_id=? AND password=?", (aid, password))
        admin = cur.fetchone()
        conn.close()

        if admin:
            # Store admin ID and type in session
            session['user'] = aid
            session['user_type'] = 'admin'

            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid ID or Password", "danger")

    return render_template('login_A.html')



@app.route('/teacher_dashboard')
def teacher_dashboard():
    return render_template(
        'teacher_dashboard.html',
        user=session.get('user'),
        user_name=session.get('user_name')
    )


@app.route('/student_dashboard')
def student_dashboard():
    return render_template(
        'student_dashboard.html',
        user=session.get('user'),
        user_name=session.get('user_name')
    )


@app.route('/admin_dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html', user=session.get('user'))


# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))


# ---------- STUDENT HOME -----------
@app.route('/student_home')
def student_home():
    if 'user' not in session:
        return redirect(url_for('student_login'))

    sid = session['user']

    conn = sqlite3.connect('flake.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM students WHERE Roll_No = ?", (sid,))
    student = cur.fetchone()
    conn.close()

    # -------------------------------
    # Extract batch, degree, and section from Roll_No
    # Example Roll_No: FA23-SE-A-1234
    # -------------------------------
    roll_no = student['Roll_No']
    roll_parts = roll_no.split('-')

    batch = roll_parts[1] if len(roll_parts) > 1 else "N/A"
    degree_code = roll_parts[2] if len(roll_parts) > 2 else "N/A"
    section = roll_parts[3][0] if len(roll_parts) > 3 else "N/A"

    degree_map = {
        'SE': 'Software Engineering',
        'AI': 'Artificial Intelligence',
        'DS': 'Data Science',
        'CY': 'Cyber Security'
    }
    degree_name = degree_map.get(degree_code, degree_code)

    return render_template(
        'home_S.html',
        student=student,
        batch=batch,
        degree_name=degree_name,
        section=section
    )


# -------------- TENTATIVE STUDY PLAN -----------------------
@app.route('/student_study_plan')
def student_study_plan():
    return render_template('tentativeStudyPlan.html')


# ------------------ TEACHER HOME -----------------------
@app.route('/teacher_home')
def teacher_home():
    if 'user' not in session:
        return redirect(url_for('teacher_login'))

    tid = session['user']  # Example: T-M-SE-CS-1001

    conn = sqlite3.connect('flake.db')
    cur = conn.cursor()
    cur.execute("""
        SELECT Teacher_ID, Name, Gender, DOB, CNIC, Email, Mobile_No,
               Current_Address, Permanent_Address, Home_Phone, Postal_Code,
               Department, Course_Name
        FROM teachers
        WHERE Teacher_ID = ?
    """, (tid,))
    row = cur.fetchone()
    conn.close()

    if not row:
        flash("Teacher not found", "danger")
        return redirect(url_for('teacher_dashboard'))

    # Convert fetched row into dictionary
    teacher = {
        'Teacher_ID': row[0],
        'Name': row[1],
        'Gender': row[2],
        'DOB': row[3],
        'CNIC': row[4],
        'Email': row[5],
        'Mobile_No': row[6],
        'Current_Address': row[7],
        'Permanent_Address': row[8],
        'Home_Phone': row[9],
        'Postal_Code': row[10],
        'Department': row[11],
        'Course_Name': row[12]
    }

    # ---------- Extract domain from Teacher_ID ----------
    parts = tid.split('-')
    domain_code = parts[3].upper() if len(parts) > 3 else ""
    domain_map = {
        "CS": "Computing",
        "MT": "Mathematics",
        "CL": "Computing",
        "SS": "Social Sciences"
    }
    domain = domain_map.get(domain_code, "Unknown")

    # ---------- Courses (from same table) ----------
    courses = [teacher['Course_Name']] if teacher['Course_Name'] else ["No courses assigned"]

    return render_template(
        'home_T.html',
        teacher=teacher,
        department=teacher['Department'],
        domain=domain,
        courses=courses
    )


# -------------------- ATTENDANCE ----------------
@app.route('/student_attendance')
def student_attendance():
    if 'user' not in session:
        return redirect(url_for('student_login'))

    roll_no = session['user']

    conn = sqlite3.connect('flake.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Step 1: Get all courses the student is enrolled in
    cur.execute("""
        SELECT c.Course_Code, c.Course_Name
        FROM enrollments e
        JOIN courses c ON e.Course_Code = c.Course_Code
        WHERE e.Roll_No = ?
    """, (roll_no,))
    courses = cur.fetchall()

    # Step 2: Get attendance records for that student
    cur.execute("""
        SELECT Course_Code, Date, Attendance
        FROM attendance
        WHERE Roll_No = ?
        ORDER BY Date
    """, (roll_no,))
    attendance_records = cur.fetchall()
    conn.close()

    # Step 3: Group attendance by course name and convert to P/A/L
    attendance = {}
    for record in attendance_records:
        course_code = record['Course_Code']
        course_name = next(
            (c['Course_Name'] for c in courses if c['Course_Code'] == course_code),
            course_code
        )

        if course_name not in attendance:
            attendance[course_name] = []

        status = record['Attendance'].strip().lower()
        if status in ['present', 'p', '1']:
            short_status = 'P'
        elif status in ['absent', 'a', '0']:
            short_status = 'A'
        elif status in ['leave', 'l']:
            short_status = 'L'
        else:
            short_status = '-'

        date_value = record['Date']
        if isinstance(date_value, str):
            date_value = date_value.split(' ')[0]
        elif isinstance(date_value, (datetime,)):
            date_value = date_value.date().isoformat()

        attendance[course_name].append({
            'Date': date_value,
            'Status': short_status
        })

    return render_template(
        'attendance_S.html',
        courses=courses,
        attendance=attendance
    )


# ------------------ STUDENT INBOX ----------------
@app.route('/student_inbox')
def student_inbox():
    if 'user' not in session:
        return redirect(url_for('student_login'))

    sid = session['user']

    conn = sqlite3.connect('flake.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # --- Get student info ---
    cur.execute("""
        SELECT Roll_No, Name
        FROM students
        WHERE Roll_No = ?
    """, (sid,))
    student = cur.fetchone()

    if not student:
        conn.close()
        flash("Student not found!", "danger")
        return redirect(url_for('student_home'))

    stu_name = student['Name']
    roll_no = student['Roll_No']

    # --- Extract Department from Roll_No ---
    parts = roll_no.split('-')
    dept = None

    if len(parts) >= 2:
        p1 = parts[1]
        if '_' in p1:
            sub = p1.split('_')
            if len(sub) >= 2:
                dept = sub[1]
        else:
            if len(parts) >= 3:
                if '_' in parts[2]:
                    dept = parts[2].split('_')[0]
                else:
                    dept = ''.join([ch for ch in parts[2] if ch.isalpha()])

    # Fallback
    if not dept:
        tokens = re.split(r'[_\-]', roll_no)
        for t in tokens:
            if re.fullmatch(r'[A-Za-z]{2,}', t):
                dept = t
                break

    if not dept:
        dept = ''

    # --- Get enrolled course codes for this student ---
    cur.execute("""
        SELECT Course_Code
        FROM enrollments
        WHERE Roll_No = ?
    """, (sid,))
    
    enrolled_courses = [row['Course_Code'] for row in cur.fetchall()]

    # --- If no enrollments, show no teachers ---
    if not enrolled_courses:
        contacts = []
        conn.close()
        return render_template('inbox_S.html', user=sid, user_name=stu_name, contacts=contacts)

    # --- Query teachers by enrolled course codes AND department ---
    placeholders = ','.join(['?' for _ in enrolled_courses])
    query = f"""
        SELECT DISTINCT t.Teacher_ID, t.Name, t.Course_Code, t.Course_Name
        FROM teachers t
        WHERE t.Course_Code IN ({placeholders})
          AND t.Department = ?
    """
    
    cur.execute(query, tuple(enrolled_courses) + (dept,))
    teachers = cur.fetchall()

    # --- Build inbox contact list ---
    contacts = []
    for t in teachers:
        contacts.append({
            'id': t['Teacher_ID'],
            'name': t['Name'],
            'course_code': t['Course_Code'],
            'course': t['Course_Name'],
            'last_msg': 'No messages yet',
            'last_time': '',
            'unread': 0
        })

    conn.close()

    return render_template(
        'inbox_S.html',
        user=sid,
        user_name=stu_name,
        contacts=contacts
    )

# ------------------- Teacher Inbox ---------------------------

@app.route('/teacher_inbox')
def teacher_inbox():
    if 'user' not in session:
        return redirect(url_for('teacher_login'))

    tid = session['user']  # Teacher ID, e.g., T-M-SE-CS-1001

    conn = sqlite3.connect('flake.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # --- Get teacher info ---
    cur.execute("""
        SELECT Teacher_ID, Name, Department, Course_Code
        FROM teachers
        WHERE Teacher_ID = ?
    """, (tid,))
    teacher = cur.fetchone()

    if not teacher:
        conn.close()
        flash("Teacher not found!", "danger")
        return redirect(url_for('teacher_home'))

    teacher_name = teacher['Name']
    department = teacher['Department']
    course_code = teacher['Course_Code']

    # --- Get students enrolled in this teacher's course ---
    cur.execute("""
        SELECT DISTINCT e.Roll_No
        FROM enrollments e
        WHERE e.Course_Code = ?
    """, (course_code,))
    
    enrolled_roll_nos = [row['Roll_No'] for row in cur.fetchall()]

    # --- If no enrollments, show no students ---
    if not enrolled_roll_nos:
        contacts = []
        sections = []
        conn.close()
        return render_template('inbox_T.html', user=tid, user_name=teacher_name, contacts=contacts, sections=sections)

    # --- Filter students by department (from Roll_No) and get their details ---
    placeholders = ','.join(['?' for _ in enrolled_roll_nos])
    query = f"""
        SELECT Roll_No, Name
        FROM students
        WHERE Roll_No IN ({placeholders})
    """
    
    cur.execute(query, tuple(enrolled_roll_nos))
    students_raw = cur.fetchall()

    # --- Build inbox contact list (filter by department) ---
    contacts = []
    sections_set = set()
    
    for s in students_raw:
        roll_no = s['Roll_No']
        
        # Extract department from Roll_No (e.g., M-22_SE-A-3001 -> SE)
        parts = roll_no.split('-')
        student_dept = None
        section = None  # This will be A, B, C, etc.
        
        if len(parts) >= 2:
            p1 = parts[1]
            if '_' in p1:
                sub = p1.split('_')
                if len(sub) >= 2:
                    student_dept = sub[1]
        
        # Extract section (A, B, C) from third part
        # Roll_No format: M-22_SE-A-3001
        # parts[2] should be 'A' (the section letter)
        if len(parts) >= 3:
            # parts[2] is like 'A' or could have other chars
            section_part = parts[2]
            # Extract only alphabetic characters (should be single letter like A, B, C)
            section = ''.join([ch for ch in section_part if ch.isalpha()])
            if not section:
                section = None
        
        # Fallback for department
        if not student_dept:
            tokens = re.split(r'[_\-]', roll_no)
            for t in tokens:
                if re.fullmatch(r'[A-Za-z]{2,}', t):
                    student_dept = t
                    break
        
        # Only add if department matches
        if student_dept == department:
            if section:
                sections_set.add(section)
            
            display_name = f"{s['Name']}" + (f" (Sec {section})" if section else "")
            
            contacts.append({
                'id': roll_no,
                'name': s['Name'],  # Just name without section
                'display_name': display_name,  # Name with section for display
                'roll_no': roll_no,
                'section': section if section else '',
                'last_msg': 'No messages yet',
                'last_time': '',
                'unread': 0
            })

    conn.close()
    
    # Sort sections alphabetically
    sections = sorted(list(sections_set))

    return render_template(
        'inbox_T.html',
        user=tid,
        user_name=teacher_name,
        contacts=contacts,
        sections=sections
    )

# ------------------- Admin Inbox ---------------------------

@app.route('/inbox_A')
def inbox_A():
    if 'user' not in session:
        return redirect(url_for('admin_login'))

    aid = session['user']  # Admin ID

    conn = sqlite3.connect('flake.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # --- Get admin info ---
    cur.execute("""
        SELECT admin_id FROM admins WHERE admin_id = ?
    """, (aid,))
    admin = cur.fetchone()

    if not admin:
        conn.close()
        flash("Admin not found!", "danger")
        return redirect(url_for('admin_dashboard'))

    # --- Get ALL students ---
    cur.execute("""
        SELECT Roll_No, Name FROM students ORDER BY Name
    """)
    students_raw = cur.fetchall()

    # --- Get ALL teachers ---
    cur.execute("""
        SELECT Teacher_ID, Name, Department, Course_Code FROM teachers ORDER BY Name
    """)
    teachers_raw = cur.fetchall()

    conn.close()

    # --- Build contacts list ---
    contacts = []

    # Add all students
    for s in students_raw:
        roll_no = s['Roll_No']
        
        # Extract section from Roll_No
        parts = roll_no.split('-')
        section = ''
        department = ''
        
        if len(parts) >= 2:
            p1 = parts[1]
            if '_' in p1:
                sub = p1.split('_')
                if len(sub) >= 2:
                    department = sub[1]
        
        if len(parts) >= 3:
            section_part = parts[2]
            section = ''.join([ch for ch in section_part if ch.isalpha()])
        
        display_name = f"{s['Name']}" + (f" (Sec {section})" if section else "")
        
        contacts.append({
            'id': roll_no,
            'name': s['Name'],
            'display_name': display_name,
            'roll_no': roll_no,
            'type': 'student',
            'department': department,
            'section': section,
            'last_msg': 'No messages yet',
            'last_time': '',
            'unread': 0
        })

    # Add all teachers
    for t in teachers_raw:
        teacher_id = t['Teacher_ID']
        department = t['Department']
        course_code = t['Course_Code']
        
        display_name = f"{t['Name']} (Teacher - {department})"
        
        contacts.append({
            'id': teacher_id,
            'name': t['Name'],
            'display_name': display_name,
            'roll_no': teacher_id,
            'type': 'teacher',
            'department': department,
            'section': '',
            'course_code': course_code,
            'last_msg': 'No messages yet',
            'last_time': '',
            'unread': 0
        })

    # Get unique departments and sections for filters
    departments = sorted(list(set([c['department'] for c in contacts if c['department']])))
    sections = sorted(list(set([c['section'] for c in contacts if c['section']])))

    return render_template(
        'inbox_A.html',
        user=aid,
        user_name='Admin',
        contacts=contacts,
        departments=departments,
        sections=sections
    )

# ------------------- Course Registration ---------------------
# Add these utility functions and routes to your app.py file

def extract_student_info(roll_no):
    """
    Extract batch, degree, section from Roll_No
    Example Roll_No formats:
    - FA23-SE-A-1234 (Format 1)
    - M-22_SE-A-3001 (Format 2)
    
    Returns dict with: batch, degree_code, degree_name, section
    """
    try:
        degree_map = {
            'SE': 'Software Engineering',
            'AI': 'Artificial Intelligence',
            'DS': 'Data Science',
            'CY': 'Cyber Security'
        }
        
        parts = roll_no.split('-')
        batch = None
        degree_code = None
        section = None
        
        # Handle Format 1: FA23-SE-A-1234
        if len(parts) >= 3 and len(parts[0]) >= 2:
            prefix = parts[0]
            batch = ''.join([ch for ch in prefix if ch.isdigit()])
            if len(parts) > 1 and parts[1] in degree_map:
                degree_code = parts[1]
            if len(parts) > 2:
                section = parts[2]
        
        # Handle Format 2: M-22_SE-A-3001
        elif len(parts) >= 2 and '_' in parts[1]:
            sub_parts = parts[1].split('_')
            if len(sub_parts) >= 1:
                batch = sub_parts[0]
            if len(sub_parts) >= 2 and sub_parts[1] in degree_map:
                degree_code = sub_parts[1]
            if len(parts) > 2:
                section = parts[2]
        
        # Fallback
        if not batch or not degree_code:
            tokens = roll_no.replace('_', '-').split('-')
            for token in tokens:
                if not batch and len(token) >= 2 and token[-2:].isdigit():
                    batch = token[-2:]
                if not degree_code:
                    alpha_only = ''.join([ch for ch in token if ch.isalpha()])
                    if len(alpha_only) == 2 and alpha_only in degree_map:
                        degree_code = alpha_only
        
        degree_name = degree_map.get(degree_code, degree_code if degree_code else 'N/A')
        
        return {
            'batch': batch or 'N/A',
            'degree_code': degree_code or 'N/A',
            'degree_name': degree_name,
            'section': section or 'N/A'
        }
    
    except Exception as e:
        print(f"Error extracting student info: {e}")
        return {'batch': 'N/A', 'degree_code': 'N/A', 'degree_name': 'N/A', 'section': 'N/A'}


def batch_to_semester(batch):
    """
    Convert batch year to current semester (Based on app.py logic)
    
    Mapping (for 2025):
    - 2022 batch (22) -> Semester 7
    - 2023 batch (23) -> Semester 5
    - 2024 batch (24) -> Semester 3
    - 2025 batch (25) -> Semester 1
    """
    batch_to_sem = {
        '22': 7,
        '23': 5,
        '24': 3,
        '25': 1
    }
    return batch_to_sem.get(str(batch), None)


def semester_to_course_digit(semester):
    """
    Convert semester number to course code digit
    
    Special rule (from app.py student_inbox logic):
    - Semester 1 is encoded as '0' in Course_Code
    - Semester 3 is encoded as '3' (or '30', '31', etc.)
    - Semester 5 is encoded as '5' (or '50', '51', etc.)
    - Semester 7 is encoded as '7' (or '70', '71', etc.)
    
    Returns the digit that appears after '-' in course code
    """
    if semester == 1:
        return '0'
    else:
        return str(semester)


# -------------------- COURSE REGISTRATION --------------------
@app.route('/course_registration')
def course_registration():
    """
    Display course registration page with intelligent course offering:
    1. Show ALL courses for current semester (even if prerequisites not met)
    2. If prerequisite not met, also offer the prerequisite course for retake
    3. Include failed courses that need to be retaken
    """
    if 'user' not in session:
        return redirect(url_for('student_login'))
    
    sid = session['user']
    
    try:
        conn = sqlite3.connect('flake.db')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Get student info
        cur.execute("""
            SELECT Roll_No, Name FROM students WHERE Roll_No = ?
        """, (sid,))
        student_row = cur.fetchone()
        
        if not student_row:
            conn.close()
            flash("Student not found", "danger")
            return redirect(url_for('student_home'))
        
        # Extract batch and degree from Roll_No
        roll_no = student_row['Roll_No']
        roll_parts = roll_no.split('-')
        
        # Extract batch (e.g., from M-22_SE-A-3001, extract '22')
        batch = None
        if len(roll_parts) >= 2:
            p1 = roll_parts[1]
            if '_' in p1:
                batch = p1.split('_')[0]
            else:
                batch = p1
        
        # Map batch to current semester
        batch_to_sem = {
            '22': 7,
            '23': 5,
            '24': 3,
            '25': 1
        }
        current_semester = batch_to_sem.get(batch, None)
        
        if current_semester is None:
            conn.close()
            flash("Unable to determine your current semester", "danger")
            return redirect(url_for('student_home'))
        
        # Convert semester to course code digit
        # Semester 1 → '0', all others → their number
        if current_semester == 1:
            code_digit = '0'
        else:
            code_digit = str(current_semester)
        
        # DEBUG: Print to console
        print(f"\n{'='*60}")
        print(f"🔍 DEBUG - Student: {sid}, Batch: {batch}, Semester: {current_semester}, Code Digit: {code_digit}")
        print(f"{'='*60}")
        
        # Get all courses for this semester
        cur.execute("""
            SELECT Course_Code, Course_Name, Credit_Hr, Prerequisite
            FROM courses
            WHERE substr(Course_Code, instr(Course_Code, '-') + 1, 1) = ?
            ORDER BY Course_Code
        """, (code_digit,))
        
        current_sem_courses_raw = cur.fetchall()
        
        print(f"\n📚 Found {len(current_sem_courses_raw)} courses for semester {current_semester}:")
        for c in current_sem_courses_raw:
            print(f"  - {c['Course_Code']}: {c['Course_Name']} (Prereq: {c['Prerequisite'] or 'None'})")
        
        # Get enrolled courses for this student
        cur.execute("""
            SELECT Course_Code FROM enrollments WHERE Roll_No = ?
        """, (sid,))
        enrolled = [row['Course_Code'] for row in cur.fetchall()]
        
        # Get passed courses (prerequisites met)
        cur.execute("""
            SELECT Course_Code FROM passed_courses WHERE Roll_No = ?
        """, (sid,))
        passed = [row['Course_Code'] for row in cur.fetchall()]
        
        print(f"\n✅ Passed courses: {passed}")
        print(f"📝 Enrolled courses: {enrolled}")
        
        # Build the courses list - SHOW ALL COURSES
        courses_to_offer = []
        prerequisite_courses_to_retake = set()
        
        for c in current_sem_courses_raw:
            code = c['Course_Code']
            prerequisite = c['Prerequisite']
            
            # Check if student has passed the prerequisite
            prerequisite_met = (not prerequisite or prerequisite in passed)
            
            # Extract semester info
            code_parts = code.split('-')
            sem_digit = code_parts[1][0] if len(code_parts) > 1 else '0'
            
            if sem_digit == '0':
                semester = 1
            else:
                semester = int(sem_digit) if sem_digit.isdigit() else 1
            
            department = code_parts[0] if len(code_parts) > 0 else 'CS'
            
            # ADD ALL CURRENT SEMESTER COURSES (show all, regardless of prerequisites)
            courses_to_offer.append({
                'code': code,
                'name': c['Course_Name'],
                'credits': c['Credit_Hr'],
                'semester': semester,
                'prerequisite': prerequisite,
                'department': department,
                'type': 'current'  # Current semester course
            })
            
            # Track prerequisites that need retaking
            if not prerequisite_met and prerequisite:
                print(f"⚠️  {code} requires {prerequisite} which is not passed - adding {prerequisite} to retake list")
                prerequisite_courses_to_retake.add(prerequisite)
        
        # Add prerequisite courses that need to be retaken
        if prerequisite_courses_to_retake:
            print(f"\n🔄 Fetching {len(prerequisite_courses_to_retake)} prerequisite course(s) for retake:")
            for prereq in prerequisite_courses_to_retake:
                print(f"  - {prereq}")
            
            placeholders = ','.join(['?' for _ in prerequisite_courses_to_retake])
            cur.execute(f"""
                SELECT Course_Code, Course_Name, Credit_Hr, Prerequisite
                FROM courses
                WHERE Course_Code IN ({placeholders})
            """, tuple(prerequisite_courses_to_retake))
            
            prereq_courses_raw = cur.fetchall()
            
            print(f"\n📋 Found {len(prereq_courses_raw)} prerequisite course(s) in database:")
            
            for c in prereq_courses_raw:
                code = c['Course_Code']
                code_parts = code.split('-')
                sem_digit = code_parts[1][0] if len(code_parts) > 1 else '0'
                
                if sem_digit == '0':
                    semester = 1
                else:
                    semester = int(sem_digit) if sem_digit.isdigit() else 1
                
                department = code_parts[0] if len(code_parts) > 0 else 'CS'
                
                print(f"  ✓ Adding {code}: {c['Course_Name']} as RETAKE course")
                
                courses_to_offer.append({
                    'code': code,
                    'name': c['Course_Name'],
                    'credits': c['Credit_Hr'],
                    'semester': semester,
                    'prerequisite': c['Prerequisite'],
                    'department': department,
                    'type': 'retake'  # Prerequisite course to retake
                })
        
        conn.close()
        
        # Sort: current semester courses first, then retake courses
        courses_sorted = sorted(courses_to_offer, key=lambda x: (x['type'] != 'current', x['code']))
        
        print(f"\n🎯 FINAL OFFERING - Total courses: {len(courses_sorted)}")
        print(f"  📅 Current semester courses: {len([c for c in courses_sorted if c['type'] == 'current'])}")
        print(f"  ⚠️  Retake courses: {len([c for c in courses_sorted if c['type'] == 'retake'])}")
        print(f"\nCourses being offered:")
        for c in courses_sorted:
            badge = "📅 CURRENT" if c['type'] == 'current' else "⚠️  RETAKE"
            print(f"  {badge} | {c['code']}: {c['name']}")
        print(f"{'='*60}\n")
        
        # Extract degree info for template
        degree_code = None
        if len(roll_parts) >= 2:
            p1 = roll_parts[1]
            if '_' in p1:
                degree_code = p1.split('_')[1] if len(p1.split('_')) > 1 else None
        
        student_info = {
            'batch': batch,
            'degree_code': degree_code
        }
        
        return render_template(
            'course_registration.html',
            user=sid,
            user_name=student_row['Name'],
            student_info=student_info,
            current_semester=current_semester,
            courses=courses_sorted,
            enrolled_courses=enrolled,
            passed_courses=passed
        )
    
    except Exception as e:
        print(f"❌ Error loading course registration: {e}")
        import traceback
        traceback.print_exc()
        flash("Error loading course registration", "danger")
        return redirect(url_for('student_home'))


@app.route('/api/register-courses', methods=['POST'])
def register_courses():
    """Register student for selected courses"""
    if 'user' not in session:
        return {'success': False, 'error': 'Not logged in'}, 401
    
    sid = session['user']
    data = request.get_json()
    courses = data.get('courses', [])
    
    if not courses:
        return {'success': False, 'error': 'No courses selected'}, 400
    
    try:
        conn = sqlite3.connect('flake.db')
        cur = conn.cursor()
        
        # Delete existing enrollments for this student
        cur.execute("DELETE FROM enrollments WHERE Roll_No = ?", (sid,))
        
        # Insert new enrollments
        for course_code in courses:
            # Validate course exists
            cur.execute("SELECT Course_Code FROM courses WHERE Course_Code = ?", (course_code,))
            if not cur.fetchone():
                conn.close()
                return {'success': False, 'error': f'Invalid course code: {course_code}'}, 400
            
            cur.execute("INSERT INTO enrollments VALUES (?, ?)", (sid, course_code))
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': f'Successfully registered for {len(courses)} course(s)'
        }
    
    except Exception as e:
        print(f"Error registering courses: {e}")
        return {'success': False, 'error': 'Registration failed'}, 500
    


from datetime import datetime

# ============ STUDENT FEEDBACK ROUTES ============

@app.route('/student/feedback', methods=['GET'])
def student_feedback_form():
    if 'user' not in session:
        flash('Please login as student', 'error')
        return redirect(url_for('student_login'))
    
    roll_no = session['user']

    conn = sqlite3.connect('flake.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get student info
    cur.execute("""
        SELECT Roll_No, Name
        FROM students
        WHERE Roll_No = ?
    """, (roll_no,))
    student = cur.fetchone()

    if not student:
        conn.close()
        flash("Student not found!", "danger")
        return redirect(url_for('student_home'))


        # ✅ Get enrolled courses without duplicates
    cur.execute("""
        SELECT DISTINCT 
               e.Course_Code, 
               c.Course_Name, 
               c.Credit_Hr,
               t.Teacher_ID, 
               t.Name AS Teacher_Name,
               CASE 
                    WHEN f.id IS NOT NULL THEN 'Feedback Submitted'
                    ELSE 'Submit Feedback'
               END AS Status
        FROM enrollments e
        JOIN courses c ON e.Course_Code = c.Course_Code
        LEFT JOIN teacher_courses tc ON c.Course_Code = tc.Course_Code
        LEFT JOIN teachers t ON tc.Teacher_ID = t.Teacher_ID
        LEFT JOIN feedback f ON e.Roll_No = f.Roll_No AND e.Course_Code = f.Course_Code
        WHERE e.Roll_No = ?
        GROUP BY e.Course_Code
    """, (roll_no,))

    
    courses = cur.fetchall()
    conn.close()

    return render_template('student_feedback_list.html', courses=courses)




@app.route('/student/feedback/form/<course_code>', methods=['GET'])
def student_feedback_form_detail(course_code):
    if 'user' not in session:
        flash('Please login as student', 'error')
        return redirect(url_for('student_login'))
    
    roll_no = session['user']
    conn = get_db()

    # Prevent duplicate submission
    existing = conn.execute(
        'SELECT id FROM feedback WHERE Roll_No = ? AND Course_Code = ?',
        (roll_no, course_code)
    ).fetchone()

    if existing:
        flash('You have already submitted feedback for this course', 'warning')
        conn.close()
        return redirect(url_for('student_feedback_form'))

    # ✅ Correct query to fetch teacher of this course
    course_info = conn.execute("""
        SELECT c.Course_Code, c.Course_Name,
               t.Teacher_ID, t.Name AS Teacher_Name
        FROM enrollments e
        JOIN courses c ON e.Course_Code = c.Course_Code
        LEFT JOIN teacher_courses tc ON c.Course_Code = tc.Course_Code
        LEFT JOIN teachers t ON tc.Teacher_ID = t.Teacher_ID
        WHERE e.Roll_No = ? AND e.Course_Code = ?
    """, (roll_no, course_code)).fetchone()

    conn.close()

    if not course_info:
        flash("Course or teacher not found!", "danger")
        return redirect(url_for('student_feedback_form'))

    return render_template('student_feedback_form.html', course=course_info)



@app.route('/student/feedback/submit', methods=['POST'])
def submit_feedback():
    if 'user' not in session:
        return redirect(url_for('student_login'))
    
    roll_no = session['user']
    course_code = request.form.get('course_code')
    teacher_id = request.form.get('teacher_id')

    if not course_code or not teacher_id:
        flash("Invalid submission. Missing course or teacher information.", "danger")
        return redirect(url_for('student_feedback_form'))

    # Ratings (1-5)
    teaching_quality = request.form.get('teaching_quality')
    course_content = request.form.get('course_content')
    difficulty_level = request.form.get('difficulty_level')
    teacher_rating = request.form.get('teacher_rating')

    # MCQ fields
    classroom_env = request.form.get('classroom_environment')
    assessment = request.form.get('assessment_fairness')
    resources = request.form.get('learning_resources')
    organization = request.form.get('course_organization')

    # Suggestions
    suggestions = request.form.get('suggestions')

    conn = get_db()

    # Prevent duplicate
    existing = conn.execute(
        'SELECT id FROM feedback WHERE Roll_No = ? AND Course_Code = ?',
        (roll_no, course_code)
    ).fetchone()

    if existing:
        flash('You have already submitted feedback for this course', 'warning')
        conn.close()
        return redirect(url_for('student_feedback_form'))

    conn.execute("""
        INSERT INTO feedback (
            Roll_No, Course_Code, Teacher_ID,
            teaching_quality, course_content, difficulty_level, teacher_rating,
            classroom_environment, assessment_fairness, learning_resources,
            course_organization, suggestions, submitted_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        roll_no, course_code, teacher_id,
        teaching_quality, course_content, difficulty_level, teacher_rating,
        classroom_env, assessment, resources, organization,
        suggestions, datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ))

    conn.commit()
    conn.close()

    flash('Feedback submitted successfully!', 'success')
    return redirect(url_for('student_feedback_form'))



# ============ TEACHER FEEDBACK ROUTES ============

@app.route('/teacher/feedback', methods=['GET'])
def teacher_feedback_view():
    """Teachers view feedback for their courses only"""
    if 'user' not in session:
        flash('Please login as teacher', 'error')
        return redirect(url_for('teacher_login'))
    
    teacher_id = session['Teacher_ID']
    conn = get_db()
    
    # Get teacher's courses
    courses = conn.execute('''
        SELECT DISTINCT tc.Course_Code, c.Course_Name
        FROM teacher_courses tc
        JOIN courses c ON tc.Course_Code = c.Course_Code
        WHERE tc.Teacher_ID = ?
    ''', (teacher_id,)).fetchall()
    
    # Get feedback for selected course or all courses
    selected_course = request.args.get('course_code', 'all')
    
    if selected_course == 'all':
        feedbacks = conn.execute('''
            SELECT f.*, c.Course_Name
            FROM feedback f
            JOIN courses c ON f.Course_Code = c.Course_Code
            WHERE f.Teacher_ID = ?
            ORDER BY f.submitted_date DESC
        ''', (teacher_id,)).fetchall()
    else:
        feedbacks = conn.execute('''
            SELECT f.*, c.Course_Name
            FROM feedback f
            JOIN courses c ON f.Course_Code = c.Course_Code
            WHERE f.Teacher_ID = ? AND f.Course_Code = ?
            ORDER BY f.submitted_date DESC
        ''', (teacher_id, selected_course)).fetchall()
    
    # Calculate statistics
    if selected_course == 'all':
        stats = conn.execute('''
            SELECT 
                COUNT(*) as total_feedback,
                AVG(teacher_rating) as avg_teacher_rating,
                AVG(teaching_quality) as avg_teaching_quality,
                AVG(course_content) as avg_course_content
            FROM feedback
            WHERE Teacher_ID = ?
        ''', (teacher_id,)).fetchone()
    else:
        stats = conn.execute('''
            SELECT 
                COUNT(*) as total_feedback,
                AVG(teacher_rating) as avg_teacher_rating,
                AVG(teaching_quality) as avg_teaching_quality,
                AVG(course_content) as avg_course_content
            FROM feedback
            WHERE Teacher_ID = ? AND Course_Code = ?
        ''', (teacher_id, selected_course)).fetchone()
    
    conn.close()
    return render_template('teacher_feedback_view.html', 
                         courses=courses, 
                         feedbacks=feedbacks, 
                         selected_course=selected_course,
                         stats=stats)

# ============ ADMIN FEEDBACK ROUTES ============

@app.route('/admin/feedback', methods=['GET'])
def admin_feedback_view():
    """Admin views all feedback with teacher/course filter"""
    if 'user' not in session:
        flash('Please login as admin', 'error')
        return redirect(url_for('admin_login'))
    
    conn = get_db()
    
    # Get all teachers with their courses
    teacher_courses = conn.execute('''
        SELECT DISTINCT t.Teacher_ID, t.Name as Teacher_Name, 
               tc.Course_Code, c.Course_Name
        FROM teachers t
        JOIN teacher_courses tc ON t.Teacher_ID = tc.Teacher_ID
        JOIN courses c ON tc.Course_Code = c.Course_Code
        ORDER BY t.Name, c.Course_Code
    ''').fetchall()
    
    # Filter logic
    selected_teacher = request.args.get('teacher_id', 'all')
    selected_course = request.args.get('course_code', 'all')
    
    query = '''
        SELECT f.*, c.Course_Name, t.Name as Teacher_Name
        FROM feedback f
        JOIN courses c ON f.Course_Code = c.Course_Code
        JOIN teachers t ON f.Teacher_ID = t.Teacher_ID
        WHERE 1=1
    '''
    params = []
    
    if selected_teacher != 'all':
        query += ' AND f.Teacher_ID = ?'
        params.append(selected_teacher)
    
    if selected_course != 'all':
        query += ' AND f.Course_Code = ?'
        params.append(selected_course)
    
    query += ' ORDER BY f.submitted_date DESC'
    
    feedbacks = conn.execute(query, params).fetchall()
    
    # Overall statistics
    stats_query = 'SELECT COUNT(*) as total_feedback, AVG(teacher_rating) as avg_teacher_rating, AVG(teaching_quality) as avg_teaching_quality, COUNT(DISTINCT Teacher_ID) as teachers_count, COUNT(DISTINCT Course_Code) as courses_count FROM feedback WHERE 1=1'
    stats_params = []
    
    if selected_teacher != 'all':
        stats_query += ' AND Teacher_ID = ?'
        stats_params.append(selected_teacher)
    
    if selected_course != 'all':
        stats_query += ' AND Course_Code = ?'
        stats_params.append(selected_course)
    
    stats = conn.execute(stats_query, stats_params).fetchone()
    
    conn.close()
    return render_template('admin_feedback_view.html',
                         teacher_courses=teacher_courses,
                         feedbacks=feedbacks,
                         selected_teacher=selected_teacher,
                         selected_course=selected_course,
                         stats=stats)

# ========== MESSAGE HISTORY ==========
@app.route('/messages/<receiver_id>', methods=['GET', 'POST'])
def messages(receiver_id):
    if 'user' not in session:
        return jsonify([])

    sender_id = session['user']
    conn = sqlite3.connect('flake.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if request.method == 'GET':
        cur.execute("""
            SELECT sender_id, receiver_id, message, timestamp
            FROM messages
            WHERE (sender_id = ? AND receiver_id = ?)
               OR (sender_id = ? AND receiver_id = ?)
            ORDER BY timestamp ASC
        """, (sender_id, receiver_id, receiver_id, sender_id))
        msgs = [dict(row) for row in cur.fetchall()]
        conn.close()
        return jsonify(msgs)

    elif request.method == 'POST':
        data = request.get_json()
        message = data.get('text', '').strip()
        if not message:
            return jsonify({'status': 'error', 'message': 'Empty message'}), 400
        sender_type = session.get('user_type', 'student')
        receiver_type = data.get('receiver_type', 'teacher')

        cur.execute("""
            INSERT INTO messages (sender_type, sender_id, receiver_type, receiver_id, message, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (sender_type, sender_id, receiver_type, receiver_id, message, datetime.utcnow()))
        conn.commit()
        conn.close()
        return jsonify({'status': 'ok'})


# ========== SOCKET.IO EVENTS ==========

@socketio.on('join')
def on_join(data):
    user_id = data['user_id']
    join_room(user_id)
    print(f"{user_id} joined room")


@socketio.on('private_message')
def handle_send_message(data):
    sender_id = session.get('user')
    sender_type = data.get('user_type')
    receiver_id = data.get('receiver_id')
    receiver_type = data.get('receiver_type')
    message = data.get('message', '').strip()

    if not message:
        return

    conn = sqlite3.connect('flake.db')
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO messages (sender_type, sender_id, receiver_type, receiver_id, message, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (sender_type, sender_id, receiver_type, receiver_id, message, datetime.utcnow()))
    conn.commit()
    conn.close()

    msg_data = {
        'sender_id': sender_id,
        'receiver_id': receiver_id,
        'message': message,
        'timestamp': datetime.utcnow().isoformat()
    }

    emit('receive_message', msg_data, to=receiver_id)
    emit('receive_message', msg_data, to=sender_id)  # echo to sender too

    
# ------------------ RUN SERVER ------------------
if __name__ == '__main__':
    socketio.run(app, debug=True)

