from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.core.paginator import PageNotAnInteger, EmptyPage
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.contrib.auth.models import User


from backend.models import Nationality, Employee, Employment, Passport, DrivingLicense, HealthInsurance, Contact, Address, Vehicle
from backend.forms import NationalityForm, EmployeeForm, EmploymentForm, PassportForm, DrivingLicenseForm, HealthInsuranceForm, ContactForm, AddressForm, VehicleForm


def paginate_data(request, page_num, data_list):
    items_per_page, max_pages = 10, 10 
    paginator = Paginator(data_list, items_per_page)
    last_page_number = paginator.num_pages 

    try:
        data_list = paginator.page(page_num)
    except PageNotAnInteger:
        data_list = paginator.page(1)
    except EmptyPage:
        data_list = paginator.page(last_page_number)

    current_page = data_list.number
    start_page = max(current_page - int(max_pages / 2), 1)
    end_page = start_page + max_pages

    if end_page > last_page_number:
        end_page = last_page_number + 1
        start_page = max(end_page - max_pages, 1)

    paginator_list = range(start_page, end_page)

    return data_list, paginator_list, last_page_number


@method_decorator(login_required, name='dispatch')
class NationalityListView(ListView):
    model = Nationality
    template_name = "nationality/list.html"
    paginate_by = None 

    def get_queryset(self):
        filters = {
            'is_active': True, 
        } 

        name = self.request.GET.get('name', '') 
        code = self.request.GET.get('code', '')

        if name:
           filters['name__icontains'] = name
        if code:
            filters['code__icontains'] = code

        return Nationality.objects.filter(**filters)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nationalities'] = self.get_queryset()
        context['page_num'] = self.request.GET.get('page', 1)
        context['paginator_list'], context['paginator'], context['last_page_number'] = paginate_data(self.request, context['page_num'], context['nationalities'])

        get_param = self.request.GET.copy()
        if 'page' in get_param:
            get_param.pop('page')
        context['get_param'] = get_param.urlencode() 
        return context
    
@method_decorator(login_required, name='dispatch')
class NationalityCreateView(CreateView):
    model = Nationality
    template_name = "nationality/create.html"
    form_class = NationalityForm
    success_url = reverse_lazy('nationality:list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form) 
    
@method_decorator(login_required, name='dispatch')
class NationalityUpdateView(UpdateView):
    model = Nationality
    template_name = "nationality/update.html"
    form_class = NationalityForm
    success_url = reverse_lazy('nationality:list')

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form) 
    
@login_required
def nationality_delete(request, pk):
    nationality = Nationality.objects.get(pk=pk)
    nationality.is_active = False
    nationality.save()
    return redirect('nationality:list') 



@login_required
def employee_create(request):
    if request.method == 'POST':
        employee_form = EmployeeForm(request.POST, request.FILES, prefix='employee')
        employment_form = EmploymentForm(request.POST, prefix='employment')
        passport_form = PassportForm(request.POST, prefix='passport')
        driving_license_form = DrivingLicenseForm(request.POST, prefix='driving_license')
        health_insurance_form = HealthInsuranceForm(request.POST, prefix='health_insurance')
        contact_form = ContactForm(request.POST, prefix='contact')
        address_form = AddressForm(request.POST, prefix='address')
        vehicle_form = VehicleForm(request.POST, prefix='vehicle')

        if employee_form.is_valid():
            # Create User account from first_name and last_name
            employee = employee_form.save(commit=False)
            username = f"{employee.first_name.lower()}.{employee.last_name.lower()}".replace(' ', '')
            
            # Check if username exists, add number if needed
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            # Create User with default password "admin"
            user = User.objects.create_user(
                username=username,
                first_name=employee.first_name,
                last_name=employee.last_name,
                password='admin'
            )
            
            # Save employee
            employee.user = user
            employee.created_by = request.user
            employee.updated_by = request.user
            employee.save()

            # Save Employment if data provided
            if employment_form.is_valid():
                has_data = any([
                    v for k, v in employment_form.cleaned_data.items() 
                    if v not in [None, '', []]
                ])
                if has_data:
                    employment = employment_form.save(commit=False)
                    employment.employee = employee
                    employment.created_by = request.user
                    employment.updated_by = request.user
                    employment.save()

            # Save Passport if data provided
            if passport_form.is_valid():
                has_data = any([
                    v for k, v in passport_form.cleaned_data.items() 
                    if v not in [None, '', []]
                ])
                if has_data:
                    passport = passport_form.save(commit=False)
                    passport.employee = employee
                    passport.created_by = request.user
                    passport.updated_by = request.user
                    passport.save()

            # Save Driving License if data provided
            if driving_license_form.is_valid():
                has_data = any([
                    v for k, v in driving_license_form.cleaned_data.items() 
                    if v not in [None, '', []]
                ])
                if has_data:
                    driving_license = driving_license_form.save(commit=False)
                    driving_license.employee = employee
                    driving_license.created_by = request.user
                    driving_license.updated_by = request.user
                    driving_license.save()

            # Save Health Insurance if data provided
            if health_insurance_form.is_valid():
                has_data = any([
                    v for k, v in health_insurance_form.cleaned_data.items() 
                    if v not in [None, '', []]
                ])
                if has_data:
                    health_insurance = health_insurance_form.save(commit=False)
                    health_insurance.employee = employee
                    health_insurance.created_by = request.user
                    health_insurance.updated_by = request.user
                    health_insurance.save()

            # Save Contact if data provided
            if contact_form.is_valid():
                has_data = any([
                    v for k, v in contact_form.cleaned_data.items() 
                    if v not in [None, '', []]
                ])
                if has_data:
                    contact = contact_form.save(commit=False)
                    contact.employee = employee
                    contact.created_by = request.user
                    contact.updated_by = request.user
                    contact.save()

            # Save Address if data provided
            if address_form.is_valid():
                has_data = any([
                    v for k, v in address_form.cleaned_data.items() 
                    if v not in [None, '', []]
                ])
                if has_data:
                    address = address_form.save(commit=False)
                    address.employee = employee
                    address.created_by = request.user
                    address.updated_by = request.user
                    address.save()

            # Save Vehicle if data provided
            if vehicle_form.is_valid():
                has_data = any([
                    v for k, v in vehicle_form.cleaned_data.items() 
                    if v not in [None, '', []]
                ])
                if has_data:
                    vehicle = vehicle_form.save(commit=False)
                    vehicle.employee = employee
                    vehicle.created_by = request.user
                    vehicle.updated_by = request.user
                    vehicle.save()

            return redirect('employee:list')
    else:
        employee_form = EmployeeForm(prefix='employee')
        employment_form = EmploymentForm(prefix='employment')
        passport_form = PassportForm(prefix='passport')
        driving_license_form = DrivingLicenseForm(prefix='driving_license')
        health_insurance_form = HealthInsuranceForm(prefix='health_insurance')
        contact_form = ContactForm(prefix='contact')
        address_form = AddressForm(prefix='address')
        vehicle_form = VehicleForm(prefix='vehicle')

    context = {
        'employee_form': employee_form,
        'employment_form': employment_form,
        'passport_form': passport_form,
        'driving_license_form': driving_license_form,
        'health_insurance_form': health_insurance_form,
        'contact_form': contact_form,
        'address_form': address_form,
        'vehicle_form': vehicle_form,
        'nationalities': Nationality.objects.filter(is_active=True),
    }

    return render(request, "employee/create.html", context)


@login_required
def employee_update(request, pk):
    employee = Employee.objects.get(pk=pk)
    
    # Get related objects or None
    employment = Employment.objects.filter(employee=employee, is_active=True).first()
    passport = Passport.objects.filter(employee=employee, is_active=True).first()
    driving_license = DrivingLicense.objects.filter(employee=employee, is_active=True).first()
    health_insurance = HealthInsurance.objects.filter(employee=employee, is_active=True).first()
    contact = Contact.objects.filter(employee=employee, is_active=True).first()
    address = Address.objects.filter(employee=employee, is_active=True).first()
    vehicle = Vehicle.objects.filter(employee=employee, is_active=True).first()

    if request.method == 'POST':
        employee_form = EmployeeForm(request.POST, request.FILES, instance=employee, prefix='employee')
        employment_form = EmploymentForm(request.POST, instance=employment, prefix='employment')
        passport_form = PassportForm(request.POST, instance=passport, prefix='passport')
        driving_license_form = DrivingLicenseForm(request.POST, instance=driving_license, prefix='driving_license')
        health_insurance_form = HealthInsuranceForm(request.POST, instance=health_insurance, prefix='health_insurance')
        contact_form = ContactForm(request.POST, instance=contact, prefix='contact')
        address_form = AddressForm(request.POST, instance=address, prefix='address')
        vehicle_form = VehicleForm(request.POST, instance=vehicle, prefix='vehicle')

        if employee_form.is_valid():
            employee = employee_form.save(commit=False)
            
            # Update User first_name and last_name if user exists
            if employee.user:
                employee.user.first_name = employee.first_name
                employee.user.last_name = employee.last_name
                employee.user.save()
            else:
                # Create User if doesn't exist
                username = f"{employee.first_name.lower()}.{employee.last_name.lower()}".replace(' ', '')
                base_username = username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1
                
                user = User.objects.create_user(
                    username=username,
                    first_name=employee.first_name,
                    last_name=employee.last_name,
                    password='admin'
                )
                employee.user = user
            
            employee.updated_by = request.user
            employee.save()

            # Update or Create Employment
            if employment_form.is_valid():
                # Check if any field has a value (not just empty strings or None)
                has_data = any([
                    v for k, v in employment_form.cleaned_data.items() 
                    if v not in [None, '', []]
                ])
                if has_data:
                    emp_obj = employment_form.save(commit=False)
                    emp_obj.employee = employee
                    emp_obj.updated_by = request.user
                    if not employment:
                        emp_obj.created_by = request.user
                    emp_obj.save()

            # Update or Create Passport
            if passport_form.is_valid():
                has_data = any([
                    v for k, v in passport_form.cleaned_data.items() 
                    if v not in [None, '', []]
                ])
                if has_data:
                    pass_obj = passport_form.save(commit=False)
                    pass_obj.employee = employee
                    pass_obj.updated_by = request.user
                    if not passport:
                        pass_obj.created_by = request.user
                    pass_obj.save()

            # Update or Create Driving License
            if driving_license_form.is_valid():
                has_data = any([
                    v for k, v in driving_license_form.cleaned_data.items() 
                    if v not in [None, '', []]
                ])
                if has_data:
                    dl_obj = driving_license_form.save(commit=False)
                    dl_obj.employee = employee
                    dl_obj.updated_by = request.user
                    if not driving_license:
                        dl_obj.created_by = request.user
                    dl_obj.save()

            # Update or Create Health Insurance
            if health_insurance_form.is_valid():
                has_data = any([
                    v for k, v in health_insurance_form.cleaned_data.items() 
                    if v not in [None, '', []]
                ])
                if has_data:
                    hi_obj = health_insurance_form.save(commit=False)
                    hi_obj.employee = employee
                    hi_obj.updated_by = request.user
                    if not health_insurance:
                        hi_obj.created_by = request.user
                    hi_obj.save()

            # Update or Create Contact
            if contact_form.is_valid():
                has_data = any([
                    v for k, v in contact_form.cleaned_data.items() 
                    if v not in [None, '', []]
                ])
                if has_data:
                    contact_obj = contact_form.save(commit=False)
                    contact_obj.employee = employee
                    contact_obj.updated_by = request.user
                    if not contact:
                        contact_obj.created_by = request.user
                    contact_obj.save()

            # Update or Create Address
            if address_form.is_valid():
                has_data = any([
                    v for k, v in address_form.cleaned_data.items() 
                    if v not in [None, '', []]
                ])
                if has_data:
                    addr_obj = address_form.save(commit=False)
                    addr_obj.employee = employee
                    addr_obj.updated_by = request.user
                    if not address:
                        addr_obj.created_by = request.user
                    addr_obj.save()

            # Update or Create Vehicle
            if vehicle_form.is_valid():
                has_data = any([
                    v for k, v in vehicle_form.cleaned_data.items() 
                    if v not in [None, '', []]
                ])
                if has_data:
                    veh_obj = vehicle_form.save(commit=False)
                    veh_obj.employee = employee
                    veh_obj.updated_by = request.user
                    if not vehicle:
                        veh_obj.created_by = request.user
                    veh_obj.save()

            return redirect('employee:list')
    else:
        employee_form = EmployeeForm(instance=employee, prefix='employee')
        employment_form = EmploymentForm(instance=employment, prefix='employment')
        passport_form = PassportForm(instance=passport, prefix='passport')
        driving_license_form = DrivingLicenseForm(instance=driving_license, prefix='driving_license')
        health_insurance_form = HealthInsuranceForm(instance=health_insurance, prefix='health_insurance')
        contact_form = ContactForm(instance=contact, prefix='contact')
        address_form = AddressForm(instance=address, prefix='address')
        vehicle_form = VehicleForm(instance=vehicle, prefix='vehicle')

    context = {
        'employee': employee,
        'employee_form': employee_form,
        'employment_form': employment_form,
        'passport_form': passport_form,
        'driving_license_form': driving_license_form,
        'health_insurance_form': health_insurance_form,
        'contact_form': contact_form,
        'address_form': address_form,
        'vehicle_form': vehicle_form,
        'nationalities': Nationality.objects.filter(is_active=True),
    }
    return render(request, "employee/update.html", context)




@method_decorator(login_required, name='dispatch')
class EmployeeListView(ListView):
    model = Employee 
    template_name = "employee/list.html"
    paginate_by = None 

    def get_queryset(self):
        filters = {
            'is_active': True, 
        }
        
        name = self.request.GET.get('name', '') 
        qid_no = self.request.GET.get('qid_no', '')
        hr_file_no = self.request.GET.get('hr_file_no', '')
        nationality = self.request.GET.get('nationality', '')
        gender = self.request.GET.get('gender', '')
        joining_date = self.request.GET.get('joining_date', '')
        
        if qid_no:
            filters['qid_no__icontains'] = qid_no
        if hr_file_no:
            filters['hr_file_no__icontains'] = hr_file_no
        if nationality:
            filters['nationality__icontains'] = nationality
        if gender:
            filters['gender__icontains'] = gender
        if joining_date:
            filters['joining_date__icontains'] = joining_date
       
        if name:
           # Search in both first_name and last_name
           from django.db.models import Q
           return Employee.objects.filter(**filters).filter(
               Q(first_name__icontains=name) | Q(last_name__icontains=name)
           )
        
        return Employee.objects.filter(**filters)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employees'] = self.get_queryset()
        context['page_num'] = self.request.GET.get('page', 1)
        context['paginator_list'], context['paginator'], context['last_page_number'] = paginate_data(self.request, context['page_num'], context['employees'])

        get_param = self.request.GET.copy()
        if 'page' in get_param:
            get_param.pop('page')
        context['get_param'] = get_param.urlencode() 
        return context 



@login_required
def employee_delete(request, pk):
    employee = Employee.objects.get(pk=pk)
    employee.is_active = False
    employee.save()
    return redirect('employee:list') 


@method_decorator(login_required, name='dispatch')
class EmployeeDetailView(DetailView):
    model = Employee 
    template_name = "employee/detail.html" 
    context_object_name = 'employee'


@method_decorator(login_required, name='dispatch')
class EmployeementListView(ListView):
    model = Employment 
    template_name = "employeement/list.html"
    context_object_name = 'employeements'

    def get_queryset(self):
        filters = {
            'is_active': True, 
        }
        
        employee = self.request.GET.get('employee', '') 
        work_status = self.request.GET.get('work_status', '')
        qid_renew_status = self.request.GET.get('qid_renew_status', '')
        qid_lost_status = self.request.GET.get('qid_lost_status', '')
        joining_date = self.request.GET.get('joining_date', '')
        
        if employee:
           filters['employee__name__icontains'] = employee
        if work_status:
            filters['work_status__icontains'] = work_status
        if qid_renew_status:
            filters['qid_renew_status__icontains'] = qid_renew_status
        if qid_lost_status:
            filters['qid_lost_status__icontains'] = qid_lost_status
        if joining_date:
            filters['joining_date'] = joining_date
       
        return Employment.objects.filter(**filters)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_num'] = self.request.GET.get('page', 1)
        context['paginator_list'], context['paginator'], context['last_page_number'] = paginate_data(self.request, context['page_num'], self.get_queryset())

        get_param = self.request.GET.copy()
        if 'page' in get_param:
            get_param.pop('page')
        context['get_param'] = get_param.urlencode() 
        return context 


@login_required
def employeement_delete(request, pk):
    employeement = Employment.objects.get(pk=pk)
    employeement.is_active = False
    employeement.save()
    return redirect('employeement:list') 


@method_decorator(login_required, name='dispatch')
class EmployeementDetailView(DetailView):
    model = Employment 
    template_name = "employeement/detail.html" 
    context_object_name = 'employeement'


@method_decorator(login_required, name='dispatch')
class PassportListView(ListView):
    model = Passport 
    template_name = "passport/list.html" 
    context_object_name = 'passports'

    def get_queryset(self):
        filters = {
            'is_active': True, 
        }
        
        employee = self.request.GET.get('employee', '') 
        passport_no = self.request.GET.get('passport_no', '')
        passport_expiry_date = self.request.GET.get('passport_expiry_date', '')
        passport_renewed = self.request.GET.get('passport_renewed', '')
        
        if employee:
           filters['employee__name__icontains'] = employee
        if passport_no:
            filters['passport_no__icontains'] = passport_no
        if passport_expiry_date:
            filters['passport_expiry_date'] = passport_expiry_date
        if passport_renewed:
            filters['passport_renewed'] = passport_renewed == 'true'
       
        return Passport.objects.filter(**filters)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_num'] = self.request.GET.get('page', 1)
        context['paginator_list'], context['paginator'], context['last_page_number'] = paginate_data(self.request, context['page_num'], self.get_queryset())

        get_param = self.request.GET.copy()
        if 'page' in get_param:
            get_param.pop('page')
        context['get_param'] = get_param.urlencode() 
        return context 

@login_required
def passport_delete(request, pk):
    passport = Passport.objects.get(pk=pk)
    passport.is_active = False
    passport.save()
    return redirect('passport:list') 


@method_decorator(login_required, name='dispatch')
class PassportDetailView(DetailView):
    model = Passport 
    template_name = "passport/detail.html" 
    context_object_name = 'passport'


@method_decorator(login_required, name='dispatch')
class DrivingLicenseListView(ListView):
    model = DrivingLicense 
    template_name = "driving_license/list.html" 
    context_object_name = 'driving_licenses'

    def get_queryset(self):
        filters = {
            'is_active': True, 
        }
        
        employee = self.request.GET.get('employee', '') 
        license_no = self.request.GET.get('license_no', '')
        license_expiry_date = self.request.GET.get('license_expiry_date', '')
        license_renewed = self.request.GET.get('license_renewed', '')
        
        if employee:
           filters['employee__name__icontains'] = employee
        if license_no:
            filters['license_no__icontains'] = license_no
        if license_expiry_date:
            filters['license_expiry_date'] = license_expiry_date
        if license_renewed:
            filters['license_renewed'] = license_renewed == 'true'
       
        return DrivingLicense.objects.filter(**filters)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_num'] = self.request.GET.get('page', 1)
        context['paginator_list'], context['paginator'], context['last_page_number'] = paginate_data(self.request, context['page_num'], self.get_queryset())

        get_param = self.request.GET.copy()
        if 'page' in get_param:
            get_param.pop('page')
        context['get_param'] = get_param.urlencode() 
        return context 


@login_required
def driving_license_delete(request, pk):
    driving_license = DrivingLicense.objects.get(pk=pk)
    driving_license.is_active = False
    driving_license.save()
    return redirect('driving_license:list') 


@method_decorator(login_required, name='dispatch')
class DrivingLicenseDetailView(DetailView):
    model = DrivingLicense 
    template_name = "driving_license/detail.html" 
    context_object_name = 'driving_license'


@method_decorator(login_required, name='dispatch')
class HealthInsuranceListView(ListView):
    model = HealthInsurance 
    template_name = "health_insurance/list.html" 
    context_object_name = 'health_insurances'

    def get_queryset(self):
        filters = {
            'is_active': True, 
        }
        
        employee = self.request.GET.get('employee', '') 
        hamad_health_card = self.request.GET.get('hamad_health_card', '')
        wm_insurance = self.request.GET.get('wm_insurance', '')
        family_health_card = self.request.GET.get('family_health_card', '')
        
        if employee:
           filters['employee__name__icontains'] = employee
        if hamad_health_card:
            filters['hamad_health_card'] = hamad_health_card == 'true'
        if wm_insurance:
            filters['wm_insurance'] = wm_insurance
        if family_health_card:
            filters['family_health_card'] = family_health_card
       
        return HealthInsurance.objects.filter(**filters)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_num'] = self.request.GET.get('page', 1)
        context['paginator_list'], context['paginator'], context['last_page_number'] = paginate_data(self.request, context['page_num'], self.get_queryset())

        get_param = self.request.GET.copy()
        if 'page' in get_param:
            get_param.pop('page')
        context['get_param'] = get_param.urlencode() 
        return context 


@login_required
def health_insurance_delete(request, pk):
    health_insurance = HealthInsurance.objects.get(pk=pk)
    health_insurance.is_active = False
    health_insurance.save()
    return redirect('health_insurance:list') 


@method_decorator(login_required, name='dispatch')
class HealthInsuranceDetailView(DetailView):
    model = HealthInsurance 
    template_name = "health_insurance/detail.html" 
    context_object_name = 'health_insurance'


@method_decorator(login_required, name='dispatch')
class ContactListView(ListView):
    model = Contact 
    template_name = "contact/list.html" 
    context_object_name = 'contacts'

    def get_queryset(self):
        filters = {
            'is_active': True, 
        }
        
        employee = self.request.GET.get('employee', '') 
        phone_no = self.request.GET.get('phone_no', '')
        home_email = self.request.GET.get('home_email', '')
        
        if employee:
           filters['employee__name__icontains'] = employee
        if phone_no:
            filters['phone_no__icontains'] = phone_no
        if home_email:
            filters['home_email__icontains'] = home_email
       
        return Contact.objects.filter(**filters)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_num'] = self.request.GET.get('page', 1)
        context['paginator_list'], context['paginator'], context['last_page_number'] = paginate_data(self.request, context['page_num'], self.get_queryset())

        get_param = self.request.GET.copy()
        if 'page' in get_param:
            get_param.pop('page')
        context['get_param'] = get_param.urlencode() 
        return context 


@login_required
def contact_delete(request, pk):
    contact = Contact.objects.get(pk=pk)
    contact.is_active = False
    contact.save()
    return redirect('contact:list') 


@method_decorator(login_required, name='dispatch')
class ContactDetailView(DetailView):
    model = Contact 
    template_name = "contact/detail.html" 
    context_object_name = 'contact'


@method_decorator(login_required, name='dispatch')
class AddressListView(ListView):
    model = Address 
    template_name = "address/list.html" 
    context_object_name = 'addresses'

    def get_queryset(self):
        filters = {
            'is_active': True, 
        }
        
        employee = self.request.GET.get('employee', '') 
        national_address = self.request.GET.get('national_address', '')
        room_address = self.request.GET.get('room_address', '')
        
        if employee:
           filters['employee__name__icontains'] = employee
        if national_address:
            filters['national_address__icontains'] = national_address
        if room_address:
            filters['room_address__icontains'] = room_address
       
        return Address.objects.filter(**filters)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_num'] = self.request.GET.get('page', 1)
        context['paginator_list'], context['paginator'], context['last_page_number'] = paginate_data(self.request, context['page_num'], self.get_queryset())

        get_param = self.request.GET.copy()
        if 'page' in get_param:
            get_param.pop('page')
        context['get_param'] = get_param.urlencode() 
        return context  


@login_required
def address_delete(request, pk):
    address = Address.objects.get(pk=pk)
    address.is_active = False
    address.save()
    return redirect('address:list') 


@method_decorator(login_required, name='dispatch')
class AddressDetailView(DetailView):
    model = Address 
    template_name = "address/detail.html" 
    context_object_name = 'address'


@method_decorator(login_required, name='dispatch')
class VehicleListView(ListView):
    model = Vehicle 
    template_name = "vehicle/list.html" 
    context_object_name = 'vehicles'

    def get_queryset(self):
        filters = {
            'is_active': True, 
        }
        
        employee = self.request.GET.get('employee', '') 
        vehicle_no = self.request.GET.get('vehicle_no', '')
        istemara_expiry_date = self.request.GET.get('istemara_expiry_date', '')
        
        if employee:
           filters['employee__name__icontains'] = employee
        if vehicle_no:
            filters['vehicle_no__icontains'] = vehicle_no
        if istemara_expiry_date:
            filters['istemara_expiry_date'] = istemara_expiry_date
       
        return Vehicle.objects.filter(**filters)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_num'] = self.request.GET.get('page', 1)
        context['paginator_list'], context['paginator'], context['last_page_number'] = paginate_data(self.request, context['page_num'], self.get_queryset())

        get_param = self.request.GET.copy()
        if 'page' in get_param:
            get_param.pop('page')
        context['get_param'] = get_param.urlencode() 
        return context  



@login_required
def vehicle_delete(request, pk):
    vehicle = Vehicle.objects.get(pk=pk)
    vehicle.is_active = False
    vehicle.save()
    return redirect('vehicle:list') 


@method_decorator(login_required, name='dispatch')
class VehicleDetailView(DetailView):
    model = Vehicle 
    template_name = "vehicle/detail.html" 
    context_object_name = 'vehicle'