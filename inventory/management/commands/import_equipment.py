from django.core.management.base import BaseCommand
from inventory.models import Equipment
import pandas as pd
from datetime import datetime

print("THIS IS THE FILE BEING RUN")

class Command(BaseCommand):
    help = "Import equipment from Excel file"

    SHEETS = ["GEN", "PUMP", "SUBS", "DOSING"]  # add/remove sheets here as needed

    def add_arguments(self, parser):
        parser.add_argument("file_path", type=str)

    def clean_string(self, value):
        if pd.isna(value):
            return ""
        return str(value).strip()
    
    def parse_date(self, value):
        if pd.isna(value):
            return None
        
        if isinstance(value, datetime):
            return value.date()
        try:
            return pd.to_datetime(value).date()
        except Exception:
            return None
    
    # def clean_int(self, value):
        if pd.isna(value):
            return None
        value = str(value).strip().lower()
        if value in ["", "n/a", "na", "none", "-"]:
            return None

        try:
            return int(float(value))  # handles "12.0" too
        except:
            print(f"Invalid number: {value}")
            return None

    def import_sheet(self, file_path, sheet_name):
        # Import a single sheet and return (created_count, updated_count).
        try:
            # df = pd.read_excel(file_path)
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Error reading sheet '{sheet_name}': {e}"))
            return 0, 0

        df.columns = df.columns.str.strip().str.lower()
        self.stdout.write(f" Columns found: {df.columns.tolist()}")  # this will print the EXCEL column names to help debug any issues with column naming   
        # print(df.columns.tolist()) # this will print the EXCEL column names to help debug any issues with column naming

        created_count = 0
        updated_count = 0

        for _, row in df.iterrows():

            raw_SAGE = row.get("sage reference")

            if pd.isna(raw_SAGE):
                continue  # skip rows with no SAGE reference    

            SAGE_num = str(raw_SAGE).strip().upper()    

            if not SAGE_num:
                continue

            equipment, created = Equipment.objects.update_or_create(
                SAGE_num=SAGE_num,
                defaults={
                    "type": self.clean_string(row.get("equipment type")),
                    "serial_number": self.clean_string(row.get("serial number")),
                    "location": self.clean_string(row.get("location")),
                    # "days_till_service": self.clean_int(row.get("days to next service")),
                    "purchase_date": self.parse_date(row.get("date into service")),
                    "last_service": self.parse_date(row.get("last service")),
                    # "next_service": self.parse_date(row.get("next service")),
                    "notes": self.clean_string(row.get("notes")),
                }
            )

            if created:
                created_count += 1
            else:
                updated_count += 1
        
        return created_count, updated_count
    
    def handle(self, *args, **kwargs):
        file_path = kwargs.get("file_path")

        total_created = 0
        total_updated = 0

        for sheet_name in self.SHEETS:
            self.stdout.write(f"\nImporting sheet: {sheet_name}")
            created, updated = self.import_sheet(file_path, sheet_name)
            self.stdout.write(self.style.SUCCESS(f"  {created} created, {updated} updated"))
            total_created += created
            total_updated += updated

        self.stdout.write(self.style.SUCCESS(
            f"\nTotal: {total_created} created, {total_updated} updated across {len(self.SHEETS)} sheets"
        ))

