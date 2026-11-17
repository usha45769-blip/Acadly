# Acadly: Student Academic Companion

One dashboard for attendance, timetable, internal marks, SGPA/CGPA and study material,
with machine-learning prediction of future attendance.

> Mini project, Department of Artificial Intelligence and Data Science, Rajeev Institute of Technology, Hassan (VTU, Belagavi).

## Features

| Feature | How it works |
|---|---|
| Timetable from a photo | OpenCV finds the table lines, Tesseract reads each cell, a review grid lets you fix mistakes before saving |
| Attendance | Attendance % = attended / held x 100, per subject, with an opening balance plus daily marking |
| 85% threshold analysis | Shows classes you can still miss, or how many in a row you must attend to recover |
| Future attendance prediction | Pandas builds a history table, scikit-learn logistic regression scores every remaining class on the timetable (falls back to your current rate when there is little data) |
| Internal marks | Internal 1 and 2 (out of 20) with total and average |
| SGPA / CGPA | VTU 10-point scale, credit-weighted, past semesters supported |
| Study library | Textbooks, notes, question papers, assignments and study material, grouped subject-wise |

## Tech stack

Python, Django, HTML/CSS/JavaScript, MySQL, Pandas, NumPy, Scikit-learn, OpenCV, Tesseract OCR, Git/GitHub, VS Code.

## Setup

1. Install Python 3.10+, MySQL and the **Tesseract OCR** program
   (Windows installer: https://github.com/UB-Mannheim/tesseract/wiki; Ubuntu: `sudo apt install tesseract-ocr`).
2. Create the database: `CREATE DATABASE acadly CHARACTER SET utf8mb4;`
3. Then:

```bash
git clone https://github.com/usha45769-blip/Acadly.git
cd Acadly
python -m venv venv
venv\Scripts\activate            # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env           # Mac/Linux: cp .env.example .env   then fill in the values
python manage.py migrate
python manage.py load_5th_sem    # subjects + timetable for 5th sem AI&DS
python manage.py createsuperuser # this account can upload and edit the timetable
python manage.py runserver
```

Open http://127.0.0.1:8000/. For a quick try without MySQL, set `DB_ENGINE=sqlite` in `.env`.
`pip install mysqlclient` needs build tools on some systems; see the mysqlclient docs if it fails.

Run the calculation tests (no database needed): `python -m unittest core.tests`

## Notes

* Subject credits in `load_5th_sem` are not printed on the timetable sheet. Check them against your scheme and edit in `/admin/` or on the SGPA page.
* Only staff accounts can replace the class timetable. Everyone else can view it.
* Semester dates and holidays are in `acadly/settings.py` (`SEMESTER_START`, `SEMESTER_END`, `HOLIDAYS`).

## Contributing

1. `git checkout main` then `git pull origin main`
2. `git checkout -b feature/your-feature`
3. Commit with clear messages, `git push origin feature/your-feature`
4. Open a Pull Request into `main`. Do not push directly to `main`.
