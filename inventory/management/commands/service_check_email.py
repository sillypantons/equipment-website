from django.core.management.base import BaseCommand
from inventory.models import Equipment
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.conf import settings

class Command(BaseCommand):
    help = "Check for equipment due for service"

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        soon = today + timedelta(days=14)

        due_items = []

        for item in Equipment.objects.all():
            if item.next_service and today <= item.next_service <= soon:
                due_items.append(item)

        if due_items:
            message = "Equipment due for service soon:\n\n"

            for item in due_items:
                message += f"{item.SAGE_num} - Due on {item.next_service}\n"

            send_mail(
                "Equipment Service Due Soon",
                message,
                settings.EMAIL_HOST_USER,
                ["alex.campbell@pantonmcleod.co.uk"],
            )

            self.stdout.write(self.style.SUCCESS("Email sent"))
        else:
            self.stdout.write("No items due soon")

        overdue_items = []

        for item in Equipment.objects.all():
            if item.next_service and item.next_service < today:
                overdue_items.append(item)

        if overdue_items:
            message = "Overdue equipment:\n\n"

            for item in overdue_items:
                message += f"{item.SAGE_num} - Was due on {item.next_service}\n"

            send_mail(
                "Overdue Equipment",
                message,
                settings.EMAIL_HOST_USER,
                ["alex.campbell@pantonmcleod.co.uk"],
            )

            self.stdout.write(self.style.SUCCESS("Email sent"))
        else:
            self.stdout.write("No overdue items")