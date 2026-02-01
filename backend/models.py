from django.db import models
from django.contrib.auth.models import User 
from django.utils import timezone


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
        return f"{self.employee.name} - {self.work_permit_no}"

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
        return f"Passport - {self.employee.name}"
    
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
        return f"Driving License - {self.employee.name}"
    
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
        return f"Health & Insurance - {self.employee.name}"
    
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
        return f"Contact - {self.employee.name}"
    
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
        return f"Address - {self.employee.name}"
    
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
        return f"Vehicle - {self.employee.name}"

    class Meta:
        ordering = ['-created_at']