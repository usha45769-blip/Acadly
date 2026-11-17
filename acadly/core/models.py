from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

DAY_CHOICES = [(0, "Monday"), (1, "Tuesday"), (2, "Wednesday"), (3, "Thursday"), (4, "Friday"), (5, "Saturday")]
GRADE_CHOICES = [(g, g) for g in ["O", "A+", "A", "B+", "B", "C", "P", "F"]]


class Student(models.Model):
    BATCHES = [("B1", "Batch B1"), ("B2", "Batch B2")]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student")
    phone = models.CharField(max_length=15)
    roll_no = models.PositiveIntegerField(unique=True, null=True, blank=True)
    batch = models.CharField(max_length=2, choices=BATCHES, default="B1")

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} (roll {self.roll_no})"


class Subject(models.Model):
    code = models.CharField(max_length=12, unique=True)          # BCS501
    short = models.CharField(max_length=20, unique=True)         # SEPM
    name = models.CharField(max_length=120)
    staff = models.CharField(max_length=80, blank=True)
    credits = models.PositiveSmallIntegerField(default=3)
    is_lab = models.BooleanField(default=False)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.short} - {self.name}"


class TimetableSlot(models.Model):
    """One class in the weekly grid. start_col/end_col are columns of settings.PERIODS."""
    day = models.PositiveSmallIntegerField(choices=DAY_CHOICES)
    start_col = models.PositiveSmallIntegerField()
    end_col = models.PositiveSmallIntegerField()
    subject = models.ForeignKey(Subject, null=True, blank=True, on_delete=models.CASCADE)
    label = models.CharField(max_length=60, blank=True)          # Library, Tutorial ... (not tracked)
    batch = models.CharField(max_length=2, blank=True)           # '' = whole class

    class Meta:
        ordering = ["day", "start_col", "batch"]

    @property
    def start_time(self):
        return settings.PERIODS[self.start_col][0]

    @property
    def end_time(self):
        return settings.PERIODS[self.end_col][1]

    @property
    def title(self):
        return self.subject.short if self.subject else self.label

    def __str__(self):
        return f"{self.get_day_display()} {self.start_time}-{self.end_time} {self.title}"


class TimetableUpload(models.Model):
    image = models.ImageField(upload_to="timetables/")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class AttendanceBase(models.Model):
    """Opening balance: classes held/attended before the student started logging in Acadly."""
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    held = models.PositiveIntegerField(default=0)
    attended = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("student", "subject")


class AttendanceRecord(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    slot = models.ForeignKey(TimetableSlot, null=True, blank=True, on_delete=models.SET_NULL)
    date = models.DateField()
    present = models.BooleanField()

    class Meta:
        unique_together = ("student", "subject", "date", "slot")
        ordering = ["date"]


class Mark(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    internal1 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                    validators=[MinValueValidator(0), MaxValueValidator(20)])
    internal2 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                    validators=[MinValueValidator(0), MaxValueValidator(20)])

    class Meta:
        unique_together = ("student", "subject")


class Grade(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    grade = models.CharField(max_length=2, choices=GRADE_CHOICES, default="A")
    credits = models.PositiveSmallIntegerField(default=3)

    class Meta:
        unique_together = ("student", "subject")


class Semester(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    sgpa = models.DecimalField(max_digits=4, decimal_places=2,
                               validators=[MinValueValidator(0), MaxValueValidator(10)])
    credits = models.PositiveSmallIntegerField()


class Resource(models.Model):
    CATEGORIES = [("textbook", "Textbook"), ("notes", "Notes"), ("paper", "Question paper"),
                  ("assignment", "Assignment"), ("material", "Study material")]
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="resources")
    category = models.CharField(max_length=12, choices=CATEGORIES)
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to="resources/", blank=True)
    link = models.URLField(max_length=500, blank=True)
    uploaded_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "-created_at"]
