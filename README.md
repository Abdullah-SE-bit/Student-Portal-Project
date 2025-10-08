# Student Portal (Flask + SQLite)

## Overview

This is a simple **Student Portal** built with **Python (Flask)** and **SQLite** as part of our Software Engineering course.
It demonstrates Scrum-based development, incremental sprints, and core portal features.

## Features

* Student Attendance Management

  * Teacher can add attendance (Present / Late / Absent)
  * Students can view attendance records
* SQLite Database to store records
* Flask backend with HTML/CSS frontend templates
* Ready to extend with Marks, Courses, and Announcements

## Tech Stack

* Python 3.x
* Flask (web framework)
* SQLite (database)
* HTML / CSS (frontend templates)

## Contributors

* M. Abdullah Adnan (Product Owner)
* Taha Sohail (Scrum Master)
* M. Shaheer (Developer)

## How to Run Locally

1. **Clone the repository**

   ```bash
   git clone https://github.com/Abdullah-SE-bit/Student-Portal-Project.git
   cd student-portal-Project
   ```

2. **Install dependencies**

   ```bash
   pip install flask
   ```

3. **Create the database (only first time)**

   ```bash
   python create_db.py
   ```

4. **Run the Flask app**

   ```bash
   python app.py
   ```

5. **Open in browser**

   ```
   http://127.0.0.1:5000/main
   ```

## Project Structure

```
student_portal/
│   app.py           # main Flask app
│   create_db.py     # script to create and seed SQLite DB
│   portal.db        # SQLite database file
│
├── templates/       # HTML pages
│   ├── attendance.html
│   └── add_attendance.html
│
├── static/          # CSS and assets
│   └── style.css
```
