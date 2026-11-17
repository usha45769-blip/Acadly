"""SGPA / CGPA (VTU 10-point scale)."""
GRADE_POINTS = {"O": 10, "A+": 9, "A": 8, "B+": 7, "B": 6, "C": 5, "P": 4, "F": 0}


def sgpa(courses):
    """courses: iterable of (grade, credits). SGPA = sum(points x credits) / sum(credits)."""
    total = sum(c for _, c in courses)
    if total == 0:
        return 0.0
    return round(sum(GRADE_POINTS[g] * c for g, c in courses) / total, 2)


def cgpa(semesters):
    """semesters: iterable of (sgpa, credits). Credit-weighted mean of SGPAs."""
    total = sum(c for _, c in semesters)
    if total == 0:
        return 0.0
    return round(sum(s * c for s, c in semesters) / total, 2)
