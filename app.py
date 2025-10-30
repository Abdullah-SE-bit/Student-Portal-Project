from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime
import re
from flask_socketio import SocketIO

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
            # Extract numeric digits and take the last 4 as password
            real_pass = ''.join([ch for ch in tid if ch.isdigit()])[-4:]
            if password == real_pass:
                session['user'] = tid
                session['user_name'] = teacher[0]  # store teacher name
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

    # --- Extract Department and Batch from Roll_No ---
    # Example: M-22_SE-A-3001 -> parts = ['M', '22_SE', 'A', '3001'] OR if your format uses underscores differently:
    # attempt robust parsing: find the part that contains department (like 'SE') and the batch (two-digit year)
    parts = roll_no.split('-')

    # Try to get batch (the commonly second hyphen-part contains batch or batch may be embedded)
    # The earlier format you use: M-22_SE-A-3001  -> parts[1] is "22_SE"
    batch = None
    dept = None
    section = None

    if len(parts) >= 2:
        # parts[1] may contain "22_SE" or "22" — handle both
        p1 = parts[1]
        # if there's an underscore, split
        if '_' in p1:
            sub = p1.split('_')
            # expect sub like ['22', 'SE']
            if len(sub) >= 1:
                batch = sub[0]
            if len(sub) >= 2:
                dept = sub[1]
        else:
            # no underscore: maybe batch alone, next part contains dept
            batch = p1
            if len(parts) >= 3:
                # parts[2] could be "SE" or "SE-A" — try to extract dept
                if '_' in parts[2]:
                    dept = parts[2].split('_')[0]
                else:
                    # if parts[2] like "SE" or "SE-A" (take letters before non-letters)
                    dept = ''.join([ch for ch in parts[2] if ch.isalpha()])

    # fallback: if still not found try to locate a two-digit batch and an uppercase dept token anywhere
    if not batch or not dept:
        tokens = re.split(r'[_\-]', roll_no)
        for t in tokens:
            if not batch and re.fullmatch(r'\d{2}', t):
                batch = t
            if not dept and re.fullmatch(r'[A-Za-z]{2,}', t):
                # choose first alphabetic token that looks like dept
                dept = t

    # section extraction (if exists in a part like 'A' or 'SE-A')
    if len(parts) >= 3:
        # look for single-letter section in parts
        sec_candidate = parts[2]
        if '-' in sec_candidate or '_' in sec_candidate:
            # strip non-letters
            section = ''.join([ch for ch in sec_candidate if ch.isalpha()])
        else:
            section = ''.join([ch for ch in sec_candidate if ch.isalpha()])

    # Safety defaults
    if not batch:
        batch = ''   # will map to None later
    if not dept:
        dept = ''    # empty dept => no teachers returned

    # --- Map batch -> semester (your mapping) ---
    batch_to_sem = {
        '22': 7,
        '23': 5,
        '24': 3,
        '25': 1
    }
    sem = batch_to_sem.get(batch, None)

    # If semester cannot be determined, show no teachers (or fallback to dept-only if desired)
    if sem is None:
        # optional: fallback to dept-only lookup. For now block and return empty contacts.
        contacts = []
        conn.close()
        return render_template('inbox_S.html', user=sid, user_name=stu_name, contacts=contacts)

    # --- Convert semester -> course-code digit ---
    # special rule you gave: semester 1 is encoded as '0' in Course_Code; others use their number char
    if sem == 1:
        code_digit = '0'
    else:
        code_digit = str(sem)

    # --- Query teachers filtered by department and course-code digit ---
    # We'll find the character immediately after the hyphen in Course_Code and match it to code_digit
    # Use SQLite substr + instr to extract the char after '-'
    cur.execute("""
        SELECT DISTINCT t.Teacher_ID, t.Name, t.Course_Code, t.Course_Name
        FROM teachers t
        WHERE t.Department = ?
          AND substr(t.Course_Code, instr(t.Course_Code, '-') + 1, 1) = ?
    """, (dept, code_digit))

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
    1. First, offer courses for current semester where prerequisites are met
    2. If prerequisite not met, offer the prerequisite course for retake
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
        student_info = extract_student_info(student_row['Roll_No'])
        batch = student_info['batch']
        degree_code = student_info['degree_code']
        
        # Get current semester based on batch
        current_semester = batch_to_semester(batch)
        
        if current_semester is None:
            conn.close()
            flash("Unable to determine your current semester", "danger")
            return redirect(url_for('student_home'))
        
        # Convert semester to course code digit (following app.py logic)
        code_digit = semester_to_course_digit(current_semester)
        
        # Get all courses for this semester
        cur.execute("""
            SELECT Course_Code, Course_Name, Credit_Hr, Prerequisite
            FROM courses
            WHERE substr(Course_Code, instr(Course_Code, '-') + 1, 1) = ?
            ORDER BY Course_Code
        """, (code_digit,))
        
        current_sem_courses_raw = cur.fetchall()
        
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
        
        # Now build the courses list with intelligent offering logic
        courses_to_offer = []
        prerequisite_courses_to_retake = set()
        
        for c in current_sem_courses_raw:
            code = c['Course_Code']
            prerequisite = c['Prerequisite']
            
            # Check if student has passed the prerequisite
            prerequisite_met = (not prerequisite or prerequisite in passed)
            
            if not prerequisite_met:
                # Prerequisite NOT met - add the prerequisite course to retake list
                if prerequisite:
                    prerequisite_courses_to_retake.add(prerequisite)
            else:
                # Prerequisite met - add this course to current semester offerings
                code_parts = code.split('-')
                sem_digit = code_parts[1][0] if len(code_parts) > 1 else '0'
                
                if sem_digit == '0':
                    semester = 1
                else:
                    semester = int(sem_digit) if sem_digit.isdigit() else 1
                
                department = code_parts[0] if len(code_parts) > 0 else 'CS'
                
                courses_to_offer.append({
                    'code': code,
                    'name': c['Course_Name'],
                    'credits': c['Credit_Hr'],
                    'semester': semester,
                    'prerequisite': prerequisite,
                    'department': department,
                    'type': 'current'  # Current semester course
                })
        
        # Now add prerequisite courses that need to be retaken
        if prerequisite_courses_to_retake:
            cur.execute("""
                SELECT Course_Code, Course_Name, Credit_Hr, Prerequisite
                FROM courses
                WHERE Course_Code IN ({})
            """.format(','.join(['?' for _ in prerequisite_courses_to_retake])),
                tuple(prerequisite_courses_to_retake))
            
            prereq_courses_raw = cur.fetchall()
            
            for c in prereq_courses_raw:
                code = c['Course_Code']
                code_parts = code.split('-')
                sem_digit = code_parts[1][0] if len(code_parts) > 1 else '0'
                
                if sem_digit == '0':
                    semester = 1
                else:
                    semester = int(sem_digit) if sem_digit.isdigit() else 1
                
                department = code_parts[0] if len(code_parts) > 0 else 'CS'
                
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
        print(f"Error loading course registration: {e}")
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
    
# ------------------ RUN SERVER ------------------
if __name__ == '__main__':
    socketio.run(app, debug=True)


