from django.db import models
from django.conf import settings
from datetime import date


User=settings.AUTH_USER_MODEL

class Week(models.Model):
    name=models.CharField(max_length=100)
    start_date=models.DateField()
    end_date=models.DateField()
    month=models.IntegerField()
    year=models.IntegerField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='weeks')
    def __str__(self):
        return f"{self.name} - {self.start_date} {self.end_date} {self.month} {self.year} {self.created_by}"


class DailyActivity(models.Model):
    # Foreign Keys
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    week = models.ForeignKey(Week, on_delete=models.CASCADE, related_name='activities')
    date = models.DateField()

    # Choice fields
    STATUS_CHOICES = [
        ('Completed', 'Completed'),
        ('Not Completed', 'Not Completed'),
    ]
    ATTENDANCE_CHOICES = [
        ('Attended', 'Attended'),
        ('Not Attended', 'Not Attended'),
    ]
    SPORT_SESSION_CHOICES = [
        ('Attended', 'Attended'),
        ('Not Attended', 'Not Attended'),
        ('No Session Today', 'No Session Today'),
    ]
    DISCUSSION_CHOICES = [
        ('Online', 'Online'),
        ('Offline', 'Offline'),
        ('Not Attended', 'Not Attended'),
    ]
    YES_NO_CHOICES = [
        ('Yes', 'Yes'),
        ('No', 'No'),
    ]
    # Activity fields
    daily_hearing = models.CharField(max_length=20,choices=STATUS_CHOICES,default='Not Completed')
    daily_reading = models.CharField(max_length=20,choices=STATUS_CHOICES, default='Not Completed')
    daily_chanting = models.PositiveIntegerField(default=0)
    sport_session_attendance = models.CharField(max_length=20, choices=SPORT_SESSION_CHOICES, default='Not Attended')
    
    #thursday specific data
    thursday_morning_chanting_session_attendance = models.CharField(max_length=20, choices=ATTENDANCE_CHOICES, default='Not Attended')
    # Friday Specific data
    friday_morning_chanting_session_attendance = models.CharField(max_length=20, choices=ATTENDANCE_CHOICES, default='Not Attended')
    # Sunday Specific data
    sunday_offline_program_attendance = models.CharField(max_length=20, choices=ATTENDANCE_CHOICES, default='Not Attended')
    sunday_temple_chanting_session_attendance = models.CharField(max_length=20, choices=ATTENDANCE_CHOICES, default='Not Attended')
    #Weekly data
    weekly_discussion_session = models.CharField(max_length=20, choices=DISCUSSION_CHOICES, default='Not Attended')
    weekly_sloka_audio_posted = models.CharField(max_length=5, choices=YES_NO_CHOICES, default='No')
    weekly_seva = models.CharField(max_length=5, choices=YES_NO_CHOICES, default='No')


    feedback_for_this_week = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'date')

    def __str__(self):
        return f"{self.user.username} - {self.date}"

class MonthlyActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    month = models.IntegerField()
    year = models.IntegerField()

    weeks = models.ManyToManyField(Week, related_name='monthly_activity')

    one_to_one_meeting_conducted_with_counselor = models.CharField(
        max_length=5,
        choices=[('Yes', 'Yes'), ('No', 'No')],
        default='No'
    )
    monthly_morning_program = models.CharField(
        max_length=20,
        choices=[('Attended', 'Attended'), ('Not Attended', 'Not Attended')],
        default='Not Attended'
    )
    monthly_book_completed = models.CharField(
        max_length=20,
        choices=[('Completed', 'Completed'),('Partially Completed', 'Partially Completed'), ('Not Completed', 'Not Completed')],
        default='Not Completed'
    )
    #if Book is completed
    book_name = models.CharField(max_length=100, blank=True, default='')
    book_discussion_attended = models.CharField(
        max_length=20,
        choices=[('Attended', 'Attended'), ('Not Attended', 'Not Attended')],
        default='Not Attended'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'month', 'year')
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.user.username} - {self.month}/{self.year}"








