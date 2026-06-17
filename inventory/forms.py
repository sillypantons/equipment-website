from django import forms

class EquipmentRequestForm(forms.Form):
    request_type = forms.ChoiceField(
        label="Request Type",
        choices=[
            ('', '-- Select Request Type --'),
            ('service', 'Service'),  
            ('repair', 'Repair'),
            ('other', 'Other'),
        ],
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_request_type'})
    )
    requester_name = forms.CharField(
        max_length=100,
        label="Your Name",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'John Smith'})
    )
    requester_email = forms.EmailField(
        label="Your Email",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'john.smith@pantonmcleod.co.uk'})
    )
    message = forms.CharField(
        label="Request Message",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Please describe what you need this equipment for/any repairs that need to be done to the equipment, and any other relevant information.'
        })
    )