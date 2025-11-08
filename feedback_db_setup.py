import sqlite3

def create_feedback_table():
    conn = sqlite3.connect('flake.db')
    cur = conn.cursor()
    
    # Create feedback table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Roll_No TEXT NOT NULL,
            Course_Code TEXT NOT NULL,
            Teacher_ID TEXT NOT NULL,
            
            -- Ratings (1-5 scale)
            teaching_quality INTEGER,
            course_content INTEGER,
            difficulty_level INTEGER,
            teacher_rating INTEGER,
            
            -- MCQ Categories (Poor/Fair/Good/Excellent)
            classroom_environment TEXT,
            assessment_fairness TEXT,
            learning_resources TEXT,
            course_organization TEXT,
            
            -- Text feedback
            suggestions TEXT,
            
            -- Metadata
            submitted_date TEXT NOT NULL,
            
            FOREIGN KEY (Roll_No) REFERENCES students (Roll_No),
            FOREIGN KEY (Course_Code) REFERENCES courses (Course_Code),
            FOREIGN KEY (Teacher_ID) REFERENCES teachers (Teacher_ID)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Feedback table created successfully!")

if __name__ == "__main__":
    create_feedback_table()