from django import forms
from django.contrib.auth.models import User
from django import forms 
from backend.models import (
    Visitor, TrafficViolationPenalty, 
    Nationality, Employee, Employment, Passport, DrivingLicense, HealthInsurance, Contact, Address,
    Vehicle, VehicleHandover, TrafficViolation, VehicleInstallment, VehiclePurchase,
    VehicleMaintenance, VehicleAccident, VehicleAssign, ViolationType, InsuranceClaim, VehicleMaintananceType, 
    Uniform, UniformStock, UniformIssuance, UniformClearance, 
    UniformStockTransactionLog, 
)

TAILWIND_TEXT = (
    "h-11 w-full mt-1 rounded-lg bg-[var(--bg-color)] px-3 text-sm "
    "ring-1 ring-[var(--border-color)] outline-none "
    "focus:ring-[var(--primary-color)]/40"
)

TAILWIND_TEXTAREA = (
    "h-11 w-full mt-1 pt-2 rounded-lg bg-[var(--bg-color)] px-3 text-sm "
    "ring-1 ring-[var(--border-color)] outline-none "
    "focus:ring-[var(--primary-color)]/40"
)

TAILWIND_SELECT = (
    "select2-items h-11 w-full mt-1 appearance-none rounded-lg bg-[var(--bg-color)] px-3 pr-10 text-sm "
    "ring-1 ring-[var(--border-color)] outline-none "
    "focus:ring-[var(--primary-color)]/40"
)

GENDER_CHOICES = (
    ("male", "Male"),
    ("female", "Female"),
    ("other", "Other"),
)

class CustomUserLoginForm(forms.Form):
    """
    Custom form for user login.
    This form is used to authenticate users in the backend.
    """
    username = forms.CharField(
        max_length=150, required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Enter Your Username', 'class': 'h-14 w-full rounded-md border border-slate-200 bg-[#A5B4FC26] pl-9 pr-3 text-sm outline-none transition focus:border-brand-600 focus:bg-white'})
    )
    password = forms.CharField(
        max_length=128, required=True,
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter Your Password', 'class': 'h-14 w-full rounded-md border border-slate-200 bg-[#A5B4FC26] pl-9 pr-10 text-sm outline-none transition focus:border-brand-600 focus:bg-white'})
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        return username.strip() if username else username

    def clean_password(self):
        password = self.cleaned_data.get('password')
        return password


class UserCreateForm(forms.ModelForm):
    
    first_name = forms.CharField(
        label="Full Name",
        max_length=100,
        widget=forms.TextInput(attrs={
            "placeholder": "Enter full name",
            "class": TAILWIND_TEXT,
            "id": "first_name",
        })
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            "placeholder": "Enter email",
            "class": TAILWIND_TEXT,
            "id": "email",
        })
    )

    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": TAILWIND_TEXT}))
    date_of_birth = forms.DateField(required=False, widget=forms.DateInput(attrs={
        "type": "date",
        "class": TAILWIND_TEXT,
    }))

    phone = forms.CharField(
        label="Mobile No.",
        max_length=30,
        widget=forms.TextInput(attrs={
            "placeholder": "Enter phone number",
            "class": TAILWIND_TEXT,
            "id": "phone",
        })
    )
    gender = forms.ChoiceField(
        choices=GENDER_CHOICES,
        widget=forms.Select(attrs={
            "class": f'{TAILWIND_SELECT} select2-items',
            "id": "gender",
        })
    )
    profile_image = forms.ImageField(
        label="Profile Image",
        required=False,
        widget=forms.ClearableFileInput(attrs={
            "accept": "image/*",
            # we'll hide this in the template with sr-only
            "class": "sr-only",
            "id": "profile_image",
        })
    )

    class Meta:
        model = User
        fields = ["phone", "gender", "profile_image"]

    def clean_email(self):
        email = self.cleaned_data.get("email")
        # When editing, allow current user's email
        user_id = self.instance.user.pk if getattr(self.instance, "user", None) else None
        qs = User.objects.exclude(pk=user_id) if user_id else User.objects.all()
        if qs.filter(email=email).exists():
            raise forms.ValidationError("This email is already taken.")
        return email

    def save(self, commit=True):
        """
        Create/update the related auth User and the AdminUser profile.
        """
        admin_user = super().save(commit=False)

        # Use existing related user if editing; otherwise create new
        user = getattr(self.instance, "user", None)
        if not user:
            user = User()

        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")
        user.email = self.cleaned_data.get("email")
        user.username = user.email  # use email as username

        # Set a default password only when creating a new user
        if not user.pk:
            user.set_password("12345678")

        if commit:
            user.save()
            admin_user.user = user
            admin_user.save()
            # handle file after save_m2m if you add more relations later

        return admin_user


class NationalityForm(forms.ModelForm):
    code = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={
            "placeholder": "(e.g., US, UK, IN)",
            "class": TAILWIND_TEXT,
        })
    )
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "placeholder": "(e.g., United States)",
            "class": TAILWIND_TEXT,
        })
    )
    
    class Meta:
        model = Nationality
        exclude = ['created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']


class VisitorForm(forms.ModelForm):
    class Meta:
        model = Visitor
        exclude = ['created_at', 'is_active', 'deleted']

        widgets = {
            'first_name': forms.TextInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter first name'}),
            'last_name': forms.TextInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter last name'}),
            'phone_number': forms.TextInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter phone number'}),
            'email': forms.EmailInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter email address'}), 
        }


class EmployeeForm(forms.ModelForm):
    gender = forms.ChoiceField(
        choices=[('', 'Select Gender'), ('M', 'Male'), ('F', 'Female')],
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    )
    
    class Meta:
        model = Employee
        exclude = ['user', 'hr_file_no', 'joining_at', 'created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']

        widgets = {
            'qid_no': forms.TextInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter QID number'}),
            'first_name': forms.TextInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter first name'}),
            'last_name': forms.TextInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter last name'}),
            'phone_number': forms.TextInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter phone number'}),
            'email': forms.EmailInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter email address'}), 
            'nationality': forms.Select(attrs={'class': TAILWIND_SELECT}),
            'remarks': forms.Textarea(attrs={'class': TAILWIND_TEXTAREA, 'rows': 3, 'placeholder': 'Enter remarks'}),
        }

class UniformForm(forms.ModelForm):
    uniform_type = forms.ChoiceField(
        choices=[('', 'Select Uniform Type'), ('SHIRT', 'Shirt'), ('PANT', 'Pant'), ('JACKET', 'Jacket'), ('SHOES', 'Shoes'), ('CAP', 'Cap'), ('OTHER', 'Other'),],
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    ) 
    class Meta:
        model = Uniform
        exclude = ['created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']
        widgets = {
            'name': forms.TextInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter uniform name'}),
            'description': forms.Textarea(attrs={'class': TAILWIND_TEXTAREA, 'rows': 3, 'placeholder': 'Enter description'}),
        }

class UniformStockForm(forms.ModelForm):
    uniform = forms.ModelChoiceField(
        queryset=Uniform.objects.filter(is_active=True),
        empty_label="Select Uniform",
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    ) 

    size = forms.ChoiceField(
        choices=[(
            '', 'Select Size'), 
            ('XS', 'Extra Small'),
            ('S', 'Small'),
            ('M', 'Medium'),
            ('L', 'Large'),
            ('XL', 'Extra Large'),
            ('XXL', 'Double Extra Large'),
            ],
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    ) 

    class Meta:
        model = UniformStock
        exclude = ['code', 'created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']
        widgets = {
            'quantity': forms.NumberInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter quantity'}),
        }

class UniformIssuanceForm(forms.ModelForm):
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.filter(is_active=True),
        empty_label="Select Employee",
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    ) 

    uniform_stock = forms.ModelChoiceField(
        queryset=UniformStock.objects.filter(is_active=True),
        empty_label="Select Uniform Stock",
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    ) 

    status = forms.ChoiceField(
        choices=[(
            '', 'Select Status'),  
            ('ISSUED', 'Issued'),
            ('RETURNED', 'Returned'),
            ('LOST', 'Lost'),
            ('DAMAGED', 'Damaged'),
        ],
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    )

    class Meta:
        model = UniformIssuance
        exclude = ['issued_by', 'created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']
        widgets = {
            'issued_date': forms.DateInput(attrs={'class': TAILWIND_TEXT, 'type': 'date'}),
            'return_date': forms.DateInput(attrs={'class': TAILWIND_TEXT, 'type': 'date'}),
            'quantity': forms.NumberInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter quantity'}),
            'expected_return_date': forms.DateInput(attrs={'class': TAILWIND_TEXT, 'type': 'date'}),
            'remark': forms.Textarea(attrs={'class': TAILWIND_TEXTAREA, 'rows': 3, 'placeholder': 'Enter remarks'}),
        }

class UniformClearanceForm(forms.ModelForm):
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.filter(is_active=True),
        empty_label="Select Employee",
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    ) 

    uniform_stock = forms.ModelChoiceField(
        queryset=UniformStock.objects.filter(is_active=True),
        empty_label="Select Uniform Stock",
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    ) 


    status = forms.ChoiceField(
        choices=[(
            '', 'Select Status'),  
            ('RETURNED', 'Returned'),
            ('LOST', 'Lost'),
            ('DAMAGED', 'Damaged'),
        ],
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    )

    class Meta:
        model = UniformClearance
        exclude = ['cleared_by', 'created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']
        widgets = {
            'quantity': forms.NumberInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter quantity'}),
            'clearance_date': forms.DateInput(attrs={'class': TAILWIND_TEXT, 'type': 'date'}),
            'remark': forms.Textarea(attrs={'class': TAILWIND_TEXTAREA, 'rows': 3, 'placeholder': 'Enter remarks'}),
        }

class EmploymentForm(forms.ModelForm):
    work_status = forms.ChoiceField(
        choices=[('', 'Select Status'), ('ACTIVE', 'Active'), ('INACTIVE', 'Inactive'), ('ON_LEAVE', 'On Leave'), ('TERMINATED', 'Terminated')],
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    )
    qid_renew_status = forms.ChoiceField(
        choices=[('', 'Select Status'), ('NOT_DUE', 'Not Due'), ('PENDING', 'Pending'), ('RENEWED', 'Renewed')],
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    )
    qid_lost_status = forms.ChoiceField(
        choices=[('', 'Select Status'), ('YES', 'Yes'), ('NO', 'No')],
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    )
    
    class Meta:
        model = Employment
        exclude = ['employee', 'created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']
        widgets = {
            'joining_at': forms.DateInput(attrs={'class': TAILWIND_TEXT, 'type': 'date'}),
            'rp_expiry_date': forms.DateInput(attrs={'class': TAILWIND_TEXT, 'type': 'date'}),
            'work_permit_no': forms.TextInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter work permit number'}),
            'work_id': forms.TextInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter work ID'}),
        }

class PassportForm(forms.ModelForm):
    class Meta:
        model = Passport
        exclude = ['employee', 'created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']
        widgets = {
            'passport_no': forms.TextInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter passport number'}),
            'passport_expiry_date': forms.DateInput(attrs={'class': TAILWIND_TEXT, 'type': 'date'}),
            'passport_renewed': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded text-blue-600'}),
        }

class DrivingLicenseForm(forms.ModelForm):
    license_renew_status = forms.ChoiceField(
        choices=[('', 'Select Status'), ('YES', 'Renewed'), ('NO', 'Not Renewed')],
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    )
    
    class Meta:
        model = DrivingLicense
        exclude = ['employee', 'created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']
        widgets = {
            'license_no': forms.TextInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter license number'}),
            'license_expiry_date': forms.DateInput(attrs={'class': TAILWIND_TEXT, 'type': 'date'}),
            'license_renewed': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded text-blue-600'}),
        }

class HealthInsuranceForm(forms.ModelForm):
    wm_insurance = forms.ChoiceField(
        choices=[('', 'Select Status'), ('YES', 'Yes'), ('NO', 'No')],
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    )
    family_health_card = forms.ChoiceField(
        choices=[('', 'Select Status'), ('YES', 'Yes'), ('NO', 'No')],
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    )
    
    class Meta:
        model = HealthInsurance
        exclude = ['employee', 'created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']
        widgets = {
            'hamad_health_card': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded text-blue-600'}),
        }

class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        exclude = ['employee', 'created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']
        widgets = {
            'phone_no': forms.TextInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter phone number'}),
            'phone_no_alt': forms.TextInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter alternate phone number'}),
            'roommate_phone': forms.TextInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter roommate phone'}),
            'relative_qatar_phone': forms.TextInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter relative Qatar phone'}),
            'home_phone': forms.TextInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter home phone'}),
            'home_phone_alt': forms.TextInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter alternate home phone'}),
            'home_email': forms.EmailInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter email address'}),
        }

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        exclude = ['employee', 'created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']
        widgets = {
            'present_address': forms.Textarea(attrs={'class': TAILWIND_TEXTAREA, 'rows': 3, 'placeholder': 'Enter present address'}),
            'permanent_address': forms.Textarea(attrs={'class': TAILWIND_TEXTAREA, 'rows': 3, 'placeholder': 'Enter permanent address'}),
            'national_address': forms.Textarea(attrs={'class': TAILWIND_TEXTAREA, 'rows': 3, 'placeholder': 'Enter national address'}),
            'room_address': forms.Textarea(attrs={'class': TAILWIND_TEXTAREA, 'rows': 3, 'placeholder': 'Enter room address'}),
        }

class VehicleForm(forms.ModelForm):
    vehicle_type = forms.ChoiceField(
        choices=[('', 'Select Vehicle Type'), ('BIKE', 'Bike'), ('CAR', 'Car')],
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    )
    ownership = forms.ChoiceField(
        choices=[('', 'Select Ownership'), ('COMPANY', 'Company'), ('DRIVER', 'Driver')],
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    )
    
    class Meta:
        model = Vehicle
        exclude = ['created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']
        widgets = {
            'plate_no': forms.TextInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter plate number'}),
            'chassee_no': forms.TextInput(attrs={'class': TAILWIND_TEXT}),
            'engine_no': forms.TextInput(attrs={'class': TAILWIND_TEXT}), 
            'istemara_expiry_date': forms.DateInput(attrs={'class': TAILWIND_TEXT, 'type': 'date'}),
            'insurance_name': forms.TextInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter insurance name'}),
            'insurance_expiry_date': forms.DateInput(attrs={'class': TAILWIND_TEXT, 'type': 'date'}),
        }


class VehicleAssignForm(forms.ModelForm):
    vehicle = forms.ModelChoiceField(
        queryset=Vehicle.objects.filter(is_active=True),
        empty_label="Select Vehicle",
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    ) 
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.filter(is_active=True),
        empty_label="Select Employee",
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    ) 
    class Meta:
        model = VehicleAssign
        exclude = ['created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']
        widgets = {
            'assign_date': forms.DateInput(attrs={'class': TAILWIND_TEXT, 'type': 'date'}),
            'remarks': forms.Textarea(attrs={'class': TAILWIND_TEXTAREA, 'rows': 3, 'placeholder': 'Enter remarks'}),
        }

class VehicleHandoverForm(forms.ModelForm):
    vehicle = forms.ModelChoiceField(
        queryset=Vehicle.objects.filter(is_active=True),
        empty_label="Select Vehicle",
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    )
    from_employee = forms.ModelChoiceField(
        queryset=Employee.objects.filter(is_active=True),
        empty_label="Select From Employee",
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    )
    to_employee = forms.ModelChoiceField(
        queryset=Employee.objects.filter(is_active=True),
        empty_label="Select To Employee",
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    ) 
    class Meta:
        model = VehicleHandover
        exclude = ['created_by', 'created_at', 'is_active']
        widgets = {
            'handover_date': forms.DateInput(attrs={'class': TAILWIND_TEXT, 'type': 'date'}),
            'remarks': forms.Textarea(attrs={'class': TAILWIND_TEXTAREA, 'rows': 3, 'placeholder': 'Enter remarks'}),
        }


class ViolationTypeForm(forms.ModelForm):
    class Meta:
        model = ViolationType
        exclude = ['created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']
        widgets = {
            'name': forms.TextInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter violation type name'}),
            'description': forms.Textarea(attrs={'class': TAILWIND_TEXTAREA, 'rows': 3, 'placeholder': 'Enter description'}),
        }

class TrafficViolationForm(forms.ModelForm):
    vehicle = forms.ModelChoiceField(
        queryset=Vehicle.objects.filter(is_active=True),
        empty_label="Select Vehicle",
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    )
    violation_type = forms.ModelChoiceField(
        queryset=ViolationType.objects.filter(is_active=True),
        empty_label="Select Violation Type",
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    )
    class Meta:
        model = TrafficViolation
        exclude = ['created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']
        widgets = {
            'place': forms.TextInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'violation place'}), 
            'violation_date': forms.DateInput(attrs={'class': TAILWIND_TEXT, 'type': 'date'}),
            'remarks': forms.Textarea(attrs={'class': TAILWIND_TEXTAREA, 'rows': 3, 'placeholder': 'Enter remarks'}),
        }

class TrafficViolationPenaltyForm(forms.ModelForm):
    violation = forms.ModelChoiceField(
        queryset=TrafficViolation.objects.filter(is_active=True),
        empty_label="Select Violation",
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    ) 
    payment_status = forms.ChoiceField(
        choices=[('', 'Select Status'), ('PENDING', 'Pending'), ('PAID', 'Paid'), ('OVERDUE', 'Overdue'), ('CANCELLED', 'Cancelled')],
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    )
    payment_method = forms.ChoiceField(
        choices=[('', 'Select Method'), ('CASH', 'Cash'), ('CARD', 'Card'), ('ONLINE', 'Online'), ('BANK_TRANSFER', 'Bank Transfer')],
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    )
    
    class Meta:
        model = TrafficViolationPenalty
        exclude = ['created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']
        widgets = {
            # 'violation': forms.Select(attrs={'class': TAILWIND_SELECT}),
            'fine_amount': forms.NumberInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter fine amount'}),
            'paid_date': forms.DateInput(attrs={'class': TAILWIND_TEXT, 'type': 'date'}),
            'remarks': forms.Textarea(attrs={'class': TAILWIND_TEXTAREA, 'rows': 3, 'placeholder': 'Enter remarks'}),
        }


class VehicleInstallmentForm(forms.ModelForm):
    purchase = forms.ModelChoiceField(
        queryset=VehiclePurchase.objects.filter(is_active=True, deleted=False),
        empty_label="Select Purchase",
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    ) 
    class Meta:
        model = VehicleInstallment
        exclude = ['created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']
        widgets = {
            'installment_no': forms.NumberInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter installment number'}),
            'amount': forms.NumberInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter amount'}),
            'due_date': forms.DateInput(attrs={'class': TAILWIND_TEXT, 'type': 'date'}),
            'is_paid': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded text-blue-600'}),
            'paid_date': forms.DateInput(attrs={'class': TAILWIND_TEXT, 'type': 'date'}),
            'payment_method': forms.Select(attrs={'class': TAILWIND_SELECT}),
            'payment_status': forms.Select(attrs={'class': TAILWIND_SELECT}),
            'remarks': forms.Textarea(attrs={'class': TAILWIND_TEXTAREA, 'rows': 3, 'placeholder': 'Enter remarks'}),
        }


class VehicleMaintananceTypeForm(forms.ModelForm):
    class Meta:
        model = VehicleMaintananceType
        exclude = ['created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']
        widgets = {
            'name': forms.TextInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter maintenance type name'}),
            'description': forms.Textarea(attrs={'class': TAILWIND_TEXTAREA, 'rows': 3, 'placeholder': 'Enter description'}),
        } 

class VehicleMaintenanceForm(forms.ModelForm):
    vehicle = forms.ModelChoiceField(
        queryset=Vehicle.objects.filter(is_active=True),
        empty_label="Select Vehicle",
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    ) 
    maintenance_type = forms.ModelChoiceField(
        queryset=VehicleMaintananceType.objects.filter(is_active=True),
        empty_label="Select Maintenance Type",
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    ) 
    status = forms.ChoiceField(
        choices=[('', 'Select Status'), ('PENDING', 'Pending'), ('IN_PROGRESS', 'In Progress'), ('COMPLETED', 'Completed')],
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    )
    
    class Meta:
        model = VehicleMaintenance
        exclude = ['created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']
        widgets = {
            # 'vehicle': forms.Select(attrs={'class': TAILWIND_SELECT}),
            # 'maintenance_type': forms.Select(attrs={'class': TAILWIND_SELECT}),
            'cost': forms.NumberInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter cost'}),
            'maintenance_date': forms.DateInput(attrs={'class': TAILWIND_TEXT, 'type': 'date'}),
            'remarks': forms.Textarea(attrs={'class': TAILWIND_TEXTAREA, 'rows': 3, 'placeholder': 'Enter remarks'}),
        }

class VehicleAccidentForm(forms.ModelForm):
    vehicle = forms.ModelChoiceField(
        queryset=Vehicle.objects.filter(is_active=True),
        empty_label="Select Vehicle",
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    )
    class Meta:
        model = VehicleAccident
        exclude = ['insurance_claimed', 'created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted'] 
        widgets = {
            # 'vehicle': forms.Select(attrs={'class': TAILWIND_SELECT}),
            'accident_date': forms.DateInput(attrs={'class': TAILWIND_TEXT, 'type': 'date'}),
            'accident_place': forms.TextInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter accident place'}),
            'damage_cost': forms.NumberInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter damage cost'}),
            'remarks': forms.Textarea(attrs={'class': TAILWIND_TEXTAREA, 'rows': 3, 'placeholder': 'Enter remarks'}),
        }



class InsuranceClaimForm(forms.ModelForm):
    accident = forms.ModelChoiceField(
        queryset=VehicleAccident.objects.filter(is_active=True),
        empty_label="Select Accident",
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    )
    claim_status = forms.ChoiceField(
        choices=[('', 'Select Status'), ('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('SETTLED', 'Settled')],
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    )
    
    class Meta:
        model = InsuranceClaim
        exclude = ['created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']
        widgets = {
            # 'accident': forms.Select(attrs={'class': TAILWIND_SELECT}),
            'claim_date': forms.DateInput(attrs={'class': TAILWIND_TEXT, 'type': 'date'}),
            'claim_amount': forms.NumberInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter claim amount'}),
            'remarks': forms.Textarea(attrs={'class': TAILWIND_TEXTAREA, 'rows': 3, 'placeholder': 'Enter remarks'}),
        }


class VehiclePurchaseForm(forms.ModelForm):
    vehicle_type = forms.ChoiceField(
        choices=[('', 'Select Vehicle Type'), ('BIKE', 'Bike'), ('CAR', 'Car')],
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    ) 
    ownership = forms.ChoiceField(
        choices=[('', 'Select Ownership'), ('COMPANY', 'Company'), ('DRIVER', 'Driver')],
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    )    
    plate_no = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter plate number'})
    ) 
    chassee_no = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter chassee number'})
    )
    engine_no = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter engine number'})
    )  
    istemara_expiry_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': TAILWIND_TEXT, 'type': 'date'})
    )
    insurance_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter insurance provider'})
    )
    insurance_expiry_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': TAILWIND_TEXT, 'type': 'date'})
    )
    payment_method = forms.ChoiceField(
        choices=[('', 'Select Payment Method'), ('CASH', 'Cash'), ('CARD', 'Card'), ('ONLINE', 'Online'), ('BANK_TRANSFER', 'Bank Transfer'), ('OTHER', 'Other')],
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    )
    payment_period = forms.ChoiceField(
        choices=[('', 'Select Payment Period'), ('WEEKLY', 'Weekly'), ('MONTHLY', 'Monthly')],
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    )
    
    class Meta:
        model = VehiclePurchase
        exclude = [ 'employee', 'vehicle', 'created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']
        widgets = {
            'purchase_date': forms.DateInput(attrs={'class': TAILWIND_TEXT, 'type': 'date'}),
            'total_amount': forms.NumberInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter total amount'}),
            'down_payment': forms.NumberInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter down payment'}),
            'installment_amount': forms.NumberInput(attrs={'class': TAILWIND_TEXT, 'placeholder': 'Enter installment amount'}),
            'start_date': forms.DateInput(attrs={'class': TAILWIND_TEXT, 'type': 'date'}),
        }

    def clean_plate_no(self):
        plate_no = self.cleaned_data.get('plate_no', '').strip()
        if not plate_no:
            raise forms.ValidationError("Plate number is required.")
        return plate_no


class InstallmentPaymentForm(forms.ModelForm):
    payment_method = forms.ChoiceField(
        choices=[('CASH', 'Cash'), ('CARD', 'Card'), ('ONLINE', 'Online'), ('BANK_TRANSFER', 'Bank Transfer'), ('OTHER', 'Other')],
        widget=forms.Select(attrs={'class': TAILWIND_SELECT})
    )
    
    class Meta:
        model = VehicleInstallment
        fields = ['payment_method', 'remarks']
        widgets = {
            'remarks': forms.Textarea(attrs={'class': TAILWIND_TEXTAREA, 'rows': 3, 'placeholder': 'Enter remarks (optional)'}),
        }

