# Acadly: Student Academic Companion

An integrated platform for academic management and performance tracking.

Students usually juggle separate apps for attendance, timetables, notes, question papers, and SGPA/CGPA calculation. Acadly brings all of these into one dashboard and uses Machine Learning to predict future attendance.

> Mini project, Department of Artificial Intelligence and Data Science, Rajeev Institute of Technology, Hassan (VTU, Belagavi).

## Features

- Student registration and login
- Timetable upload (image or document) with OCR-based extraction of subjects, days, and periods
- Subject-wise attendance tracking and percentage calculation
- 85% attendance threshold check
- ML-based future attendance prediction
- Internal marks entry with automatic total and average
- Subject-wise storage of textbooks, notes, question papers, assignments, and study materials
- SGPA and CGPA calculators
- Centralized dashboard

Attendance % = (Classes Attended / Total Classes) x 100

## Tech Stack

| Area | Tools |
|---|---|
| Backend | Python, Django |
| Frontend | HTML, CSS, JavaScript |
| Database | MySQL |
| Data and ML | Pandas, NumPy, Scikit-learn |
| Image processing | OpenCV, OCR |
| Dev tools | VS Code, Git, GitHub |

## Getting Started

### Prerequisites
- Python 3.10+
- MySQL
- Git

### Setup

```bash
git clone https://github.com/usha45769-blip/Acadly.git
cd Acadly

python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Mac/Linux

pip install -r requirements.txt
```

Create a `.env` file by copying `.env.example`, then fill in your own values (secret key, database name, user, password). Never commit `.env`.

```bash
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000/ in your browser.


## Contributing

1. Pull the latest code: `git checkout main` then `git pull origin main`
2. Create your own branch: `git checkout -b feature/your-feature`
3. Commit with clear messages, then push: `git push origin feature/your-feature`
4. Open a Pull Request into `main`

Do not push directly to `main`.

## References

- [Python](https://www.python.org/)
- [Django](https://www.djangoproject.com/)
- [Scikit-learn](https://scikit-learn.org/)
- [Pandas](https://pandas.pydata.org/)
- [MySQL](https://www.mysql.com/)
- [OpenCV](https://opencv.org/)