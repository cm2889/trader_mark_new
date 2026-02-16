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
from django.db import models
from django.contrib.auth.models import User 
from django.utils import timezone
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from django.utils.text import slugify
from django.db import transaction
from django.utils import timezone

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
    
class Company(models.Model):
    name = models.CharField(max_length=200, unique=True, db_index=True)
    code = models.CharField(max_length=20, unique=True)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='company_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='company_updated_by', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False) 
  
    def save(self, *args, **kwargs):
        if not self.code:
            last_company = Company.objects.all().order_by('id').last()
            if last_company:
                last_code = int(last_company.code.split('COM')[-1])
                new_code = f"COM{last_code + 1:05d}"
            else:
                new_code = "COM00001"
            self.code = new_code
        super().save(*args, **kwargs)

    class Meta:
        db_table = "org_companies"

    def __str__(self):
        return self.name

    

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


class Visitor(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100) 
    phone_number = models.CharField(max_length=20, blank=True, null=True) 
    email = models.EmailField(blank=True, null=True) 

    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    class Meta:
        ordering = ['-created_at'] 

class Employee(models.Model):
    
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True) 
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True) 
    hr_file_no = models.CharField(max_length=50, unique=True)
    qid_no = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200) 
    email = models.EmailField(blank=True, null=True) 
    phone_number = models.CharField(max_length=20, blank=True, null=True) 
    nationality = models.ForeignKey(Nationality, on_delete=models.SET_NULL, null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    joining_at = models.DateTimeField(default=timezone.now)
    remarks = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='employee_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='employee_updated_by', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False) 

    # auto generate full number  
    

    def save(self, *args, **kwargs):
        # Only auto-generate HR File No if not provided
        if not self.pk and not self.hr_file_no:
            from django.db import transaction
            with transaction.atomic():
                last_employee = (
                    Employee.objects
                    .select_for_update()
                    .order_by('-id')
                    .first()
                )

                if last_employee and last_employee.hr_file_no.isdigit():
                    last_hr = int(last_employee.hr_file_no)
                    self.hr_file_no = str(last_hr + 1).zfill(8)
                else:
                    self.hr_file_no = '00000001'

        if not self.joining_at:
            self.joining_at = timezone.now()

        super().save(*args, **kwargs)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return f"{self.full_name} ({self.hr_file_no})"
    
    class Meta:
        ordering = ['-created_at'] 

# =========================================================
# Uniform Management
# ========================================================= 
class Uniform(models.Model):
    UNIFORM_TYPE_CHOICES = (
        ('SHIRT', 'Shirt'),
        ('PANT', 'Pant'),
        ('JACKET', 'Jacket'),
        ('SHOES', 'Shoes'),
        ('CAP', 'Cap'),
        ('OTHER', 'Other'),
    )

    name = models.CharField(max_length=100)
    uniform_type = models.CharField(max_length=20, choices=UNIFORM_TYPE_CHOICES) 
    description = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uniform_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uniform_updated_by', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 

    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False) 

    def __str__(self):
        return f"{self.name} ({self.get_uniform_type_display()})"
    
    class Meta:
        ordering = ['name'] 

# ========================================================
# Uniform Stock Management
# ======================================================== 
class UniformStock(models.Model):
    SIZE_CHOICES = (
        ('XS', 'Extra Small'),
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
        ('XL', 'Extra Large'),
        ('XXL', 'Double Extra Large'),
    )

    code = models.CharField(max_length=50, unique=True) 
    uniform = models.ForeignKey(Uniform, on_delete=models.CASCADE, related_name='stocks')

    size = models.CharField(max_length=20, choices=SIZE_CHOICES)
    quantity = models.PositiveIntegerField(default=0)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uniform_stock_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uniform_stock_updated_by', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 

    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False) 

    def save(self, *args, **kwargs):
        if not self.code:
            # Short, clean uniform name
            uniform_name = slugify(self.uniform.name).upper().replace('-', '')

            # Example: UNI-SHIRT-OXFORD-M
            base_code = f"UNI-{self.uniform.uniform_type}-{uniform_name}-{self.size}"

            code = base_code
            counter = 1

            # Ensure uniqueness
            while UniformStock.objects.filter(code=code).exists():
                counter += 1
                code = f"{base_code}-{counter}"

            self.code = code

        super().save(*args, **kwargs) 

    def __str__(self):
        return f"{self.uniform.name} - Size: {self.size} - Qty: {self.quantity} ({self.code})"
    
    class Meta:
        ordering = ['uniform__name', 'size'] 

# ========================================================
# Uniform Issuance Management
# ========================================================
class UniformIssuance(models.Model):

    STATUS_CHOICES = (
        ('ISSUED', 'Issued'),
        ('RETURNED', 'Returned'),
        ('LOST', 'Lost'),
        ('DAMAGED', 'Damaged'),
    )

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='uniform_issuances')
    uniform_stock = models.ForeignKey(UniformStock, on_delete=models.PROTECT, related_name='issuances')

    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ISSUED')

    issued_date = models.DateField(default=timezone.now)
    return_date = models.DateField(blank=True, null=True)
    expected_return_date = models.DateField(blank=True, null=True)

    remark = models.CharField(max_length=255, blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uniform_issuance_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uniform_issuance_updated_by', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.uniform_stock.uniform.name} issued to {self.employee.full_name} - Status: {self.status}" 
    
    class Meta:
        ordering = ['-issued_date', '-created_at']



# ========================================================
# Employee Exit Uniform Clearance
# ========================================================
class UniformClearance(models.Model):

    STATUS_CHOICES = (
        ('RETURNED', 'Returned'),
        ('LOST', 'Lost'),
        ('DAMAGED', 'Damaged'),
    )

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='uniform_clearances')
    uniform_stock = models.ForeignKey(UniformStock, on_delete=models.PROTECT, related_name='clearances' )

    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='RETURNED')

    clearance_date = models.DateField(default=timezone.now)
    remark = models.CharField(max_length=255, blank=True, null=True)
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uniform_clearance_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uniform_clearance_updated_by', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.uniform_stock.uniform.name} cleared for {self.employee.full_name} - Status: {self.status}"

    class Meta:
        ordering = ['-clearance_date', '-created_at']


# ========================================================
# Uniform Logs 
# ========================================================
class UniformStockTransactionLog(models.Model):

    TRANSACTION_TYPE_CHOICES = (
        ('ISSUE', 'Issued'),
        ('RETURN', 'Returned'),
        ('LOST', 'Lost'),
        ('DAMAGED', 'Damaged'),
        ('ADJUST', 'Manual Adjustment'),
        ('ADD', 'Stock Added'),
    )

    uniform_stock = models.ForeignKey(UniformStock, on_delete=models.PROTECT, related_name='transaction_logs')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    
    quantity_change = models.IntegerField()

    quantity_before = models.PositiveIntegerField()
    quantity_after = models.PositiveIntegerField()

    issuance = models.ForeignKey(UniformIssuance, on_delete=models.SET_NULL, null=True, blank=True)
    clearance = models.ForeignKey(UniformClearance, on_delete=models.SET_NULL, null=True, blank=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

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

    joining_at = models.DateTimeField(null=True, blank=True)
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
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='driving_licenses')

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
    
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='health_insurance')

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
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='contact')

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
    
    # Helper properties to return empty string instead of None
    def get_phone_no_alt_display(self):
        return self.phone_no_alt or ""
    
    def get_roommate_phone_display(self):
        return self.roommate_phone or ""
    
    def get_relative_qatar_phone_display(self):
        return self.relative_qatar_phone or ""
    
    def get_home_phone_display(self):
        return self.home_phone or ""
    
    def get_home_phone_alt_display(self):
        return self.home_phone_alt or ""
    
    def get_home_email_display(self):
        return self.home_email or ""
    
    class Meta:
        ordering = ['-created_at']

class Address(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE)
    present_address = models.TextField(null=True, blank=True)
    permanent_address = models.TextField(null=True, blank=True)

    national_address = models.TextField(null=True, blank=True)
    room_address = models.TextField(null=True, blank=True)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='address_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='address_updated_by', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"Address - {self.employee.full_name}"
    
    # Helper properties to return empty string or user-friendly text instead of None
    def get_present_address_display(self):
        return self.present_address or ""
    
    def get_permanent_address_display(self):
        return self.permanent_address or ""
    
    def get_national_address_display(self):
        return self.national_address or ""
    
    def get_room_address_display(self):
        return self.room_address or ""
    
    class Meta:
        ordering = ['-created_at']


# =========================
# VEHICLE
# =========================
class Vehicle(models.Model):

    VEHICLE_TYPE_CHOICES = (
        ('BIKE', 'Bike'),
        ('CAR', 'Car'),
    )
     
    OWNERSHIP_CHOICES = (
        ('COMPANY', 'Company'),
        ('DRIVER', 'Driver'),
    )

    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
    )

    vehicle_type = models.CharField(max_length=10, choices=VEHICLE_TYPE_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ACTIVE') 

    plate_no = models.CharField(max_length=50, unique=True, null=True, blank=True)
    chassee_no = models.CharField(max_length=100, blank=True, null=True)
    engine_no = models.CharField(max_length=100, blank=True, null=True) 

    istemara_expiry_date = models.DateField()

    insurance_name = models.CharField(max_length=100)
    insurance_expiry_date = models.DateField()

    ownership = models.CharField(max_length=10, choices=OWNERSHIP_CHOICES)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehicle_setup_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehicle_setup_updated_by', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.plate_no} - {self.get_vehicle_type_display()}"
    
    class Meta:
        ordering = ['-created_at']

# ===========================================================
# Vehicle Purchase 
# ============================================================= 
class VehiclePurchase(models.Model):

    PAYMENT_METHOD_CHOICES = (
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
        ('ONLINE', 'Online'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('OTHER', 'Other'),
    )

    PAYMENT_PERIOD_CHOICES = (
        ("WEEKLY", "Weekly"),
        ("MONTHLY", "Monthly"),
    ) 

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='vehicle_purchases', null=True, blank=True)

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='vehicle_purchases')
    purchase_date = models.DateField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    down_payment = models.DecimalField(max_digits=10, decimal_places=2) 
    installment_amount = models.DecimalField(max_digits=10, decimal_places=2) 
    start_date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_period = models.CharField(max_length=20, choices=PAYMENT_PERIOD_CHOICES)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehicle_purchase_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehicle_purchase_updated_by', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True) 
    deleted = models.BooleanField(default=False) 

    def generate_installment_schedule(self, created_by):
        installments = []
        current_date = self.start_date
        installment_no = 1

        while self.down_payment + (installment_no - 1) * self.installment_amount < self.total_amount:
            installments.append(VehicleInstallment(
                purchase=self,
                installment_no=installment_no,
                amount=self.installment_amount,
                due_date=current_date,
                created_by=created_by
            ))
            if self.payment_period == 'WEEKLY':
                current_date += timedelta(weeks=1)
            elif self.payment_period == 'MONTHLY':
                current_date += timedelta(days=30) 
            installment_no += 1

        VehicleInstallment.objects.bulk_create(installments)    


    def __str__(self):
        return f"Purchase - {self.vehicle.plate_no} by {self.employee.full_name}" 
    
    class Meta:
        ordering = ['-purchase_date', '-created_at'] 


# =========================
# INSTALLMENT PAID / RECEIVED
# =========================
class VehicleInstallment(models.Model):
    PAYMENT_METHOD_CHOICES = (
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
        ('ONLINE', 'Online'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('OTHER', 'Other'),
    )
    PAYMENT_STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('OVERDUE', 'Overdue'),
        ('CANCELLED', 'Cancelled'),
    ) 

    purchase = models.ForeignKey(VehiclePurchase, on_delete=models.CASCADE, related_name='installments')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='CASH')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')

    installment_no = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    due_date = models.DateField()
    is_paid = models.BooleanField(default=False)
    paid_date = models.DateField(null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='installment_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='installment_updated_by', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"Installment {self.installment_no} - {self.purchase.vehicle.plate_no}"


class VehicleAssign(models.Model):
    STATUS_CHOICES = (
        ('ASSIGNED', 'Assigned'),
        ('RETURNED', 'Returned'),
    ) 
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='vehicle_assignments')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='vehicle_assignments') 

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ASSIGNED')
    assigned_date = models.DateField()
    remarks = models.TextField(blank=True, null=True) 

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehicle_assign_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehicle_assign_updated_by', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False) 

    def __str__(self):
        return f"{self.vehicle.plate_no} assigned to {self.employee.full_name}"
    
    class Meta:
        ordering = ['-assigned_date', '-created_at'] 


# =========================
# HAND OVER / TAKE OVER
# =========================
class VehicleHandover(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    from_employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, related_name='handover_from')
    to_employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, related_name='handover_to')
    handover_date = models.DateField()
    
    remarks = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehicle_handover_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehicle_handover_updated_by', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False) 

    def __str__(self):
        return f"Handover - {self.vehicle.plate_no}"
    
    class Meta:
        ordering = ['-handover_date', '-created_at']

class ViolationType(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='violation_type_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='violation_type_updated_by', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.name
    class Meta:
        ordering = ['name'] 

# =========================
# TRAFFIC VIOLATION
# =========================
class TrafficViolation(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='traffic_violations')
    violation_type = models.ForeignKey(ViolationType, on_delete=models.CASCADE, related_name='traffic_violations')
    place = models.CharField(max_length=200, blank=True, null=True)

    violation_date = models.DateField()
    
    remarks = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='traffic_violation_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='traffic_violation_updated_by', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"Violation - {self.vehicle.plate_no}"

    class Meta:
        ordering = ['-violation_date', '-created_at']


class TrafficViolationPenalty(models.Model):
    PAYMENT_STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('OVERDUE', 'Overdue'),
        ('CANCELLED', 'Cancelled'),
    ) 

    PAYMENT_METHOD_CHOICES = (
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
        ('ONLINE', 'Online'),
        ('BANK_TRANSFER', 'Bank Transfer'),
    ) 

    violation = models.ForeignKey(TrafficViolation, on_delete=models.CASCADE, related_name='penalties')

    fine_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_date = models.DateField(null=True, blank=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING') 
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='CASH', null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='violation_penalty_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='violation_penalty_updated_by', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"Penalty - {self.violation.vehicle.plate_no} - {self.fine_amount}"

    class Meta:
        ordering = ['-created_at']


# =========================
# ACCIDENT HISTORY
# =========================
class VehicleAccident(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='vehicle_accidents')

    accident_date = models.DateField()
    accident_place = models.CharField(max_length=200)

    damage_cost = models.DecimalField(max_digits=10, decimal_places=2)
    insurance_claimed = models.BooleanField(default=False)

    remarks = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accident_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accident_updated_by', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"Accident - {self.vehicle.plate_no}"


class InsuranceClaim(models.Model):
    CLAIM_STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('SETTLED', 'Settled'),
    ) 
    accident = models.ForeignKey(VehicleAccident, on_delete=models.CASCADE, related_name='insurance_claims')

    claim_amount = models.DecimalField(max_digits=10, decimal_places=2)
    claim_date = models.DateField()
    claim_status = models.CharField(max_length=20, choices=CLAIM_STATUS_CHOICES, default='PENDING')

    remarks = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='insurance_claim_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='insurance_claim_updated_by', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"Insurance Claim - {self.accident.vehicle.plate_no}" 
    



class VehicleMaintananceType(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='maintenance_type_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='maintenance_type_updated_by', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.name 

    class Meta:
        ordering = ['name'] 


# =========================
# MAINTENANCE
# =========================
class VehicleMaintenance(models.Model):

    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
    )

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='vehicle_maintenances')
    maintenance_type = models.ForeignKey(VehicleMaintananceType, on_delete=models.CASCADE, related_name='vehicle_maintenances')
    cost = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    maintenance_date = models.DateField()

    remarks = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='maintenance_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='maintenance_updated_by', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"Maintenance - {self.vehicle.plate_no}"

