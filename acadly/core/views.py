from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import RegisterForm, ResourceForm, TimetableUploadForm
from .models import (DAY_CHOICES, AttendanceBase, AttendanceRecord, Grade, Mark, Resource,
                     Semester, Student, Subject, TimetableSlot, TimetableUpload)
from .services.attendance import attendance_stats
from .services.gpa import GRADE_POINTS, cgpa, sgpa
from .services.ml import predict_attendance

staff_required = user_passes_test(lambda u: u.is_staff)
ACTIVITIES = ["Library", "Tutorial", "Department Activities", "Student Counselling", "Skill Laboratory"]


# ---------------------------------------------------------------- helpers
def get_student(request):
    student, _ = Student.objects.get_or_create(user=request.user, defaults={"phone": ""})
    return student


def slots_for(student, weekday):
    return (TimetableSlot.objects.filter(day=weekday).exclude(subject=None)
            .filter(Q(batch="") | Q(batch=student.batch)).select_related("subject"))


def attendance_summary(student):
    """Per-subject stats + ML prediction for the dashboard."""
    threshold = settings.ATTENDANCE_THRESHOLD
    today = date.today()
    subjects = list(Subject.objects.all())
    bases = {b.subject_id: b for b in AttendanceBase.objects.filter(student=student)}
    records = list(AttendanceRecord.objects.filter(student=student).select_related("slot"))
    done_today = {(r.subject_id, r.slot_id) for r in records if r.date == today}

    # remaining classes from today to the end of the semester, from the timetable
    future = {s.id: [] for s in subjects}
    by_day = {wd: list(slots_for(student, wd)) for wd in range(6)}   # one query per weekday, not per date
    d = today
    while d <= settings.SEMESTER_END:
        if d.weekday() < 6 and d not in settings.HOLIDAYS:
            for slot in by_day[d.weekday()]:
                if d == today and (slot.subject_id, slot.id) in done_today:
                    continue
                future[slot.subject_id].append({"weekday": d.weekday(), "hour": int(slot.start_time[:2])})
        d += timedelta(days=1)

    out = []
    for s in subjects:
        b = bases.get(s.id)
        bh, ba = (b.held, b.attended) if b else (0, 0)
        hist = [{"date": r.date, "hour": int(r.slot.start_time[:2]) if r.slot else 10,
                 "present": int(r.present)} for r in records if r.subject_id == s.id]
        stats = attendance_stats(bh + len(hist), ba + sum(h["present"] for h in hist), threshold)
        pred = predict_attendance(hist, bh, ba, future[s.id], threshold) if stats["held"] else None
        out.append({"subject": s, "stats": stats, "pred": pred})
    return out


# ---------------------------------------------------------------- auth
def register(request):
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        cd = form.cleaned_data
        for _ in range(3):  # retry if two people grab the same roll number at once
            try:
                with transaction.atomic():
                    taken = set(Student.objects.exclude(roll_no=None).values_list("roll_no", flat=True))
                    roll = next((i for i in range(1, settings.MAX_STUDENTS + 1) if i not in taken), None)
                    if roll is None:
                        form.add_error(None, f"All {settings.MAX_STUDENTS} student slots are taken.")
                        break
                    user = User.objects.create_user(username=cd["email"], email=cd["email"],
                                                    password=cd["password"], first_name=cd["name"].strip())
                    Student.objects.create(user=user, phone=cd["phone"], roll_no=roll, batch=cd["batch"])
                login(request, user)
                return redirect("attendance_base")
            except IntegrityError:
                continue
    return render(request, "core/register.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("login")


# ---------------------------------------------------------------- dashboard + attendance
@login_required
def dashboard(request):
    student = get_student(request)
    today = date.today()
    today_slots = list(slots_for(student, today.weekday())) if today.weekday() < 6 else []
    marked = {(r.slot_id): r.present for r in AttendanceRecord.objects.filter(student=student, date=today)}
    for sl in today_slots:
        sl.mark = marked.get(sl.id)
    summary = attendance_summary(student)
    tracked = [x for x in summary if x["stats"]["held"]]
    low = [x for x in tracked if x["stats"]["status"] == "short"]
    return render(request, "core/dashboard.html", {
        "student": student, "summary": summary, "today_slots": today_slots, "today": today,
        "low": low, "threshold": settings.ATTENDANCE_THRESHOLD,
        "needs_setup": not tracked,
    })


@login_required
@require_POST
def attendance_mark(request):
    student = get_student(request)
    slot = get_object_or_404(slots_for(student, date.today().weekday()), pk=request.POST.get("slot"))
    AttendanceRecord.objects.update_or_create(
        student=student, subject=slot.subject, slot=slot, date=date.today(),
        defaults={"present": request.POST.get("present") == "1"})
    return redirect("dashboard")


@login_required
@require_POST
def attendance_manual(request):
    """Log a class that is not on today's timetable (past day, extra or swapped class)."""
    student = get_student(request)
    subject = get_object_or_404(Subject, pk=request.POST.get("subject"))
    try:
        d = date.fromisoformat(request.POST.get("date", ""))
    except ValueError:
        messages.error(request, "Pick a valid date.")
        return redirect("attendance_history")
    if d > date.today() or d < settings.SEMESTER_START:
        messages.error(request, "Date must be between the semester start and today.")
        return redirect("attendance_history")
    rec = AttendanceRecord.objects.filter(student=student, subject=subject, date=d, slot=None).first()
    present = request.POST.get("present") == "1"
    if rec:
        rec.present = present
        rec.save()
    else:
        AttendanceRecord.objects.create(student=student, subject=subject, date=d, present=present)
    messages.success(request, "Class logged.")
    return redirect("attendance_history")


@login_required
def attendance_base(request):
    """Opening balance: totals up to the day the student started using Acadly."""
    student = get_student(request)
    subjects = Subject.objects.all()
    if request.method == "POST":
        errors = []
        with transaction.atomic():
            for s in subjects:
                try:
                    held = int(request.POST.get(f"held_{s.id}") or 0)
                    att = int(request.POST.get(f"att_{s.id}") or 0)
                except ValueError:
                    errors.append(f"{s.short}: enter whole numbers.")
                    continue
                if held < 0 or att < 0 or att > held:
                    errors.append(f"{s.short}: attended cannot be more than held.")
                    continue
                AttendanceBase.objects.update_or_create(student=student, subject=s,
                                                        defaults={"held": held, "attended": att})
        for e in errors:
            messages.error(request, e)
        if not errors:
            messages.success(request, "Attendance totals saved.")
            return redirect("dashboard")
    bases = {b.subject_id: b for b in AttendanceBase.objects.filter(student=student)}
    rows = [{"subject": s, "base": bases.get(s.id)} for s in subjects]
    return render(request, "core/attendance_base.html", {"rows": rows})


@login_required
def attendance_history(request):
    student = get_student(request)
    recs = AttendanceRecord.objects.filter(student=student).select_related("subject").order_by("-date", "-id")[:60]
    return render(request, "core/attendance_history.html", {
        "records": recs, "subjects": Subject.objects.all(), "today": date.today(),
        "start": settings.SEMESTER_START})


@login_required
@require_POST
def attendance_delete(request, pk):
    get_object_or_404(AttendanceRecord, pk=pk, student=get_student(request)).delete()
    return redirect("attendance_history")


# ---------------------------------------------------------------- timetable
@login_required
def timetable(request):
    rows = []
    for day, name in DAY_CHOICES:
        grouped = {}
        for sl in TimetableSlot.objects.filter(day=day).select_related("subject"):
            text = sl.title + (f" ({sl.batch})" if sl.batch else "")
            grouped.setdefault((sl.start_col, sl.end_col), []).append(text)
        cells, col = [], 0
        while col < len(settings.PERIODS):
            hit = next((k for k in grouped if k[0] == col), None)
            if hit:
                cells.append({"span": hit[1] - hit[0] + 1, "text": " / ".join(grouped[hit]),
                              "filled": True})
                col = hit[1] + 1
            else:
                cells.append({"span": 1, "text": "", "filled": False, "brk": col in settings.BREAK_COLUMNS})
                col += 1
        rows.append({"name": name, "cells": cells})
    heads = [{"label": f"{a}-{b}", "brk": i in settings.BREAK_COLUMNS}
             for i, (a, b) in enumerate(settings.PERIODS)]
    return render(request, "core/timetable.html", {"rows": rows, "heads": heads})


def _aliases():
    al = {}
    for s in Subject.objects.all():
        key = s.short.upper()
        al[key] = s.short
        al[key + " LAB"] = s.short
        first = s.short.split()[0].upper()
        if len(first) >= 2:
            al.setdefault(first, s.short)
        if s.code:
            al[s.code.upper()] = s.short
    for s in Subject.objects.filter(short="PE"):
        al["PHYSICAL EDUCATION"] = s.short
    for a in ACTIVITIES:
        al[a.upper()] = "act:" + a
    al["TUTORIAL"] = "act:Tutorial"
    al["COUNSELLING"] = "act:Student Counselling"
    return al


@login_required
@staff_required
def timetable_upload(request):
    form = TimetableUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        up = TimetableUpload.objects.create(image=form.cleaned_data["image"], uploaded_by=request.user)
        try:
            import pytesseract
            from .services.ocr import read_table
            if settings.TESSERACT_CMD:
                pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
            result = read_table(up.image.path, _aliases())
        except Exception as exc:  # Tesseract missing, unreadable image, ...
            messages.error(request, f"Automatic reading failed ({exc}). Fill the grid by hand.")
            request.session.pop("tt_proposal", None)
            return redirect("timetable_review")
        proposal = {}
        for day_name, cells in result["rows"].items():
            day = ["MON", "TUE", "WED", "THU", "FRI", "SAT"].index(day_name)
            for c in cells:
                if c["code"]:
                    for col in range(c["start"], c["end"] + 1):
                        proposal[f"{day}-{col}"] = c["code"]
        request.session["tt_proposal"] = proposal
        if result["warning"]:
            messages.warning(request, result["warning"])
        messages.info(request, "Check every cell below: the photo reader can miss or mix up cells.")
        return redirect("timetable_review")
    return render(request, "core/timetable_upload.html", {"form": form})


@login_required
@staff_required
def timetable_review(request):
    cols = [i for i in range(len(settings.PERIODS)) if i not in settings.BREAK_COLUMNS]
    if request.method == "POST":
        subjects = {s.short: s for s in Subject.objects.all()}
        valid = set(subjects) | {"act:" + a for a in ACTIVITIES}
        new_slots = []
        runs = {}
        for day, _ in DAY_CHOICES:
            cur = None
            for col in cols:
                a = request.POST.get(f"a_{day}_{col}", "")
                b = request.POST.get(f"b_{day}_{col}", "")
                a, b = (a if a in valid else ""), (b if b in valid else "")
                key = (a, b) if (a or b) else None
                if key and cur and cur["key"] == key and cur["end"] == col - 1:
                    cur["end"] = col
                elif key:
                    cur = {"day": day, "key": key, "start": col, "end": col}
                    runs[(day, col)] = cur
                else:
                    cur = None

        def make(day, start, end, value, batch):
            if value.startswith("act:"):
                return TimetableSlot(day=day, start_col=start, end_col=end, label=value[4:], batch=batch)
            return TimetableSlot(day=day, start_col=start, end_col=end, subject=subjects[value], batch=batch)

        for r in runs.values():
            a, b = r["key"]
            if a and (not b or a == b):
                new_slots.append(make(r["day"], r["start"], r["end"], a, ""))
            else:
                if a:
                    new_slots.append(make(r["day"], r["start"], r["end"], a, "B1"))
                if b:
                    new_slots.append(make(r["day"], r["start"], r["end"], b, "B2"))
        with transaction.atomic():
            TimetableSlot.objects.all().delete()
            TimetableSlot.objects.bulk_create(new_slots)
        request.session.pop("tt_proposal", None)
        messages.success(request, f"Timetable saved ({len(new_slots)} slots).")
        return redirect("timetable")

    # initial values: OCR proposal if there is one, otherwise what is saved now
    initial = {}
    proposal = request.session.get("tt_proposal")
    if proposal:
        for k, v in proposal.items():
            d, c = k.split("-")
            initial[(int(d), int(c))] = (v, "")
    else:
        for sl in TimetableSlot.objects.select_related("subject"):
            val = sl.subject.short if sl.subject else "act:" + sl.label
            for col in range(sl.start_col, sl.end_col + 1):
                a, b = initial.get((sl.day, col), ("", ""))
                if sl.batch == "B2":
                    b = val
                else:
                    a = val
                initial[(sl.day, col)] = (a, b)
    options = [(s.short, s.short) for s in Subject.objects.all()] + [("act:" + a, a) for a in ACTIVITIES]
    rows = []
    for day, name in DAY_CHOICES:
        cells = []
        for col in cols:
            a, b = initial.get((day, col), ("", ""))
            cells.append({"col": col, "a": a, "b": b, "an": f"a_{day}_{col}", "bn": f"b_{day}_{col}"})
        rows.append({"name": name, "cells": cells})
    heads = [f"{settings.PERIODS[c][0]}-{settings.PERIODS[c][1]}" for c in cols]
    return render(request, "core/timetable_review.html", {
        "rows": rows, "heads": heads, "options": options, "from_ocr": bool(proposal)})


# ---------------------------------------------------------------- marks
@login_required
def marks(request):
    student = get_student(request)
    subjects = list(Subject.objects.all())
    if request.method == "POST":
        bad = False
        for s in subjects:
            vals = []
            for f in ("i1", "i2"):
                raw = (request.POST.get(f"{f}_{s.id}") or "").strip()
                if not raw:
                    vals.append(None)
                    continue
                try:
                    v = Decimal(raw)
                except InvalidOperation:
                    v = None
                if v is None or not (0 <= v <= 20):
                    messages.error(request, f"{s.short}: marks must be a number from 0 to 20.")
                    bad = True
                    vals.append(None)
                else:
                    vals.append(v)
            if not bad:
                Mark.objects.update_or_create(student=student, subject=s,
                                              defaults={"internal1": vals[0], "internal2": vals[1]})
        if not bad:
            messages.success(request, "Internal marks saved.")
            return redirect("marks")
    existing = {m.subject_id: m for m in Mark.objects.filter(student=student)}
    rows = []
    for s in subjects:
        m = existing.get(s.id)
        i1, i2 = (m.internal1, m.internal2) if m else (None, None)
        got = [x for x in (i1, i2) if x is not None]
        rows.append({"subject": s, "i1": i1, "i2": i2,
                     "total": sum(got) if got else None,
                     "avg": round(sum(got) / len(got), 2) if got else None})
    return render(request, "core/marks.html", {"rows": rows})


# ---------------------------------------------------------------- SGPA / CGPA
@login_required
def gpa(request):
    student = get_student(request)
    subjects = list(Subject.objects.all())
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "grades":
            for s in subjects:
                grade = request.POST.get(f"grade_{s.id}")
                try:
                    credits = int(request.POST.get(f"credits_{s.id}", s.credits))
                except ValueError:
                    credits = s.credits
                if grade in GRADE_POINTS and 0 <= credits <= 10:
                    Grade.objects.update_or_create(student=student, subject=s,
                                                   defaults={"grade": grade, "credits": credits})
            messages.success(request, "Grades saved.")
        elif action == "semester":
            try:
                v, c = Decimal(request.POST.get("sgpa", "")), int(request.POST.get("credits", ""))
                if not (0 <= v <= 10) or c <= 0:
                    raise ValueError
                Semester.objects.create(student=student, sgpa=v, credits=c)
                messages.success(request, "Semester added.")
            except (InvalidOperation, ValueError):
                messages.error(request, "SGPA must be 0 to 10 and credits a positive number.")
        return redirect("gpa")

    saved = {g.subject_id: g for g in Grade.objects.filter(student=student)}
    rows = []
    for s in subjects:
        g = saved.get(s.id)
        rows.append({"subject": s, "grade": g.grade if g else "A", "credits": g.credits if g else s.credits})
    this_sgpa = sgpa([(r["grade"], r["credits"]) for r in rows])
    this_credits = sum(r["credits"] for r in rows)
    past = list(Semester.objects.filter(student=student).order_by("id"))
    past_pairs = [(float(p.sgpa), p.credits) for p in past]
    return render(request, "core/gpa.html", {
        "rows": rows, "grades": list(GRADE_POINTS), "sgpa": this_sgpa, "this_credits": this_credits,
        "past": past, "cgpa_past": cgpa(past_pairs) if past else None,
        "cgpa_all": cgpa(past_pairs + [(this_sgpa, this_credits)])})


@login_required
@require_POST
def semester_delete(request, pk):
    get_object_or_404(Semester, pk=pk, student=get_student(request)).delete()
    return redirect("gpa")


# ---------------------------------------------------------------- resources
@login_required
def resources(request):
    form = ResourceForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.uploaded_by = request.user
        obj.save()
        messages.success(request, "Added to the library.")
        return redirect("resources")
    items = Resource.objects.select_related("subject", "uploaded_by")
    subj = request.GET.get("subject")
    cat = request.GET.get("category")
    if subj and subj.isdigit():
        items = items.filter(subject_id=subj)
    if cat in dict(Resource.CATEGORIES):
        items = items.filter(category=cat)
    grouped = {}
    for r in items:
        grouped.setdefault(r.subject, {}).setdefault(r.get_category_display(), []).append(r)
    return render(request, "core/resources.html", {
        "form": form, "grouped": grouped, "subjects": Subject.objects.all(),
        "categories": Resource.CATEGORIES, "sel_subject": subj or "", "sel_cat": cat or ""})


@login_required
@require_POST
def resource_delete(request, pk):
    r = get_object_or_404(Resource, pk=pk)
    if r.uploaded_by_id == request.user.id or request.user.is_staff:
        r.delete()
    else:
        messages.error(request, "Only the person who added this can remove it.")
    return redirect("resources")
