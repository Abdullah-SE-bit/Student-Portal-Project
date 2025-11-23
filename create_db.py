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

    cur.execute('''CREATE TABLE IF NOT EXISTS marks (
        Roll_No TEXT, Name TEXT, Date TEXT, Course_Code TEXT,
        Heading TEXT, Total INTEGER, Obtained INTEGER
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS teacher_courses (
        Teacher_ID TEXT, Course_Code TEXT,
        FOREIGN KEY (Teacher_ID) REFERENCES teachers (Teacher_ID),
        FOREIGN KEY (Course_Code) REFERENCES courses (Course_Code)
    )''')

    # Add timetable table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS timetable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Teacher_ID TEXT NOT NULL,
        Course_Code TEXT NOT NULL,
        Day TEXT NOT NULL,
        Start_Time TEXT NOT NULL,
        End_Time TEXT NOT NULL,
        Room TEXT NOT NULL,
        Section TEXT NOT NULL,
        Class_Type TEXT NOT NULL,
        Week_Number INTEGER DEFAULT 1,
        FOREIGN KEY (Teacher_ID) REFERENCES teachers(Teacher_ID),
        FOREIGN KEY (Course_Code) REFERENCES courses(Course_Code)
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

    conn.commit()
    conn.close()
    print("✅ Database created and data imported successfully!")

if __name__ == "__main__":
    init_db()

