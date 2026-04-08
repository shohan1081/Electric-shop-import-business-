from django.db import models
from django.contrib.admin.models import LogEntry

class DailyActivity(LogEntry):
    class Meta:
        proxy = True
        verbose_name = "Daily Activity & Report"
        verbose_name_plural = "Daily Activity & Reports"
