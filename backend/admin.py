from django.contrib import admin
from .models import (
    Nationality, 
    Employee, Employment, Passport, DrivingLicense, 
    HealthInsurance, Contact, Address, Vehicle, BackendMenu
)

@admin.register(BackendMenu)
class BackendMenuAdmin(admin.ModelAdmin):
    list_display = ('module_name', 'menu_name', 'menu_url', 'is_active')

@admin.register(Nationality)
class NationalityAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')
    ordering = ('name',) 

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'hr_file_no', 'qid_no', 'nationality', 'joining_date', 'is_active')
    search_fields = ('first_name', 'last_name', 'hr_file_no', 'qid_no')
    list_filter = ('gender', 'nationality', 'is_active')
    ordering = ('first_name', 'last_name')

@admin.register(Employment)
class EmploymentAdmin(admin.ModelAdmin):
    list_display = ('employee', 'work_status', 'work_permit_no', 'qid_renew_status', 'is_active')
    search_fields = ('employee__first_name', 'employee__last_name', 'work_permit_no', 'work_id')
    list_filter = ('work_status', 'qid_renew_status', 'is_active')
    ordering = ('employee__first_name', 'employee__last_name')

@admin.register(Passport)
class PassportAdmin(admin.ModelAdmin):
    list_display = ('employee', 'passport_no', 'passport_expiry_date', 'passport_renewed')
    search_fields = ('employee__first_name', 'employee__last_name', 'passport_no')
    list_filter = ('passport_renewed', 'is_active')
    ordering = ('passport_expiry_date',)

@admin.register(DrivingLicense)
class DrivingLicenseAdmin(admin.ModelAdmin):
    list_display = ('employee', 'license_no', 'license_expiry_date', 'license_renew_status')
    search_fields = ('employee__first_name', 'employee__last_name', 'license_no')
    list_filter = ('license_renew_status', 'is_active')
    ordering = ('license_expiry_date',)

@admin.register(HealthInsurance)
class HealthInsuranceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'hamad_health_card', 'wm_insurance', 'family_health_card')
    search_fields = ('employee__first_name', 'employee__last_name')
    list_filter = ('hamad_health_card', 'wm_insurance', 'is_active')

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('employee', 'phone_no', 'home_email')
    search_fields = ('employee__first_name', 'employee__last_name', 'phone_no', 'home_email')
    ordering = ('employee__first_name', 'employee__last_name')

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('employee', 'national_address', 'room_address')
    search_fields = ('employee__first_name', 'employee__last_name', 'national_address')

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('employee', 'vehicle_no', 'istemara_expiry_date')
    search_fields = ('employee__first_name', 'employee__last_name', 'vehicle_no')
    ordering = ('istemara_expiry_date',)

