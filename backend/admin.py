from django.contrib import admin
from .models import (
    WebImages, PasswordResetCode, LoginLog, BackendMenu, UserMenuPermission,
    SiteSettings, SiteDesignSettings, EmailConfiguration, SMSConfiguration, SMSLog,
    Nationality, Employee, Employment, Passport, DrivingLicense, HealthInsurance,
    Contact, Address, Vehicle, VehicleAssign, VehicleHandover, TrafficViolation,
    VehicleInstallment, VehicleMaintenance, VehicleAccident, ViolationType,
    Visitor, TrafficViolationPenalty, InsuranceClaim, Uniform, UniformStock,
    UniformIssuance, UniformClearance, VehicleMaintananceType, VehiclePurchase, UniformStockTransactionLog 
)

@admin.register(WebImages)
class WebImagesAdmin(admin.ModelAdmin):
    list_display = ('unique_key', 'image', 'created_by', 'created_at')
    search_fields = ('unique_key',)
    readonly_fields = ('unique_key', 'created_at')

@admin.register(PasswordResetCode)
class PasswordResetCodeAdmin(admin.ModelAdmin):
    list_display = ('user', 'code', 'is_used', 'expires_at', 'created_at')
    search_fields = ('user__email', 'user__username', 'code')
    list_filter = ('is_used',)

@admin.register(LoginLog)
class LoginLogAdmin(admin.ModelAdmin):
    list_display = ('username', 'login_ip', 'login_status', 'created_at')
    search_fields = ('username', 'login_ip')
    list_filter = ('login_status',)

@admin.register(BackendMenu)
class BackendMenuAdmin(admin.ModelAdmin):
    list_display = ('menu_name', 'module_name', 'menu_url', 'parent', 'is_active')
    search_fields = ('menu_name', 'module_name')
    list_filter = ('is_active', 'is_main_menu', 'is_sub_menu')

@admin.register(UserMenuPermission)
class UserMenuPermissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'menu', 'can_view', 'can_add', 'can_update', 'can_delete', 'is_active')
    search_fields = ('user__username', 'menu__menu_name')
    list_filter = ('is_active', 'can_view')

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ('site_title', 'contact_email', 'contact_phone', 'is_active')
    search_fields = ('site_title', 'contact_email')

@admin.register(SiteDesignSettings)
class SiteDesignSettingsAdmin(admin.ModelAdmin):
    list_display = ('primary_color', 'bg_color', 'text_color', 'created_at')

@admin.register(EmailConfiguration)
class EmailConfigurationAdmin(admin.ModelAdmin):
    list_display = ('email_host_user', 'email_host', 'email_port', 'is_active')
    search_fields = ('email_host_user', 'email_host')
    list_filter = ('is_active', 'use_tls', 'use_ssl')

@admin.register(SMSConfiguration)
class SMSConfigurationAdmin(admin.ModelAdmin):
    list_display = ('sms_provider', 'sms_id', 'status', 'created_at')
    search_fields = ('sms_id', 'username')
    list_filter = ('status', 'sms_provider')

@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ('mobile_number', 'status', 'created_at')
    search_fields = ('mobile_number',)
    list_filter = ('status',)

@admin.register(Nationality)
class NationalityAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active')
    search_fields = ('name', 'code')
    ordering = ('name',)

@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'phone_number', 'email', 'created_at', 'is_active')
    search_fields = ('first_name', 'last_name', 'phone_number', 'email')
    list_filter = ('is_active', 'created_at')

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'hr_file_no', 'qid_no', 'nationality', 'joining_at', 'is_active')
    search_fields = ('first_name', 'last_name', 'hr_file_no', 'qid_no')
    list_filter = ('gender', 'nationality', 'is_active')
    ordering = ('first_name', 'last_name')

@admin.register(Employment)
class EmploymentAdmin(admin.ModelAdmin):
    list_display = ('employee', 'work_status', 'work_permit_no', 'qid_renew_status', 'is_active')
    search_fields = ('employee__first_name', 'employee__last_name', 'work_permit_no', 'work_id')
    list_filter = ('work_status', 'qid_renew_status', 'is_active')

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

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('employee', 'national_address', 'room_address')
    search_fields = ('employee__first_name', 'employee__last_name', 'national_address')

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('plate_no', 'vehicle_type', 'ownership', 'istemara_expiry_date', 'insurance_name', 'is_active')
    search_fields = ('plate_no', 'insurance_name')
    list_filter = ('vehicle_type', 'ownership', 'is_active')
    ordering = ('istemara_expiry_date',)

@admin.register(VehicleHandover)
class VehicleHandoverAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'from_employee', 'to_employee', 'handover_date')
    search_fields = ('vehicle__plate_no', 'from_employee__first_name', 'to_employee__first_name')
    list_filter = ('handover_date',)

@admin.register(VehicleAssign)
class VehicleAssignAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'employee', 'assigned_date', 'is_active')
    search_fields = ('vehicle__plate_no', 'employee__first_name', 'employee__last_name')
    list_filter = ('assigned_date', 'is_active')

@admin.register(ViolationType)
class ViolationTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    search_fields = ('name',)
    list_filter = ('is_active',) 

@admin.register(TrafficViolation)
class TrafficViolationAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'violation_type', 'violation_date',)
    search_fields = ('vehicle__plate_no', 'violation_type__name', )
    list_filter = ('violation_date',)

@admin.register(TrafficViolationPenalty)
class TrafficViolationPenaltyAdmin(admin.ModelAdmin):
    list_display = ('violation', 'fine_amount', 'payment_status', 'paid_date', 'payment_method',)
    search_fields = ('violation__vehicle__plate_no',)
    list_filter = ('payment_status', 'payment_method', 'paid_date')


@admin.register(VehicleInstallment)
class VehicleInstallmentAdmin(admin.ModelAdmin):
    list_display = ('purchase', 'installment_no', 'amount', 'due_date', 'is_paid')
    search_fields = ('purchase__vehicle__plate_no',)
    list_filter = ('is_paid', 'due_date')


@admin.register(VehiclePurchase)
class VehiclePurchaseAdmin(admin.ModelAdmin):
    list_display = ('employee', 'vehicle', 'purchase_date', 'total_amount', 'down_payment',)
    search_fields = ('employee__first_name', 'employee__last_name', 'vehicle__plate_no')
    list_filter = ('payment_method', 'payment_period', 'purchase_date')

@admin.register(VehicleMaintenance)
class VehicleMaintenanceAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'maintenance_type', 'cost', 'status', 'maintenance_date')
    search_fields = ('vehicle__plate_no', 'maintenance_type')
    list_filter = ('status', 'maintenance_date')

@admin.register(VehicleAccident)
class VehicleAccidentAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'accident_date', 'accident_place', 'damage_cost', 'insurance_claimed')
    search_fields = ('vehicle__plate_no', 'accident_place')
    list_filter = ('insurance_claimed', 'accident_date')

@admin.register(InsuranceClaim)
class InsuranceClaimAdmin(admin.ModelAdmin):
    list_display = ('accident', 'claim_amount', 'claim_status', 'claim_date')
    search_fields = ('accident__vehicle__plate_no',)
    list_filter = ('claim_status', 'claim_date')

@admin.register(Uniform)
class UniformAdmin(admin.ModelAdmin):
    list_display = ('name', 'uniform_type', 'is_active')
    search_fields = ('name',)
    list_filter = ('uniform_type', 'is_active')

@admin.register(UniformStock)
class UniformStockAdmin(admin.ModelAdmin):
    list_display = ('uniform', 'size', 'quantity', 'is_active')
    search_fields = ('uniform__name', 'size')
    list_filter = ('size', 'is_active')

@admin.register(UniformIssuance)
class UniformIssuanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'uniform_stock', 'quantity', 'status', 'issued_date')
    search_fields = ('employee__first_name', 'employee__last_name', 'uniform_stock__uniform__name')
    list_filter = ('status', 'issued_date', 'is_active')

@admin.register(UniformClearance)
class UniformClearanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'uniform_stock', 'quantity', 'status', 'clearance_date')
    search_fields = ('employee__first_name', 'employee__last_name', 'uniform_stock__uniform__name')
    list_filter = ('status', 'clearance_date', 'is_active')

@admin.register(UniformStockTransactionLog)
class UniformStockTransactionLogAdmin(admin.ModelAdmin):
    list_display = ('uniform_stock', 'transaction_type', 'quantity_change', 'quantity_before', 'quantity_after',)
    search_fields = ('uniform_stock__uniform__name',)
    list_filter = ('transaction_type', 'created_at')


@admin.register(VehicleMaintananceType)
class VehicleMaintananceTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    search_fields = ('name',)

