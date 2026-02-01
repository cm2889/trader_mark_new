from django import forms 
from backend.models import Nationality, Employee, Employment, Passport, DrivingLicense, HealthInsurance, Contact, Address, Vehicle

class NationalityForm(forms.ModelForm):
    class Meta:
        model = Nationality
        exclude = ['created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        exclude = ['user', 'created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']

class EmploymentForm(forms.ModelForm):
    class Meta:
        model = Employment
        exclude = ['employee', 'created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']

class PassportForm(forms.ModelForm):
    class Meta:
        model = Passport
        exclude = ['employee', 'created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']

class DrivingLicenseForm(forms.ModelForm):
    class Meta:
        model = DrivingLicense
        exclude = ['employee', 'created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']

class HealthInsuranceForm(forms.ModelForm):
    class Meta:
        model = HealthInsurance
        exclude = ['employee', 'created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']

class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        exclude = ['employee', 'created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        exclude = ['employee', 'created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']

class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        exclude = ['employee', 'created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']