from django.contrib import admin

from . import models

for m in [models.Student, models.Subject, models.TimetableSlot, models.AttendanceBase,
          models.AttendanceRecord, models.Mark, models.Grade, models.Semester, models.Resource]:
    admin.site.register(m)
