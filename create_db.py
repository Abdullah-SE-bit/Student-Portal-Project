import sqlite3
import pandas as pd
import re
import os

def extract_last_digits(value):
    """Extract last numeric part from an ID like F-22_SE-A-3001 -> 3001"""
    matches = re.findall(r'\d+', str(value))
    return matches[-1] if matches else value

def init_db():
    conn = sqlite3.connect('flake.db')
    cur = conn.cursor()

    # ---- TABLE CREATION ----
    cur.execute('''CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL  
    )''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS students (
        Roll_No TEXT PRIMARY KEY,
        Name TEXT,
        Gender TEXT,
        DOB TEXT,
        CNIC TEXT,
        Email TEXT,
        Mobile_No TEXT,
        Current_Address TEXT,
        Permanent_Address TEXT,
        Home_Phone TEXT,
        Postal_Code TEXT,
        Password TEXT
    )
''')


    cur.execute('''
        CREATE TABLE IF NOT EXISTS teachers (
            Teacher_ID TEXT PRIMARY KEY,
            Name TEXT,
            Gender TEXT,
            DOB TEXT,
            CNIC TEXT,
            Email TEXT,
            Mobile_No TEXT,
            Current_Address TEXT,
            Permanent_Address TEXT,
            Home_Phone TEXT,
            Postal_Code TEXT,
            Department TEXT,
            Course_Code TEXT,
            Course_Name TEXT
        )
    ''')

    cur.execute('''CREATE TABLE IF NOT EXISTS courses (
        Course_Code TEXT PRIMARY KEY,
        Course_Name TEXT, Credit_Hr INTEGER, Prerequisite TEXT
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS enrollments (
        Roll_No TEXT, Course_Code TEXT,
        FOREIGN KEY (Roll_No) REFERENCES students (Roll_No),
        FOREIGN KEY (Course_Code) REFERENCES courses (Course_Code)
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS passed_courses (
        Roll_No TEXT, Course_Code TEXT, Grade TEXT,
        FOREIGN KEY (Roll_No) REFERENCES students (Roll_No),
        FOREIGN KEY (Course_Code) REFERENCES courses (Course_Code)
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS attendance (
        Roll_No TEXT, Name TEXT, Date TEXT, Course_Code TEXT,
        Class_No INTEGER, Attendance TEXT
    )''')

    # --- Replace old marks table with these new tables ---
    cur.execute('''DROP TABLE IF EXISTS marks''')  # remove old table if present

    cur.execute('''
    CREATE TABLE IF NOT EXISTS mark_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Course_Code TEXT NOT NULL,
        Category TEXT NOT NULL,       -- Assignment, Quiz, Sessional-I, etc.
        Item_No INTEGER DEFAULT 1,    -- e.g., Quiz 1 -> 1
        Title TEXT,                   -- user-friendly name (e.g., "Quiz 1")
        Total INTEGER NOT NULL,       -- total marks for this item
        Teacher_ID TEXT,              -- who created it
        Created_Date TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS student_marks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mark_item_id INTEGER NOT NULL,
        Roll_No TEXT NOT NULL,
        Obtained INTEGER,
        FOREIGN KEY(mark_item_id) REFERENCES mark_items(id),
        FOREIGN KEY(Roll_No) REFERENCES students(Roll_No)
    )
    ''')


    cur.execute('''CREATE TABLE IF NOT EXISTS teacher_courses (
        Teacher_ID TEXT, Course_Code TEXT,
        FOREIGN KEY (Teacher_ID) REFERENCES teachers (Teacher_ID),
        FOREIGN KEY (Course_Code) REFERENCES courses (Course_Code)
    )''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Roll_No TEXT,
        Course_Code TEXT,
        Teacher_ID TEXT,
        teaching_quality INTEGER,
        course_content INTEGER,
        difficulty_level INTEGER,
        teacher_rating INTEGER,
        classroom_environment TEXT,
        assessment_fairness TEXT,
        learning_resources TEXT,
        course_organization TEXT,
        suggestions TEXT,
        submitted_date TEXT,
        FOREIGN KEY (Roll_No) REFERENCES students(Roll_No),
        FOREIGN KEY (Course_Code) REFERENCES courses(Course_Code),
        FOREIGN KEY (Teacher_ID) REFERENCES teachers(Teacher_ID)
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_type TEXT CHECK(sender_type IN ('student', 'teacher', 'admin')) NOT NULL,
        sender_id TEXT NOT NULL,
        receiver_type TEXT CHECK(receiver_type IN ('student', 'teacher', 'admin')) NOT NULL,
        receiver_id TEXT NOT NULL,
        message TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        is_read INTEGER DEFAULT 0,
    
        -- References (logical only, not enforced by FK to avoid schema break)
        FOREIGN KEY (sender_id) REFERENCES students (Roll_No),
        FOREIGN KEY (receiver_id) REFERENCES students (Roll_No)
    )
    ''')


    # ---- ADMIN DEFAULT ----
    admin_id = "A123"
    cur.execute("INSERT OR IGNORE INTO admins (admin_id, password) VALUES (?, ?)", (admin_id, admin_id))

    # ---- LOAD EXCEL FILES ----
    data_path = "data"
    if os.path.exists(os.path.join(data_path, "students.xlsx")):
        students_df = pd.read_excel(os.path.join(data_path, "students.xlsx"))
        for _, r in students_df.iterrows():
            cur.execute('''INSERT OR IGNORE INTO students VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (r['Roll_No'], r['Name'], r['Gender'], r['DOB'], r['CNIC'], r['Email'], r['Mobile_No'],
                 r['Current_Address'], r['Permanent_Address'], r['Home_Phone'], r['Postal_Code'],
                 extract_last_digits(r['Roll_No'])))

    if os.path.exists(os.path.join(data_path, "teachers.xlsx")):
        teachers_df = pd.read_excel(os.path.join(data_path, "teachers.xlsx"))
    for _, r in teachers_df.iterrows():
        cur.execute('''INSERT OR IGNORE INTO teachers 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                r['Teacher_ID'], r['Name'], r['Gender'], r['DOB'], r['CNIC'], r['Email'], r['Mobile_No'],
                r['Current_Address'], r['Permanent_Address'], r['Home_Phone'], r['Postal_Code'],
                r['Department'], r['Course_Code'], r['Course_Name']
            ))
    # ✅ Insert teacher-course mappings automatically
    cur.execute('SELECT Teacher_ID, Course_Code FROM teachers')
    teacher_course_rows = cur.fetchall()

    for row in teacher_course_rows:
        cur.execute('INSERT OR IGNORE INTO teacher_courses (Teacher_ID, Course_Code) VALUES (?, ?)', row)




    if os.path.exists(os.path.join(data_path, "courses.xlsx")):
        df = pd.read_excel(os.path.join(data_path, "courses.xlsx"))
        for _, r in df.iterrows():
            cur.execute("INSERT OR IGNORE INTO courses VALUES (?, ?, ?, ?)",
                        (r['Course_Code'], r['Course_Name'], r['Credit_Hr'], r['Prerequsite']))

    if os.path.exists(os.path.join(data_path, "enrollments.xlsx")):
        df = pd.read_excel(os.path.join(data_path, "enrollments.xlsx"))
        for _, r in df.iterrows():
            cur.execute("INSERT OR IGNORE INTO enrollments VALUES (?, ?)",
                        (r['Roll_No'], r['Course_Code']))

    if os.path.exists(os.path.join(data_path, "passed_courses.xlsx")):
        df = pd.read_excel(os.path.join(data_path, "passed_courses.xlsx"))
        for _, r in df.iterrows():
            cur.execute("INSERT OR IGNORE INTO passed_courses VALUES (?, ?, ?)",
                        (r['Roll_No'], r['Course_Code'], r['Grade']))

    if os.path.exists(os.path.join(data_path, "attendance.xlsx")):
        df = pd.read_excel(os.path.join(data_path, "attendance.xlsx"))
        for _, r in df.iterrows():
            cur.execute("INSERT OR IGNORE INTO attendance VALUES (?, ?, ?, ?, ?, ?)",
                        (r['Roll_No'], r['Name'], str(r['Date']), r['Course_Code'], r['Class_No'], r['Attendance']))

    if os.path.exists(os.path.join(data_path, "marks.xlsx")):
        df = pd.read_excel(os.path.join(data_path, "marks.xlsx"))
        for _, r in df.iterrows():
            cur.execute("INSERT OR IGNORE INTO marks VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (r['Roll_No'], r['Name'], r['Date'], r['Course_Code'], r['Heading'], r['Total'], r['Obtained']))
            
    

    cur.execute('''
    CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_type TEXT CHECK(sender_type IN ('student', 'teacher', 'admin')) NOT NULL,
    sender_id TEXT NOT NULL,
    receiver_type TEXT CHECK(receiver_type IN ('student', 'teacher', 'admin')) NOT NULL,
    receiver_id TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_read INTEGER DEFAULT 0
    )
''')


    conn.commit()
    conn.close()
    print("✅ Database created and data imported successfully!")

if __name__ == "__main__":
    init_db()
