from django.contrib import admin
from .models import Equipment, EquipmentRequest, EquipmentHistory

@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ("SAGE_num", "type", "days_till_service", "location", "next_service")
    search_fields = ("SAGE_num", "type", "serial_number", "purchase_date", "location")
    list_filter = ("type", "location")


@admin.register(EquipmentRequest)
class EquipmentRequestAdmin(admin.ModelAdmin):
    list_display  = ['equipment', 'requester_name', 'requester_email', 'status', 'date_requested', 'date_completed']
    list_filter   = ['status', 'equipment']
    search_fields = ['requester_name', 'requester_email', 'equipment__SAGE_num']
    list_editable = ['status', 'date_completed']  # lets you update status directly from the list view


@admin.register(EquipmentHistory)
class EquipmentHistoryAdmin(admin.ModelAdmin):
    list_display  = ['equipment', 'action', 'performed_by', 'date']
    list_filter   = ['action', 'equipment']
    search_fields = ['equipment__SAGE_num', 'performed_by']