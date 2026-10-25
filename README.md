<<<<<<< HEAD
# Acadly — Full Backend (Node.js + Express + MySQL)

Everything now lives on a real server: login, attendance (with the
yes/no/swap check-in), internal marks, SGPA/CGPA, and the subject-wise
question bank. Nothing is stored in the browser except the login token.

## 1. Install prerequisites
- Node.js (v18 or newer)
- MySQL Server, running locally (or update `.env` to point at a remote one)

## 2. Set up the database
```bash
cp .env.example .env
```
Open `.env` and fill in your MySQL username/password and a random `JWT_SECRET`.

```bash
npm install
npm run initdb
```
This creates the database, all tables, and seeds the 8 subjects.

## 3. Start the server
```bash
npm start
```
You should see: `Acadly server running at http://localhost:3000`

## 4. Use it
Open **http://localhost:3000**. Sign up with name, phone, email and password —
you're automatically assigned the next free roll number (1 to 48; a 49th
signup is rejected since all slots are full). Everything you do afterwards —
marking attendance, entering internal marks, setting grades, adding past
semesters, adding question papers — is saved straight to MySQL.

## What's in the database
| Table | Holds |
|---|---|
| `users` | name, phone, email, password hash, roll number, required attendance %, notification position |
| `subjects` | the 8 class subjects (shared by everyone) |
| `attendance` | held/attended counts per student per subject |
| `marks` | Internal 1 / Internal 2 per student per subject |
| `grades` | current-semester grade + credits per student per subject (for SGPA) |
| `semesters` | past semesters' SGPA + credits per student (for CGPA) |
| `questions` | previous papers / important questions, subject-wise, shared by the class |

## API summary
- `POST /api/signup`, `POST /api/login`, `GET /api/me`
- `GET /api/subjects`, `PUT /api/subjects/:id`
- `GET /api/attendance`, `POST /api/attendance/mark`, `POST /api/attendance/swap`
- `GET /api/marks`, `PUT /api/marks/:subjectId`
- `GET /api/grades`, `PUT /api/grades/:subjectId`
- `GET /api/semesters`, `POST /api/semesters`, `DELETE /api/semesters/:id`
- `GET /api/questions`, `POST /api/questions`, `DELETE /api/questions/:id`
- `PUT /api/settings` (required attendance %)

All routes except signup/login require `Authorization: Bearer <token>`,
which the frontend handles automatically after you log in.

## Note on the hosted preview link
The Claude artifact link from earlier is a separate, browser-only demo — a
hosted preview page can't reach a MySQL server on your computer. This project
is the real one; run it locally as above.
=======
# Acadly
a student-focused platform to manage academics, assignments, and study resources in one place.
>>>>>>> 84c095c5e6b921526d5f0c663f7385aba4825f2e
