"""python manage.py load_5th_sem  -> subjects + weekly timetable of 5th sem AI&DS (AY 2026-27)."""
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Subject, TimetableSlot

# code, short, name, staff, credits, is_lab   (credits are NOT on the sheet: check your scheme)
SUBJECTS = [
    ("BCS501", "SEPM", "Software Engineering & Project Management", "Mrs. Rojashree", 3, False),
    ("BCS502", "CN", "Computer Networks", "Mr. Gopinath C B", 4, False),
    ("BCS503", "TOC", "Theory of Computation", "Mr. Sanjeev Jadhav", 4, False),
    ("BCS515D", "DSS", "Distributed Systems", "Mr. Guruprasad K M", 3, False),
    ("BRMK557", "RM", "Research Methodology and IPR", "Mrs. Shruthi M R", 3, False),
    ("BCS508", "EWS", "Environmental Studies & E-Waste Management", "Mrs. Madhu K M", 1, False),
    ("BAIL504", "DV Lab", "Data Visualization Laboratory", "Mr. Gopinath C B", 1, True),
    ("BAD586", "Mini Project", "Mini Project", "Mrs. Shruthi M R", 2, True),
    ("BPEK559", "PE", "Physical Education (Sports and Athletics)", "Mr. Ganesh H A", 0, False),
]
# (day 0=Mon, start_col, end_col, subject short or label, batch)  - columns follow settings.PERIODS
GRID = [
    (0, 0, 0, "DSS", ""), (0, 1, 1, "RM", ""), (0, 3, 3, "SEPM", ""), (0, 4, 4, "EWS", ""),
    (0, 6, 7, "CN", ""), (0, 8, 8, "act:Library", ""),
    (1, 0, 0, "CN", ""), (1, 1, 1, "SEPM", ""), (1, 3, 3, "TOC", ""), (1, 4, 4, "EWS", ""),
    (1, 6, 7, "DV Lab", "B1"), (1, 6, 7, "Mini Project", "B2"), (1, 8, 8, "act:Tutorial", ""),
    (2, 0, 0, "TOC", ""), (2, 1, 1, "RM", ""), (2, 3, 3, "CN", ""), (2, 4, 4, "DSS", ""),
    (2, 6, 8, "act:Department Activities", ""),
    (3, 0, 0, "SEPM", ""), (3, 1, 1, "DSS", ""), (3, 3, 3, "RM", ""), (3, 4, 4, "TOC", ""),
    (3, 6, 7, "Mini Project", ""), (3, 8, 8, "act:Student Counselling", ""),
    (4, 0, 0, "RM", ""), (4, 1, 1, "TOC", ""),
    (4, 3, 4, "DV Lab", "B2"), (4, 3, 4, "Mini Project", "B1"),
    (4, 6, 6, "CN", ""), (4, 7, 8, "act:Skill Laboratory", ""),
    (5, 0, 0, "RM", ""), (5, 1, 1, "TOC", ""), (5, 3, 3, "SEPM", ""), (5, 4, 4, "CN", ""),
    (5, 6, 8, "PE", ""),
]


class Command(BaseCommand):
    help = "Load the 5th semester subjects and timetable (safe to re-run)."

    @transaction.atomic
    def handle(self, *args, **opts):
        subs = {}
        for code, short, name, staff, credits, lab in SUBJECTS:
            s, _ = Subject.objects.update_or_create(
                code=code, defaults=dict(short=short, name=name, staff=staff, is_lab=lab,
                                         credits=credits))
            subs[short] = s
        TimetableSlot.objects.all().delete()
        for day, a, b, what, batch in GRID:
            if what.startswith("act:"):
                TimetableSlot.objects.create(day=day, start_col=a, end_col=b, label=what[4:], batch=batch)
            else:
                TimetableSlot.objects.create(day=day, start_col=a, end_col=b, subject=subs[what], batch=batch)
        self.stdout.write(self.style.SUCCESS(
            f"{len(SUBJECTS)} subjects and {len(GRID)} timetable slots loaded."))
