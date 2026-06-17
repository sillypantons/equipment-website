# from urllib import request

from datetime import timezone
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Equipment, EquipmentRequest
from django.db.models import Q
from django.core.paginator import Paginator

@login_required
def equipment_list(request):
    equipment = Equipment.objects.all()

    #search functionality
    query = request.GET.get("q", "")
    if query:
        equipment = equipment.filter(
            Q(SAGE_num__icontains=query) |
            Q(type__icontains=query) |
            Q(location__icontains=query) |
            Q(serial_number__icontains=query)
        )

    # filters -- location
    location_filter = request.GET.get("location", "")
    if location_filter:
        equipment = equipment.filter(location=location_filter)
    
    # Multi-checkbox filters for type -- getlist handles multiple values for the same key in the query params, e.g. ?type=Camera&type=Lens
    selected_types = request.GET.getlist("type")
    if selected_types:
        equipment = equipment.filter(type__in=selected_types)
    
    from django.db.models import F, ExpressionWrapper, DateField
    from django.utils import timezone
    from datetime import timedelta

    equipment = equipment.annotate(
        next_service_calc=ExpressionWrapper(
            F("last_service") + timedelta(days=182),
            output_field=DateField()
        )
    )

    # sorting functionality
    sort = request.GET.get("sort", "SAGE_num")  # default sort by SAGE_num  
    direction = request.GET.get("direction", "asc")  # default asc

    allowed_sorts = ["SAGE_num", "type", "location", "next_service_calc"]

    if sort in allowed_sorts:
        if direction == "desc":
            equipment = equipment.order_by(f"-{sort}")
        else:
            equipment = equipment.order_by(sort)
    else:
        equipment = equipment.order_by("SAGE_num")    # fallback default        

    # pagination
    paginator = Paginator(equipment, 20)  # 20 items per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)    # page_number if go back to old
    
    # Get distinct values for dropdowns
    # types = Equipment.objects.values_list('type', flat=True).distinct()
    locations = Equipment.objects.values_list('location', flat=True).distinct().order_by('location')

    return render(request, "inventory/equipment_list.html", {
        "page_obj": page_obj,
        "type_groups": get_type_groups(),  # get grouped types for checkboxes
        "locations": locations,
        'selected_types': selected_types, # passed back so checkboxes stay ticked
        "location_filter": location_filter,  # pass back so dropdown stays selected
        "query":           query,            # pass back so search box stays filled
    })

def get_type_groups():
    # Group equipment types by category based on keywords.
    all_types = Equipment.objects.values_list('type', flat=True).distinct().order_by('type')

    groups = {
        "Generators":    [],
        "Pumps":         [],
        "Submersibles":  [],
        "Dosing Pumps":  [],
        "Other":         [],
    }

    for t in all_types:
        t_lower = t.lower()
        if "generator" in t_lower:
            groups["Generators"].append(t)
        elif "dosing" in t_lower:
            groups["Dosing Pumps"].append(t)
        elif "sub" in t_lower:
            groups["Submersibles"].append(t)
        elif "pump" in t_lower:
            groups["Pumps"].append(t)
        else:
            groups["Other"].append(t)

    # Remove empty groups
    return {k: v for k, v in groups.items() if v}


from django.core.mail import send_mail
from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from .forms import EquipmentRequestForm
from itertools import chain
# from operator import attrgetter

def equipment_detail(request, SAGE_num):
    item = get_object_or_404(Equipment, SAGE_num=SAGE_num)
    request_history = EquipmentRequest.objects.filter(equipment=item)
    item_history    = EquipmentHistory.objects.filter(equipment=item)
    combined_history = sorted(
        chain(request_history, item_history),
        key=lambda x: x.date if hasattr(x, 'date') else x.date_requested,
        reverse=True
        )
    # service_form_value = get_service_form_value(item)

    if request.method == 'POST':
        form = EquipmentRequestForm(request.POST)
        if form.is_valid():
            name         = form.cleaned_data['requester_name']
            email        = form.cleaned_data['requester_email']
            request_type = form.cleaned_data['request_type']
            message_text = form.cleaned_data['message']

            EquipmentRequest.objects.create(
                equipment=item,
                requester_name=name,
                requester_email=email,
                request_type=request_type,
                message=message_text,
                status='pending',
            )

            # Log the request to item history
            # EquipmentHistory.objects.create(
            #     equipment=item,
            #     action='request',
            #     description=f"Request type: {request_type}\nMessage: {message_text}",
            #     performed_by=name,
            # )
            
            return render(request, 'inventory/request_successful.html', {'item': item})
    else:
        form = EquipmentRequestForm()

    return render(request, 'inventory/equipment_detail.html', {
        'item': item,
        'form': form,
        'combined_history': combined_history,
        # 'service_form_value': service_form_value(item),
    })


def delete_request(request, request_id):
    if not request.user.is_authenticated or not request.user.is_staff:
        messages.error(request, "You need admin permission to access the request dashboard.")
        return redirect('equipment_list')

    eq_request = get_object_or_404(EquipmentRequest, id=request_id)

    if request.method == 'POST':
        eq_request.delete()
        messages.success(request, "Request deleted successfully.")

    return redirect('request_dashboard')


# def equipment_detail(request, SAGE_num):
    item = get_object_or_404(Equipment, SAGE_num=SAGE_num)
    request_history = EquipmentRequest.objects.filter(equipment=item)
    
    if request.method == 'POST':
        form = EquipmentRequestForm(request.POST)
        if form.is_valid():
            name    = form.cleaned_data['requester_name']
            email   = form.cleaned_data['requester_email']
            message_text = form.cleaned_data['message']

            # Email to manager
            subject = f"Equipment Request: {item.SAGE_num} - {item.type}"
            body = f"""
A new equipment request has been submitted via the inventory system.

Equipment Details:
------------------
SAGE Reference: {item.SAGE_num}
Type:           {item.type}
Location:       {item.location}

Requested By:   {name}
Requester Email:{email}

Message:
--------
{message_text}
            """

            # Confirmation email to requester
            confirmation_body = f"""
Hi {name},

Your request for the following equipment has been submitted:

  SAGE Reference: {item.SAGE_num}
  Type:           {item.type}
  Location:       {item.location}

Your message:
{message_text}

regards,
Equipment Inventory System
            """

            try:
                # Send to manager
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=None,
                    recipient_list=['alex.campbell@pantonmcleod.co.uk'],  # sends to manager, could be multiple if needed
                    fail_silently=False,
                )
                # Send confirmation to requester
                send_mail(
                    subject=f"Request Confirmation - {item.SAGE_num}",
                    message=confirmation_body,
                    from_email=None,
                    recipient_list=[email],
                    fail_silently=False,
                )
                
                 # Save request to database
                EquipmentRequest.objects.create(
                    equipment=item,
                    requester_name=name,
                    requester_email=email,
                    message=message_text,
                    status='pending',
                )
                
                # messages.success(request, f"Request submitted successfully. A confirmation has been sent to {email}.")
                return render(request, 'request_success.html', {'item': item})

            except Exception as e:
                messages.error(request, "There was a problem sending your request. Please try again.")
                print(f"Email error: {e}")

    else:
        form = EquipmentRequestForm()

    return render(request, 'inventory/equipment_detail.html', {
        'item': item,
        'form': form,
        'request_history': request_history,
        # 'service_form_value': get_service_form_value(item), # enable if using dynamic form values in get_service_form_value
    })

# Just used the OTHER selection in form - dont need to use this as defaults to OTHER if value does not match
# def get_service_form_value(item):
    # Return the correct service form value based on equipment type.
    type_lower = item.type.lower()

    # Generators - check kVA size
    if "generator" in type_lower:
        # Extract the kVA number from the type string e.g. "3.5 kVA Generator"
        import re
        match = re.search(r'(\d+\.?\d*)\s*kva', type_lower)
        if match:
            kva = float(match.group(1))
            if kva <= 3.5:
                return "Small%20Generator"    
            else:
                return "Large%20Generator"

    elif "dosing" in type_lower:
        return "Dosing%20Pump"                

    elif "submersible" in type_lower:
        return "Submersible%20Pump"                

    elif "high" in type_lower:
        return "2%5C%22%20Pump"
    
    elif "trash" in type_lower:
        return "Trash%20Pump"

    # Fallback if nothing matches
    return ""


from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm

def is_admin(user):
    return user.is_staff  # only Django staff/admin users can access

# @login_required(login_url='login')
# @user_passes_test(is_admin, login_url='login')
def request_dashboard(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        messages.error(request, "You need admin permission to access the request dashboard.")
        return redirect('equipment_list')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    requests = EquipmentRequest.objects.all()

    if status_filter:
        requests = requests.filter(status=status_filter)

    return render(request, 'inventory/request_dashboard.html', {
        'requests': requests,
        'status_filter': status_filter,
    })


# @login_required(login_url='login')
# @user_passes_test(is_admin, login_url='login')
def update_request_status(request, request_id):
    if not request.user.is_authenticated or not request.user.is_staff:
        messages.error(request, "You need admin permission to access the request dashboard.")
        return redirect('equipment_list')
    
    eq_request = get_object_or_404(EquipmentRequest, id=request_id)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['pending', 'accepted', 'rejected', 'completed']:
            eq_request.status = new_status
            if new_status == 'completed':
                from django.utils import timezone
                eq_request.date_completed = timezone.now()
            else:
                eq_request.date_completed = None
            eq_request.save()

    return redirect('request_dashboard')


def login_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('request_dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_staff:
                login(request, user)
                return redirect('request_dashboard')
            else:
                form.add_error(None, "You do not have permission to access this page.")
    else:
        form = AuthenticationForm()

    return render(request, 'registration/login.html', {'form': form})


def logout_view(request):
    if request.method == 'POST':
        logout(request)
    return redirect('login')


from django.forms import ModelForm
from django import forms

class EquipmentEditForm(ModelForm):
    class Meta:
        model = Equipment
        fields = ['type', 'serial_number', 'location', 'purchase_date', 'last_service', 'notes']
        widgets = {
            'type':          forms.TextInput(attrs={'class': 'form-control'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control'}),
            'location':      forms.TextInput(attrs={'class': 'form-control'}),
            'purchase_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'last_service':  forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes':         forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


from .models import Equipment, EquipmentRequest, EquipmentHistory

def edit_equipment(request, SAGE_num):
    if not request.user.is_authenticated or not request.user.is_staff:
        messages.error(request, "You need admin permission to edit equipment.")
        return redirect('equipment_detail', SAGE_num=SAGE_num)

    item = get_object_or_404(Equipment, SAGE_num=SAGE_num)

    if request.method == 'POST':
        # Store old values before saving so we can log what changed
        old_values = {
            'type':          item.type,
            'serial_number': item.serial_number,
            'location':      item.location,
            'purchase_date': item.purchase_date,
            'last_service':  item.last_service,
            'notes':         item.notes,
        }

        form = EquipmentEditForm(request.POST, instance=item)
        if form.is_valid():
            form.save()

            # Build a description of what changed
            changes = []
            for field, old_val in old_values.items():
                new_val = getattr(item, field)
                if str(old_val) != str(new_val):
                    changes.append(f"{field.replace('_', ' ').title()}: '{old_val}' → '{new_val}'")

            description = "\n".join(changes) if changes else "No fields changed."

            from django.utils import timezone

            EquipmentHistory.objects.create(
                equipment=item,
                action='edited',
                description=description,
                performed_by=request.user.username,
                status='completed',             # status is completed as default as edits not checked (mainly for formatting)
                date_completed=timezone.now(),  # same as date made
            )

            messages.success(request, f"{SAGE_num} has been updated successfully.")
            return redirect('equipment_detail', SAGE_num=SAGE_num)
    else:
        form = EquipmentEditForm(instance=item)

    return render(request, 'inventory/edit_equipment.html', {
        'item': item,
        'form': form,
    })
