CREATE DATABASE IF NOT EXISTS acadly;
USE acadly;

-- One row per registered student (max 48, roll_no auto-assigned 1..48)
CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  phone VARCHAR(15) NOT NULL,
  email VARCHAR(150) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  roll_no INT UNIQUE,
  required_attendance_pct INT NOT NULL DEFAULT 75,
  notif_idx INT NOT NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- The 8 subjects, shared by the whole class (class-wide timetable)
CREATE TABLE IF NOT EXISTS subjects (
  id INT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  credits INT NOT NULL DEFAULT 3
);

-- Attendance totals per student per subject
CREATE TABLE IF NOT EXISTS attendance (
  user_id INT NOT NULL,
  subject_id INT NOT NULL,
  held INT NOT NULL DEFAULT 0,
  attended INT NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id, subject_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);

-- Internal 1 / Internal 2 marks per student per subject (out of 20 each)
CREATE TABLE IF NOT EXISTS marks (
  user_id INT NOT NULL,
  subject_id INT NOT NULL,
  internal1 DECIMAL(5,2) NULL,
  internal2 DECIMAL(5,2) NULL,
  PRIMARY KEY (user_id, subject_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);

-- Current semester grade per student per subject, used for SGPA
CREATE TABLE IF NOT EXISTS grades (
  user_id INT NOT NULL,
  subject_id INT NOT NULL,
  grade VARCHAR(2) NOT NULL DEFAULT 'A',
  credits INT NOT NULL DEFAULT 3,
  PRIMARY KEY (user_id, subject_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);

-- Past semesters, used to compute CGPA
CREATE TABLE IF NOT EXISTS semesters (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  sgpa DECIMAL(4,2) NOT NULL,
  credits INT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Previous year papers / important questions, subject-wise, shared class-wide
CREATE TABLE IF NOT EXISTS questions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  subject_id INT NOT NULL,
  title VARCHAR(200) NOT NULL,
  link VARCHAR(500) NULL,
  added_by INT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
  FOREIGN KEY (added_by) REFERENCES users(id) ON DELETE SET NULL
);

INSERT IGNORE INTO subjects (id, name, credits) VALUES
  (1,'Subject 1',3),(2,'Subject 2',3),(3,'Subject 3',3),(4,'Subject 4',3),
  (5,'Subject 5',3),(6,'Subject 6',3),(7,'Subject 7',3),(8,'Subject 8',3);
