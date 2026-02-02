from django.db import models
from django.contrib.auth.models import User 
from django.utils import timezone



import os
import uuid
import string
import random
from datetime import datetime, timedelta
from django.db import models
from django.db.models import JSONField  
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.urls import reverse

from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile

from auditlog.registry import auditlog


def generate_unique_key():
    letters_and_digits = string.ascii_lowercase + string.digits
    while True:
        key = ''.join(random.choices(letters_and_digits, k=32))
        if not WebImages.objects.filter(unique_key=key).exists():
            return key


class WebImages(models.Model):
    unique_key = models.CharField(max_length=100, unique=True, default=generate_unique_key, editable=False)
    image = models.ImageField(upload_to="images/")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='web_images')

    @property
    def get_image_url(self):
        if not self.unique_key:
            return None
        path = reverse('site:serve_optimized_image', kwargs={'unique_key': self.unique_key})
        return path

    class Meta:
        db_table = 'web_images'

    def save(self, *args, **kwargs):
        if self.image and not self.image.name.lower().endswith(".webp"):
            img = Image.open(self.image)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            base_name = slugify(os.path.splitext(os.path.basename(self.image.name))[0])
            unique_suffix = self.unique_key[:8]

            max_base_length = 90 - len(unique_suffix) - len(".webp") - 1
            if len(base_name) > max_base_length:
                base_name = base_name[:max_base_length]

            safe_filename = f"{base_name}_{unique_suffix}.webp"

            buffer = BytesIO()
            img.save(buffer, format="WEBP", quality=100)
            buffer.seek(0)

            self.image.save(safe_filename, ContentFile(buffer.read()), save=False)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.unique_key


def default_expiry():
    return datetime.now() + timedelta(minutes=5)


class PasswordResetCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_codes')
    code = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_expiry)

    def __str__(self):
        return f"{self.user.email} - {self.code} - {self.created_at}"

    class Meta:
        db_table = 'password_reset_code'
        verbose_name_plural = 'Password Reset Codes'
        ordering = ['-created_at']


class LoginLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, blank=True, null=True)
    username = models.CharField(max_length=100, blank=True, null=True)
    wrong_password = models.CharField(max_length=100, blank=True, null=True)
    login_ip = models.CharField(max_length=100, blank=True, null=True)
    login_status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "login_logs"

    def __str__(self) -> str:
        return self.username or ""


class BackendMenu(models.Model):
    module_name = models.CharField(max_length=100, db_index=True)
    menu_name = models.CharField(max_length=100, db_index=True)
    menu_url = models.CharField(max_length=250, blank=True, null=True)
    menu_icon = models.CharField(max_length=250, blank=True, null=True)
    menu_description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, related_name='children', blank=True, null=True)
    is_main_menu = models.BooleanField(default=False)
    is_sub_menu = models.BooleanField(default=False)
    is_sub_child_menu = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "backend_menu"
        indexes = [
            models.Index(fields=['module_name', 'is_active']),
        ]

    def __str__(self) -> str:
        return self.menu_name


class UserMenuPermission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_permission")
    menu = models.ForeignKey(BackendMenu, on_delete=models.CASCADE, related_name="user_permission")
    can_view = models.BooleanField(default=False)
    can_add = models.BooleanField(default=False)
    can_update = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_by_user_permission")
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="updated_by_user_permission", blank=True, null=True)
    deleted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="deleted_by_user_permission", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "user_permission"
        unique_together = (('user', 'menu'),)

    def __str__(self):
        return f"{self.user} -> {self.menu}"


class SiteSettings(models.Model):
    site_title = models.CharField(max_length=255, default="Demo HRMS")
    logo = models.ImageField(upload_to='settings/logo/', blank=True, null=True)
    favicon = models.ImageField(upload_to='settings/favicon/', blank=True, null=True)

    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    facebook_url = models.URLField(blank=True, null=True)
    instagram_url = models.URLField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='site_settings_created_by', blank=True, null=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='site_settings_updated_by', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'site_settings'
        verbose_name_plural = 'Site Settings'
        ordering = ['-is_active']

    def __str__(self):
        return self.site_title if self.site_title else "Site Settings"


class SiteDesignSettings(models.Model):
    primary_color = models.CharField(max_length=20, default="#4354A3")
    bg_color = models.CharField(max_length=20, default="#FFFFFF")
    hover_color = models.CharField(max_length=20, default="#4354A3")
    border_color = models.CharField(max_length=20, default="#E5E7EB")
    shadow_color = models.CharField(max_length=20, default="#DDE0FF")
    control_shadow_color = models.CharField(max_length=20, default="#00000040")
    text_color = models.CharField(max_length=20, default="#22242A")
    text_light_color = models.CharField(max_length=20, default="#868686")
    button_text_color = models.CharField(max_length=20, default="#ffffff")
    button_bg_color = models.CharField(max_length=20, default="#4354A3")
    discount_bg_color = models.CharField(max_length=20, default="#F80000")
    active_color = models.CharField(max_length=20, default="#4354A3")
    inactive_color = models.CharField(max_length=20, default="#EF4444")
    footer_bg_color = models.CharField(max_length=20, default="#22242A")
    footer_text_color = models.CharField(max_length=20, default="#ffffff")

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='design_settings_created_by', blank=True, null=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='design_settings_updated_by', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'site_design_settings'
        verbose_name_plural = 'Site Design Settings'
        ordering = ['-created_at']

    def __str__(self):
        return f"Primary {self.primary_color} / Text {self.text_color}"


class EmailConfiguration(models.Model):
    email_host = models.CharField(max_length=255)
    email_port = models.IntegerField()
    email_host_user = models.EmailField()
    email_host_password = models.CharField(max_length=255)
    use_tls = models.BooleanField(default=True)
    use_ssl = models.BooleanField(default=False)
    email_from_name = models.CharField(max_length=255, default="")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_config_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_config_updated_by', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'email_configuration'

    def __str__(self):
        return self.email_host_user


class SMSConfiguration(models.Model):
    sms_provider_choices = (('ssl', 'SSL'),)
    sms_configuration_type_choices = (('api_token', 'API Token'), ('password', 'Password'),)

    sms_provider = models.CharField(max_length=50, choices=sms_provider_choices, default='ssl', db_index=True)
    sms_configuration_type = models.CharField(max_length=100, choices=sms_configuration_type_choices, default='api_token', db_index=True)
    api_url = models.URLField(max_length=255, blank=True, null=True)
    sms_id = models.CharField(max_length=100, blank=True, null=True)
    api_token = models.TextField(blank=True, null=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    password = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sms_config_created_by_user")
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sms_config_updated_by_user", blank=True, null=True)
    deleted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sms_config_deleted_by_user", blank=True, null=True)
    status = models.BooleanField(default=False)

    class Meta:
        db_table = "sms_configurations"

    def __str__(self):
        return f"{self.get_sms_provider_display()} - {self.get_sms_configuration_type_display()} ({self.sms_id})"


class SMSLog(models.Model):
    mobile_number = models.CharField(max_length=15, db_index=True)
    message_text = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=15, blank=True, null=True)
    ip_address = models.CharField(max_length=50, blank=True, null=True)
    sms_configuration = models.ForeignKey(SMSConfiguration, on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="sms_sent_created_by_user",
        blank=True, null=True
    )
    deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "sms_log"

    def __str__(self):
        return str(self.mobile_number)
    


class SiteSettings(models.Model):
    site_title = models.CharField(max_length=255, default="Demo HRMS")
    logo = models.ImageField(upload_to='settings/logo/', blank=True, null=True)
    favicon = models.ImageField(upload_to='settings/favicon/', blank=True, null=True)

    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    facebook_url = models.URLField(blank=True, null=True)
    instagram_url = models.URLField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='site_settings_created_by', blank=True, null=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='site_settings_updated_by', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'site_settings'
        verbose_name_plural = 'Site Settings'
        ordering = ['-is_active']

    def __str__(self):
        return self.site_title if self.site_title else "Site Settings"
    
class Nationality(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='nationality_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='nationality_updated_by', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.name 
    
    class Meta:
        verbose_name_plural = "Nationalities"
        ordering = ['name']


class Employee(models.Model):
    
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True) 
    hr_file_no = models.CharField(max_length=50, unique=True)
    qid_no = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200) 
    nationality = models.ForeignKey(Nationality, on_delete=models.SET_NULL, null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    joining_date = models.DateField()
    remarks = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='employee_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='employee_updated_by', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False) 

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return f"{self.full_name} ({self.hr_file_no})"
    
    class Meta:
        ordering = ['-created_at'] 


class Employment(models.Model):

    YES_NO_CHOICES = (
        ('YES', 'Yes'),
        ('NO', 'No'),
    )

    RENEW_STATUS_CHOICES = (
        ('NOT_DUE', 'Not Due'),
        ('PENDING', 'Pending'),
        ('RENEWED', 'Renewed'),
    )

    WORK_STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('ON_LEAVE', 'On Leave'),
        ('TERMINATED', 'Terminated'),
    )

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='employments')

    joining_date = models.DateField()
    work_status = models.CharField( max_length=20,choices=WORK_STATUS_CHOICES,default='ACTIVE')

    rp_expiry_date = models.DateField() 
    work_permit_no = models.CharField(max_length=100) 
    work_id = models.CharField(max_length=100)
    qid_renew_status = models.CharField(max_length=20, choices=RENEW_STATUS_CHOICES, default='NOT_DUE')
    qid_lost_status = models.CharField(max_length=3, choices=YES_NO_CHOICES, default='NO')

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='employment_created')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='employment_updated', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False) 

    def __str__(self):
        return f"{self.employee.full_name} - {self.work_permit_no}"

    class Meta:
        ordering = ['-created_at']


class Passport(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='passports')

    passport_no = models.CharField(max_length=50)
    passport_expiry_date = models.DateField()
    passport_renewed = models.BooleanField(default=False)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='passport_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='passport_updated_by', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"Passport - {self.employee.full_name}"
    
    class Meta:
        ordering = ['-created_at'] 


class DrivingLicense(models.Model):
    RENEW_STATUS_CHOICES = (
            ('YES', 'Renewed'),
            ('NO', 'Not Renewed'),
        )
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)

    license_no = models.CharField(max_length=50)
    license_expiry_date = models.DateField()
    license_renewed = models.BooleanField(default=False)
    license_renew_status = models.CharField(max_length=3, choices=RENEW_STATUS_CHOICES)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='driving_license_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='driving_license_updated_by', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"Driving License - {self.employee.full_name}"
    
    class Meta:
        ordering = ['-created_at']


class HealthInsurance(models.Model):
    YES_NO_CHOICES = (
            ('YES', 'Yes'),
            ('NO', 'No'),
        )
    
    RENEW_STATUS_CHOICES = (
            ('YES', 'Renewed'),
            ('NO', 'Not Renewed'),
        )
    
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE)

    hamad_health_card = models.BooleanField(default=False)
    wm_insurance = models.CharField(max_length=3, choices=YES_NO_CHOICES) 
    family_health_card  = models.CharField(max_length=3, choices=YES_NO_CHOICES) 

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='health_insurance_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='health_insurance_updated_by', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False) 
   
    def __str__(self):
        return f"Health & Insurance - {self.employee.full_name}"
    
    class Meta:
        ordering = ['-created_at']


class Contact(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE)

    phone_no = models.CharField(max_length=20)
    phone_no_alt = models.CharField(max_length=20, blank=True, null=True)
    roommate_phone = models.CharField(max_length=20, blank=True, null=True)
    relative_qatar_phone = models.CharField(max_length=20, blank=True, null=True)

    home_phone = models.CharField(max_length=20, blank=True, null=True)
    home_phone_alt = models.CharField(max_length=20, blank=True, null=True)
    home_email = models.EmailField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contact_created_by') 
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contact_updated_by', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"Contact - {self.employee.full_name}"
    
    class Meta:
        ordering = ['-created_at']


class Address(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE)

    national_address = models.TextField()
    room_address = models.TextField()

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='address_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='address_updated_by', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"Address - {self.employee.full_name}"
    
    class Meta:
        ordering = ['-created_at']

class Vehicle(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE)

    vehicle_no = models.CharField(max_length=50)
    istemara_expiry_date = models.DateField()

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehicle_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehicle_updated_by', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"Vehicle - {self.employee.full_name}"

    class Meta:
        ordering = ['-created_at']