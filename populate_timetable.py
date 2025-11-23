"""
Populate timetable data for all teachers
Run this after creating the database
"""

import sqlite3
import random

def populate_timetable():
    conn = sqlite3.connect('flake.db')
    cur = conn.cursor()
    
    # Clear existing data
    cur.execute("DELETE FROM timetable")
    
    # Get all teachers with their courses
    cur.execute("""
        SELECT Teacher_ID, Course_Code, Department, Name 
        FROM teachers 
        ORDER BY Teacher_ID
    """)
    teachers = cur.fetchall()
    
    # Time slots
    time_slots = [
        ('09:00', '10:30'),
        ('11:00', '12:30'),
        ('14:00', '15:30'),
        ('16:00', '17:30'),
    ]
    
    # Rooms
    lecture_rooms = [
        'Room 201', 'Room 202', 'Room 203', 'Room 204', 'Room 205',
        'Room 301', 'Room 302', 'Room 303', 'Room 304', 'Room 305',
        'Room 401', 'Room 402', 'Room 403', 'Room 501', 'Room 502'
    ]
    
    lab_rooms = [
        'Lab 1', 'Lab 2', 'Lab 3', 'Lab 4', 
        'Lab 5', 'Lab 6', 'Lab 7', 'Lab 8'
    ]
    
    # Days
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    
    # Sections
    sections = ['Section A', 'Section B', 'Section C']
    
    # Track used slots to avoid conflicts
    used_slots = set()
    
    timetable_data = []
    
    for teacher_id, course_code, department, name in teachers:
        # Determine if lab course
        is_lab = course_code.startswith('CL-')
        
        # Assign 2-3 classes per teacher
        num_classes = random.randint(2, 3)
        
        for i in range(num_classes):
            attempts = 0
            while attempts < 50:  # Max attempts to find a slot
                day = random.choice(days)
                start_time, end_time = random.choice(time_slots)
                section = random.choice(sections)
                
                # Choose room
                if is_lab:
                    room = random.choice(lab_rooms)
                    class_type = 'Lab'
                else:
                    room = random.choice(lecture_rooms)
                    # Vary class types
                    class_type = random.choice(['Lecture', 'Lecture', 'Tutorial'])
                
                # Create unique key
                slot_key = f"{teacher_id}_{day}_{start_time}"
                
                if slot_key not in used_slots:
                    used_slots.add(slot_key)
                    
                    timetable_data.append((
                        teacher_id,
                        course_code,
                        day,
                        start_time,
                        end_time,
                        room,
                        section,
                        class_type,
                        1  # Week number
                    ))
                    break
                
                attempts += 1
    
    # Insert all data
    cur.executemany('''
        INSERT INTO timetable 
        (Teacher_ID, Course_Code, Day, Start_Time, End_Time, Room, Section, Class_Type, Week_Number)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', timetable_data)
    
    conn.commit()
    
    # Show statistics
    cur.execute("SELECT COUNT(*) FROM timetable")
    total_classes = cur.fetchone()[0]
    
    print(f"\n{'='*60}")
    print(f"✅ TIMETABLE POPULATED SUCCESSFULLY!")
    print(f"{'='*60}")
    print(f"📊 Statistics:")
    print(f"   - Total Teachers: {len(teachers)}")
    print(f"   - Total Classes Scheduled: {total_classes}")
    print(f"   - Average Classes per Teacher: {total_classes / len(teachers):.1f}")
    print(f"{'='*60}\n")
    
    # Show sample data
    print("📋 Sample Schedule (First 5 entries):")
    cur.execute("""
        SELECT t.Teacher_ID, te.Name, t.Course_Code, t.Day, 
               t.Start_Time, t.End_Time, t.Room, t.Section, t.Class_Type
        FROM timetable t
        JOIN teachers te ON t.Teacher_ID = te.Teacher_ID
        LIMIT 5
    """)
    
    for row in cur.fetchall():
        print(f"   {row[1][:20]:20} | {row[2]:10} | {row[3]:10} | {row[4]}-{row[5]} | {row[6]:10} | {row[7]:10} | {row[8]}")
    
    print(f"\n{'='*60}\n")
    
    conn.close()

if __name__ == "__main__":
    populate_timetable()