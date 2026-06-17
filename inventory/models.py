from django.db import models
# from django.contrib.auth.models import User
from django.utils import timezone

from dateutil.relativedelta import relativedelta
class Equipment(models.Model):
    SAGE_num = models.CharField(max_length=100, unique=True)
    type = models.CharField(max_length=200, blank=True)
    serial_number = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=200, blank=True)
    # days_till_service = models.IntegerField(null=True, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    last_service = models.DateField(null=True, blank=True)
    # next_service = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    @property
    def next_service(self):
        if self.last_service:
            return self.last_service + relativedelta(months=6)
        return None

    @property
    def days_till_service(self):
        if self.next_service:
            today = timezone.now().date()
            return (self.next_service - today).days
        return None

    def __str__(self):
        return f"{self.SAGE_num} - {self.serial_number}"
    

class EquipmentRequest(models.Model):

    REQUEST_TYPE_CHOICES = [
        ('service  ', 'Service'),    # replace with your actual options
        ('repair', 'Repair'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('accepted',  'Accepted'),
        ('rejected',  'Rejected'),
        ('completed', 'Completed'),
    ]

    equipment      = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='requests')
    requester_name = models.CharField(default='',max_length=100)
    requester_email= models.EmailField(default='')
    request_type    = models.CharField(max_length=50, choices=REQUEST_TYPE_CHOICES, default='')
    message        = models.TextField(default='')
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    date_requested = models.DateTimeField(auto_now_add=True)
    date_completed = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-date_requested']  # newest first

    def __str__(self):
        return f"{self.equipment.SAGE_num} - {self.requester_name} ({self.status})"


class EquipmentHistory(models.Model):

    ACTION_CHOICES = [
        ('created',  'Created'),
        ('edited',   'Edited'),
        ('serviced', 'Serviced'),
        ('request',  'Request'),
    ]

    equipment   = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='history')
    action      = models.CharField(max_length=20, choices=ACTION_CHOICES)
    description = models.TextField()
    performed_by= models.CharField(max_length=100)
    date        = models.DateTimeField(auto_now_add=True)
    status       = models.CharField(max_length=20, default='completed')  
    date_completed = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-date']  # newest first

    def __str__(self):
        return f"{self.equipment.SAGE_num} - {self.action} - {self.date}"