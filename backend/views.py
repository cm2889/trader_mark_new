import os 
import base64 
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.core.paginator import PageNotAnInteger, EmptyPage
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.db.models import Q
from django.views.decorators.http import require_GET 
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings
from django.core.cache import cache
from PIL import Image
from io import BytesIO
from django.utils.text import slugify 
from datetime import datetime 

from backend.models import (
    WebImages, SiteSettings, LoginLog, UserMenuPermission, 
    BackendMenu, 
    Nationality, Employee, Employment, Passport, DrivingLicense, 
    HealthInsurance, Contact, Address, Vehicle, 
    VehicleHandover, VehicleItem, TrafficViolation, VehicleRent,
    VehicleInstallment, VehicleMaintenance, VehicleAccident
)

from backend.forms import (
    CustomUserLoginForm, NationalityForm, EmployeeForm, EmploymentForm, 
    PassportForm, DrivingLicenseForm, HealthInsuranceForm, ContactForm, 
    AddressForm, UserCreateForm, VehicleForm,
    VehicleHandoverForm, VehicleItemForm, TrafficViolationForm, VehicleRentForm,
    VehicleInstallmentForm, VehicleMaintenanceForm, VehicleAccidentForm
) 

from backend.common_func import checkUserPermission

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

    return paginator_list, data_list, last_page_number



def _resolve_menu_url(menu_url: str):
    if not menu_url:
        return ""
    if "/" in menu_url:
        return menu_url
    try:
        return reverse("backend:menu_wise_dashboard", args=[menu_url])
    except Exception:
        return menu_url


def _score_menu(menu, ql: str) -> int:
    name = (menu.menu_name or "").lower()
    module = (menu.module_name or "").lower()
    desc = (menu.menu_description or "").lower()

    score = 0

    if name == ql:
        score += 1000
    if name.startswith(ql):
        score += 300
    if ql in name:
        score += 200
        pos = name.find(ql)
        score += max(0, 100 - min(pos, 100))

    if module == ql:
        score += 120
    elif module.startswith(ql):
        score += 80
    elif ql in module:
        score += 40

    if ql in desc:
        score += 10

    score += max(0, 30 - abs(len(name) - len(ql)))

    return score


def serve_optimized_image(request, unique_key):
    try:
        width = request.GET.get("width")
        quality = request.GET.get("quality")
        path = request.GET.get("image_path")

        try:
            width = int(width) if width else None
        except ValueError:
            width = None

        try:
            quality = int(quality) if quality else 80
        except ValueError:
            quality = 80

        if quality > 100:
            quality = 100

        cache_key = f"photo_{unique_key}_{width or 'auto'}_{quality}_{path or 'default'}"
        cached_image = cache.get(cache_key)
        if cached_image:
            image_bytes = base64.b64decode(cached_image)
            response = HttpResponse(image_bytes, content_type="image/webp")
            response["Cache-Control"] = "public, max-age=2592000, immutable"
            return response

        if unique_key:
            if unique_key != "no_image":
                img_obj = get_object_or_404(WebImages, unique_key=unique_key)
                image_path = img_obj.image.path
            elif unique_key == "no_image" and request.GET.get("image_path"):
                image_path = request.GET.get("image_path")
                if image_path == "logo" or image_path == "favicon":
                    site_settings = SiteSettings.objects.first()
                    if image_path == "logo":
                        image_path = site_settings.logo.path if site_settings.logo else os.path.join(settings.STATICFILES_DIRS[0], "images/default_logo.png")
                    elif image_path == "favicon":
                        image_path = site_settings.favicon.path if site_settings.favicon else os.path.join(settings.STATICFILES_DIRS[0], "images/default_favicon.png")
                elif image_path.startswith(settings.MEDIA_URL):
                    image_path = image_path.replace(settings.MEDIA_URL, settings.MEDIA_ROOT + "/")
            else:
                image_path = os.path.join(settings.STATICFILES_DIRS[0], "images/no_image.png")
        else:
            image_path = os.path.join(settings.STATICFILES_DIRS[0], "images/no_image.png")

        img = Image.open(image_path)

        if width:
            ratio = width / float(img.width)
            height = int(img.height * ratio)
            img = img.resize((width, height), Image.LANCZOS)

        buffer = BytesIO()
        img.save(buffer, format="WEBP", quality=quality, optimize=True)
        image_bytes = buffer.getvalue()

        cache.set(cache_key, base64.b64encode(image_bytes).decode("ascii"), timeout=86400)

        base_name = slugify(unique_key)
        filename = f"{base_name}.webp"
        response = HttpResponse(image_bytes, content_type="image/webp")
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        response["Cache-Control"] = "public, max-age=2592000, immutable"
        return response

    except Exception:
        # Redirect to "no_image" instead of returning a string
        no_image_url = reverse('backend:serve_optimized_image', kwargs={'unique_key': 'no_image'})
        no_image_url = f"{no_image_url}?width=300&quality=80"
        return redirect(no_image_url)


@require_GET
def search_backend_menus(request):
    if not request.user.is_authenticated:
        return JsonResponse({"status": False, "auth_required": True, "data": []}, status=401)

    q = (request.GET.get("q") or "").strip()
    if not q:
        return JsonResponse({"status": True, "data": []})

    try:
        limit = int(request.GET.get("limit", 10))
    except ValueError:
        limit = 10
    limit = max(1, min(limit, 50))

    perms = (
        UserMenuPermission.objects.filter(
            user_id=request.user.id, can_view=True, is_active=True, deleted=False, menu__is_active=True,
        )
        .select_related("menu")
        .order_by("menu__id")
    )

    like = Q(menu__menu_name__icontains=q) | Q(menu__parent__menu_name__icontains=q)

    ql = q.lower()
    seen = set()
    ranked = []

    for perm in perms.filter(like):
        m = perm.menu
        if m.id in seen:
            continue
        seen.add(m.id)
        ranked.append((_score_menu(m, ql), m))

    ranked.sort(key=lambda t: (-t[0], len((t[1].menu_name or "")), (t[1].menu_name or "").lower()))

    results = []
    for _, m in ranked[: limit]:
        url = _resolve_menu_url(m.menu_url)
        icon = m.menu_icon or "fa-solid fa-circle"
        title = m.menu_name or ""
        # description = m.menu_description or ""

        parent_menus = []
        current_menu = m
        while current_menu.parent:
            parent_menus.append(current_menu.parent.menu_name)
            current_menu = current_menu.parent
        parent_menus.reverse()

        description = " > ".join(parent_menus) if parent_menus else ""

        results.append(
            {
                "name": title,
                "description": description,
                "icon": icon,
                "url": url,
                "module": m.module_name or "",
            }
        )

    return JsonResponse({"status": True, "count": len(results), "data": results})


@login_required
def backend_dashboard(request):
    return render(request, 'home/home.html')


def backend_login(request):
    if request.user.is_authenticated:
        return redirect('backend:backend_logout')

    form = CustomUserLoginForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')

        user_ip = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')

        user = User.objects.filter(username=username).first()

        if user:
            authenticated_user = authenticate(request, username=username, password=password)

            if authenticated_user is not None:
                login(request, authenticated_user)
                LoginLog.objects.create(user_id=user.id, username=username, login_ip=user_ip, login_status=True)

                if user.is_superuser:
                    menu_list = BackendMenu.objects.filter(is_active=True)
                    for menu in menu_list:
                        UserMenuPermission.objects.update_or_create(
                            user_id=user.id,
                            menu_id=menu.id,
                            defaults={
                                'can_view': True,
                                'can_add': True,
                                'can_update': True,
                                'can_delete': True,
                                'is_active': True,
                                'created_by_id': request.user.id,
                            }
                        )

                next_url = request.GET.get('next', reverse('backend:backend_dashboard'))
                return redirect(next_url)

        LoginLog.objects.create(username=username, login_ip=user_ip, login_status=False)
        messages.error(request, "Invalid username or password.")
    context = {
        'form': form
    }
    return render(request, 'backend_login.html', context)


@login_required
def backend_logout(request):
    LoginLog.objects.create(
        user_id=request.user.id,
        username=request.user.username,
        login_ip=request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR'),
        login_status=False
    )
    logout(request)
    return redirect('backend:backend_login')


# Menu Wise Dashboard
@login_required
def menu_wise_dashboard(request, menu_slug):
    current_menu = BackendMenu.objects.filter(menu_url=menu_slug, is_active=True).first()
    if current_menu:
        if current_menu.is_main_menu:
            menu_list = UserMenuPermission.objects.filter(user_id=request.user.id, menu__parent_id=current_menu.id, menu__is_sub_menu=True, can_view=True, menu__is_active=True, is_active=True, deleted=False).order_by('menu__id')
        else:
            menu_list = UserMenuPermission.objects.filter(user_id=request.user.id, menu__parent_id=current_menu.id, menu__is_sub_child_menu=True, can_view=True, menu__is_active=True, is_active=True, deleted=False).order_by('menu__id')
    else:
        menu_list = []

    context = {
        "current_menu": current_menu,
        "menu_list": menu_list,
    }
    return render(request, 'menu_wise_dashboard.html', context)

# Menu Wise Dashboard


# Management Start
@method_decorator(login_required, name='dispatch')
class UserListView(ListView):
    model = User
    template_name = 'user/list.html'
    context_object_name = 'user_list'
    ordering = ['-date_joined']
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        # Check permission before anything else
        if not checkUserPermission(request, "can_add", "/backend/user/"):
            return render(request, "403.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        username = self.request.GET.get('username')
        is_active = self.request.GET.get('is_active')

        if username:
            queryset = queryset.filter(username__icontains=username)
        if is_active in ['0', '1']:  # stricter check
            queryset = queryset.filter(is_active=is_active)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['username'] = self.request.GET.get('username', '')
        context['is_active'] = self.request.GET.get('is_active', '')

        get_params = self.request.GET.copy()
        get_params.pop('page', None)
        context['query_params'] = get_params.urlencode()

        context['filter_user'] = User.objects.all()
        return context


@login_required
def user_add(request):
    if not checkUserPermission(request, "can_add", "/backend/user/"):
        return render(request, "403.html", status=403)

    if request.method == 'POST':
        form = UserCreateForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'New user has been added successfully!')
            return redirect('backend:user_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = UserCreateForm()

    return render(request, 'user/add.html', {'form': form})


@login_required
def user_update(request, data_id):
    if not checkUserPermission(request, "can_update", "/backend/user/"):
        return render(request, "403.html", status=403)

    user_obj = get_object_or_404(User, id=data_id)

    if request.method == 'POST':
        # Update logic goes here
        pass

    return render(request, 'user/management_update.html', {"user": user_obj})


@login_required
def reset_password(request, data_id):
    if not checkUserPermission(request, "can_update", "/backend/user/"):
        return render(request, "403.html", status=403)

    user = get_object_or_404(User, id=data_id)
    if request.method == 'POST':
        form = AdminPasswordChangeForm(user=user, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your password has been updated successfully.')
            return redirect('backend:backend_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AdminPasswordChangeForm(user=user)

    return render(request, 'user/reset_password.html', {'form': form, 'user': user})


@login_required
def user_permission(request, user_id):
    if not checkUserPermission(request, "can_update", "/backend/user-permission/"):
        return render(request, "403.html")

    if request.method == "POST":
        username = request.POST.get("username")
        user_status = request.POST.get("user_status")
        selected_menus = request.POST.getlist("selected_menus")
        can_view = request.POST.getlist("can_view")
        can_add = request.POST.getlist("can_add")
        can_update = request.POST.getlist("can_update")
        can_delete = request.POST.getlist("can_delete")

        try:
            user = User.objects.get(pk=user_id)
            user.is_active = user_status
            user.save()
        except Exception:
            pass

        exist_all_permission = UserMenuPermission.objects.filter(user_id=user_id)
        for exist_permission in exist_all_permission:
            if exist_permission.id not in selected_menus:
                exist_permission.can_view = False
                exist_permission.can_add = False
                exist_permission.can_update = False
                exist_permission.can_delete = False
                exist_permission.is_active = False
                exist_permission.updated_at = datetime.now()
                exist_permission.deleted_by_id = request.user.id
                exist_permission.save()

        if user_id and username and selected_menus:
            for menu_id in selected_menus:
                if menu_id in can_view:
                    user_view_access = True
                else:
                    user_view_access = False

                if menu_id in can_add:
                    user_add_access = True
                else:
                    user_add_access = False

                if menu_id in can_update:
                    user_update_access = True
                else:
                    user_update_access = False

                if menu_id in can_delete:
                    user_delete_access = True
                else:
                    user_delete_access = False

                exist_permission = UserMenuPermission.objects.filter(user_id=user_id, menu_id=menu_id)
                if exist_permission:
                    exist_permission.update(
                        updated_by_id=request.user.id, can_view=user_view_access, can_add=user_add_access,
                        can_update=user_update_access, can_delete=user_delete_access, updated_at=datetime.now(), is_active=True,
                    )
                else:
                    UserMenuPermission.objects.create(
                        user_id=user_id, menu_id=menu_id, can_view=user_view_access, can_add=user_add_access,
                        can_update=user_update_access, can_delete=user_delete_access, created_by_id=request.user.id
                    )
            messages.success(request, "User permission has been assigned!")
        else:
            messages.warning(request, "No permission has been assigned!")

        return redirect('backend:user_permission', user_id=user_id)

    user = User.objects.get(pk=user_id)
    menu_list = BackendMenu.objects.filter(is_active=True).order_by("module_name")

    for data in menu_list:
        try:
            user_access_perm = UserMenuPermission.objects.get(user_id=user_id, menu_id=data.id, is_active=True)

            data.user_menu_id = user_access_perm.menu_id
            data.can_view = user_access_perm.can_view
            data.can_add = user_access_perm.can_add
            data.can_update = user_access_perm.can_update
            data.can_delete = user_access_perm.can_delete
        except Exception:
            pass

    context = {
        "user": user,
        "menu_list": menu_list,
    }
    return render(request, 'user/user_permission.html', context)

@method_decorator(login_required, name='dispatch')
class NationalityListView(ListView):
    model = Nationality
    template_name = "nationality/list.html"
    paginate_by = None 

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/nationality/"):
            messages.error(request, "You do not have permission to view nationalities.")
            return render(request, "403.html", status=403)
        return super().dispatch(request, *args, **kwargs)

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

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_add", "/backend/nationality/"):
            messages.error(request, "You do not have permission to add nationalities.")
            return render(request, "403.html", status=403)
        return super().dispatch(request, *args, **kwargs)

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

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_update", "/backend/nationality/"):
            messages.error(request, "You do not have permission to update nationalities.")
            return render(request, "403.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form) 
    
@login_required
def nationality_delete(request, pk):

    if not checkUserPermission(request, "can_delete", "/backend/nationality/"):
        messages.error(request, "You do not have permission to delete nationalities.")
        return render(request, "403.html", status=403)
    
    nationality = Nationality.objects.get(pk=pk)
    nationality.is_active = False
    nationality.save()
    return redirect('nationality:list') 


@login_required
def employee_create(request):

    if not checkUserPermission(request, "can_add", "/backend/employee/"):
        messages.error(request, "You do not have permission to add employees.")
        return render(request, "403.html", status=403)

    if request.method == 'POST':
        employee_form = EmployeeForm(request.POST, request.FILES, prefix='employee')
        employment_form = EmploymentForm(request.POST, prefix='employment')
        passport_form = PassportForm(request.POST, prefix='passport')
        driving_license_form = DrivingLicenseForm(request.POST, prefix='driving_license')
        health_insurance_form = HealthInsuranceForm(request.POST, prefix='health_insurance')
        contact_form = ContactForm(request.POST, prefix='contact')
        address_form = AddressForm(request.POST, prefix='address')

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


            return redirect('employee:list')
    else:
        employee_form = EmployeeForm(prefix='employee')
        employment_form = EmploymentForm(prefix='employment')
        passport_form = PassportForm(prefix='passport')
        driving_license_form = DrivingLicenseForm(prefix='driving_license')
        health_insurance_form = HealthInsuranceForm(prefix='health_insurance')
        contact_form = ContactForm(prefix='contact')
        address_form = AddressForm(prefix='address')

    context = {
        'employee_form': employee_form,
        'employment_form': employment_form,
        'passport_form': passport_form,
        'driving_license_form': driving_license_form,
        'health_insurance_form': health_insurance_form,
        'contact_form': contact_form,
        'address_form': address_form,
        'nationalities': Nationality.objects.filter(is_active=True),
    }

    return render(request, "employee/create.html", context)


@login_required
def employee_update(request, pk):

    if not checkUserPermission(request, "can_update", "/backend/employee/"):
        messages.error(request, "You do not have permission to update employees.")
        return render(request, "403.html", status=403)
    
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

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/employee/"):
            messages.error(request, "You do not have permission to view employees.")
            return render(request, "403.html", status=403)
        return super().dispatch(request, *args, **kwargs)

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
            filters['qid_no'] = qid_no
        if hr_file_no:
            filters['hr_file_no'] = hr_file_no
        if nationality:
            filters['nationality_id'] = nationality
        if gender:
            filters['gender'] = gender
        if joining_date:
            filters['joining_date__icontains'] = joining_date
       
        if name:
           filters['id'] = name
        
        return Employee.objects.filter(**filters)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employees'] = self.get_queryset()
        context['page_num'] = self.request.GET.get('page', 1)
        context['paginator_list'], context['paginator'], context['last_page_number'] = paginate_data(self.request, context['page_num'], context['employees'])

        # Add all employees and nationalities for select2 dropdowns
        from backend.models import Nationality
        context['all_employees'] = Employee.objects.filter(is_active=True).order_by('first_name', 'last_name')
        context['nationalities'] = Nationality.objects.filter(is_active=True).order_by('name')

        get_param = self.request.GET.copy()
        if 'page' in get_param:
            get_param.pop('page')
        context['get_param'] = get_param.urlencode() 
        return context 



@login_required
def employee_delete(request, pk):

    if not checkUserPermission(request, "can_delete", "/backend/employee/"):
        messages.error(request, "You do not have permission to delete employees.")
        return render(request, "403.html", status=403)

    employee = Employee.objects.get(pk=pk)
    employee.is_active = False
    employee.save()
    return redirect('employee:list') 


@method_decorator(login_required, name='dispatch')
class EmployeeDetailView(DetailView):
    model = Employee 
    template_name = "employee/detail.html" 
    context_object_name = 'employee'

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/employee/"):
            messages.error(request, "You do not have permission to view employee details.")
            return render(request, "403.html", status=403) 
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.get_object()

        context['employment'] = Employment.objects.filter(employee=employee, is_active=True).first()
        context['passport'] = Passport.objects.filter(employee=employee, is_active=True).first()
        context['driving_license'] = DrivingLicense.objects.filter(employee=employee, is_active=True).first()
        context['health_insurance'] = HealthInsurance.objects.filter(employee=employee, is_active=True).first()
        context['contact'] = Contact.objects.filter(employee=employee, is_active=True).first()
        context['address'] = Address.objects.filter(employee=employee, is_active=True).first()
        context['vehicle'] = Vehicle.objects.filter(employee=employee, is_active=True).first()

        return context


@method_decorator(login_required, name='dispatch')
class VehicleListView(ListView):
    model = Vehicle
    template_name = "vehicle_info/list.html"
    paginate_by = None

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/vehicle_info/"):
            messages.error(request, "You do not have permission to view vehicle infos.")
            return render(request, "403.html", status=403) 
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        filters = {
            'is_active': True, 
            'deleted': False,
        }
        
        plate_no = self.request.GET.get('plate_no', '') 
        vehicle_type = self.request.GET.get('vehicle_type', '')
        ownership = self.request.GET.get('ownership', '')
        
        if plate_no:
            filters['plate_no'] = plate_no
        if vehicle_type:
            filters['vehicle_type'] = vehicle_type
        if ownership:
            filters['ownership'] = ownership
       
        return Vehicle.objects.select_related('employee').filter(**filters)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['vehicle_infos'] = self.get_queryset()
        context['page_num'] = self.request.GET.get('page', 1)
        context['paginator_list'], context['paginator'], context['last_page_number'] = paginate_data(self.request, context['page_num'], context['vehicle_infos'])

        # Add all vehicles for select2 dropdown
        context['all_vehicles'] = Vehicle.objects.filter(is_active=True, deleted=False).select_related('employee').order_by('plate_no')

        get_param = self.request.GET.copy()
        if 'page' in get_param:
            get_param.pop('page')
        context['get_param'] = get_param.urlencode() 
        return context 


@method_decorator(login_required, name='dispatch')
class VehicleCreateView(CreateView):
    model = Vehicle
    template_name = "vehicle_info/create.html"
    form_class = VehicleForm
    success_url = reverse_lazy('vehicle_info:list')

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_add", "/backend/vehicle_info/"):
            messages.error(request, "You do not have permission to add vehicle infos.")
            return render(request, "403.html", status=403) 
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class VehicleUpdateView(UpdateView):
    model = Vehicle
    template_name = "vehicle_info/update.html"
    form_class = VehicleForm
    success_url = reverse_lazy('vehicle_info:list')

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_update", "/backend/vehicle_info/"):
            messages.error(request, "You do not have permission to edit vehicle infos.")
            return render(request, "403.html", status=403) 
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


@login_required
def vehicle_delete(request, pk):
    if not checkUserPermission(request, "can_delete", "/backend/vehicle_info/"):
        messages.error(request, "You do not have permission to delete vehicle infos.")
        return render(request, "403.html", status=403) 
    vehicle_info = Vehicle.objects.get(pk=pk)
    vehicle_info.is_active = False
    vehicle_info.deleted = True
    vehicle_info.save()
    return redirect('vehicle_info:list')



@login_required
def vehicle_management(request):
    if not checkUserPermission(request, "can_view", "/backend/vehicle-management/"):
        messages.error(request, "You do not have permission to view vehicle management.")
        return render(request, "403.html", status=403) 

    # Get counts for dashboard
    total_vehicles = Vehicle.objects.filter(is_active=True, deleted=False).count()
    total_handovers = VehicleHandover.objects.count()
    total_violations = TrafficViolation.objects.count()
    unpaid_violations = TrafficViolation.objects.filter(is_paid=False).count()
    total_rent = VehicleRent.objects.count()
    unpaid_rent = VehicleRent.objects.filter(is_paid=False).count()
    total_maintenance = VehicleMaintenance.objects.count()
    pending_maintenance = VehicleMaintenance.objects.filter(status='PENDING').count()
    total_accidents = VehicleAccident.objects.count()
    total_installments = VehicleInstallment.objects.count()
    unpaid_installments = VehicleInstallment.objects.filter(is_paid=False).count()

    context = {
        'total_vehicles': total_vehicles,
        'total_handovers': total_handovers,
        'total_violations': total_violations,
        'unpaid_violations': unpaid_violations,
        'total_rent': total_rent,
        'unpaid_rent': unpaid_rent,
        'total_maintenance': total_maintenance,
        'pending_maintenance': pending_maintenance,
        'total_accidents': total_accidents,
        'total_installments': total_installments,
        'unpaid_installments': unpaid_installments,
    }
    return render(request, 'vehicle_management/list.html', context)


# ========================================
# VEHICLE HANDOVER VIEWS
# ========================================
@method_decorator(login_required, name='dispatch')
class VehicleHandoverListView(ListView):
    model = VehicleHandover
    template_name = "vehicle_handover/list.html"
    paginate_by = None

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/vehicle-handover/"):
            messages.error(request, "You do not have permission to view vehicle handovers.")
            return render(request, "403.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = VehicleHandover.objects.all().order_by('-created_at')
        
        plate_no = self.request.GET.get('plate_no', '')
        from_employee = self.request.GET.get('from_employee', '')
        to_employee = self.request.GET.get('to_employee', '')
        
        if plate_no:
            queryset = queryset.filter(vehicle__vehicle__plate_no=plate_no)
        if from_employee:
            queryset = queryset.filter(from_employee_id=from_employee)
        if to_employee:
            queryset = queryset.filter(to_employee_id=to_employee)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['handovers'] = self.get_queryset()
        context['page_num'] = self.request.GET.get('page', 1)
        context['paginator_list'], context['paginator'], context['last_page_number'] = paginate_data(
            self.request, context['page_num'], context['handovers']
        )
        get_param = self.request.GET.copy()
        if 'page' in get_param:
            get_param.pop('page')
        context['get_param'] = get_param.urlencode()
        
        # Add data for select2 dropdowns
        context['all_vehicles'] = Vehicle.objects.filter(is_active=True, deleted=False).order_by('plate_no')
        context['all_employees'] = Employee.objects.filter(is_active=True, deleted=False).order_by('first_name', 'last_name')
        
        return context


@login_required
def vehicle_handover_create(request):
    if not checkUserPermission(request, "can_add", "/backend/vehicle-handover/"):
        messages.error(request, "You do not have permission to add vehicle handovers.")
        return render(request, "403.html", status=403)

    if request.method == 'POST':
        form = VehicleHandoverForm(request.POST)
        if form.is_valid():
            handover = form.save(commit=False)
            handover.created_by = request.user
            handover.save()
            messages.success(request, "Vehicle handover created successfully.")
            return redirect('vehicle_handover:list')
    else:
        form = VehicleHandoverForm()

    context = {
        'form': form,
        'vehicles': Vehicle.objects.filter(is_active=True),
        'employees': Employee.objects.filter(is_active=True),
    }
    return render(request, 'vehicle_handover/create.html', context)


@login_required
def vehicle_handover_update(request, pk):
    if not checkUserPermission(request, "can_update", "/backend/vehicle-handover/"):
        messages.error(request, "You do not have permission to update vehicle handovers.")
        return render(request, "403.html", status=403)

    handover = get_object_or_404(VehicleHandover, pk=pk)
    
    if request.method == 'POST':
        form = VehicleHandoverForm(request.POST, instance=handover)
        if form.is_valid():
            form.save()
            messages.success(request, "Vehicle handover updated successfully.")
            return redirect('vehicle_handover:list')
    else:
        form = VehicleHandoverForm(instance=handover)

    context = {
        'form': form,
        'handover': handover,
        'vehicles': Vehicle.objects.filter(is_active=True),
        'employees': Employee.objects.filter(is_active=True),
    }
    return render(request, 'vehicle_handover/update.html', context)


@login_required
def vehicle_handover_detail(request, pk):
    if not checkUserPermission(request, "can_view", "/backend/vehicle-handover/"):
        messages.error(request, "You do not have permission to view vehicle handover details.")
        return render(request, "403.html", status=403)

    handover = get_object_or_404(VehicleHandover, pk=pk)
    context = {'handover': handover}
    return render(request, 'vehicle_handover/detail.html', context)


@login_required
def vehicle_handover_delete(request, pk):
    if not checkUserPermission(request, "can_delete", "/backend/vehicle-handover/"):
        messages.error(request, "You do not have permission to delete vehicle handovers.")
        return render(request, "403.html", status=403)

    handover = get_object_or_404(VehicleHandover, pk=pk)
    handover.delete()
    messages.success(request, "Vehicle handover deleted successfully.")
    return redirect('vehicle_handover:list')


# ========================================
# TRAFFIC VIOLATION VIEWS
# ========================================
@method_decorator(login_required, name='dispatch')
class TrafficViolationListView(ListView):
    model = TrafficViolation
    template_name = "traffic_violation/list.html"
    paginate_by = None

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/traffic-violation/"):
            messages.error(request, "You do not have permission to view traffic violations.")
            return render(request, "403.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = TrafficViolation.objects.all().order_by('-violation_date')
        
        plate_no = self.request.GET.get('plate_no', '')
        employee = self.request.GET.get('employee', '')
        is_paid = self.request.GET.get('is_paid', '')
        
        if plate_no:
            queryset = queryset.filter(vehicle__vehicle__plate_no=plate_no)
        if employee:
            queryset = queryset.filter(employee_id=employee)
        if is_paid:
            queryset = queryset.filter(is_paid=(is_paid == 'true'))
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['violations'] = self.get_queryset()
        context['page_num'] = self.request.GET.get('page', 1)
        context['paginator_list'], context['paginator'], context['last_page_number'] = paginate_data(
            self.request, context['page_num'], context['violations']
        )
        get_param = self.request.GET.copy()
        if 'page' in get_param:
            get_param.pop('page')
        context['get_param'] = get_param.urlencode()
        
        # Add data for select2 dropdowns
        context['all_vehicles'] = Vehicle.objects.filter(is_active=True, deleted=False).order_by('plate_no')
        context['all_employees'] = Employee.objects.filter(is_active=True, deleted=False).order_by('first_name', 'last_name')
        
        return context


@login_required
def traffic_violation_create(request):
    if not checkUserPermission(request, "can_add", "/backend/traffic-violation/"):
        messages.error(request, "You do not have permission to add traffic violations.")
        return render(request, "403.html", status=403)

    if request.method == 'POST':
        form = TrafficViolationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Traffic violation created successfully.")
            return redirect('traffic_violation:list')
    else:
        form = TrafficViolationForm()

    context = {
        'form': form,
        'vehicles': Vehicle.objects.filter(is_active=True),
        'employees': Employee.objects.filter(is_active=True),
    }
    return render(request, 'traffic_violation/create.html', context)


@login_required
def traffic_violation_update(request, pk):
    if not checkUserPermission(request, "can_update", "/backend/traffic-violation/"):
        messages.error(request, "You do not have permission to update traffic violations.")
        return render(request, "403.html", status=403)

    violation = get_object_or_404(TrafficViolation, pk=pk)
    
    if request.method == 'POST':
        form = TrafficViolationForm(request.POST, instance=violation)
        if form.is_valid():
            form.save()
            messages.success(request, "Traffic violation updated successfully.")
            return redirect('traffic_violation:list')
    else:
        form = TrafficViolationForm(instance=violation)

    context = {
        'form': form,
        'violation': violation,
        'vehicles': Vehicle.objects.filter(is_active=True),
        'employees': Employee.objects.filter(is_active=True),
    }
    return render(request, 'traffic_violation/update.html', context)


@login_required
def traffic_violation_detail(request, pk):
    if not checkUserPermission(request, "can_view", "/backend/traffic-violation/"):
        messages.error(request, "You do not have permission to view traffic violation details.")
        return render(request, "403.html", status=403)

    violation = get_object_or_404(TrafficViolation, pk=pk)
    context = {'violation': violation}
    return render(request, 'traffic_violation/detail.html', context)


@login_required
def traffic_violation_delete(request, pk):
    if not checkUserPermission(request, "can_delete", "/backend/traffic-violation/"):
        messages.error(request, "You do not have permission to delete traffic violations.")
        return render(request, "403.html", status=403)

    violation = get_object_or_404(TrafficViolation, pk=pk)
    violation.delete()
    messages.success(request, "Traffic violation deleted successfully.")
    return redirect('traffic_violation:list')


# ========================================
# VEHICLE RENT VIEWS
# ========================================
@method_decorator(login_required, name='dispatch')
class VehicleRentListView(ListView):
    model = VehicleRent
    template_name = "vehicle_rent/list.html"
    paginate_by = None

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/vehicle-rent/"):
            messages.error(request, "You do not have permission to view vehicle rents.")
            return render(request, "403.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = VehicleRent.objects.all().order_by('-rent_month')
        
        plate_no = self.request.GET.get('plate_no', '')
        is_paid = self.request.GET.get('is_paid', '')
        
        if plate_no:
            queryset = queryset.filter(vehicle__vehicle__plate_no=plate_no)
        if is_paid:
            queryset = queryset.filter(is_paid=(is_paid == 'true'))
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['rents'] = self.get_queryset()
        context['page_num'] = self.request.GET.get('page', 1)
        context['paginator_list'], context['paginator'], context['last_page_number'] = paginate_data(
            self.request, context['page_num'], context['rents']
        )
        get_param = self.request.GET.copy()
        if 'page' in get_param:
            get_param.pop('page')
        context['get_param'] = get_param.urlencode()
        
        # Add data for select2 dropdowns
        context['all_vehicles'] = Vehicle.objects.filter(is_active=True, deleted=False).order_by('plate_no')
        
        return context


@login_required
def vehicle_rent_create(request):
    if not checkUserPermission(request, "can_add", "/backend/vehicle-rent/"):
        messages.error(request, "You do not have permission to add vehicle rents.")
        return render(request, "403.html", status=403)

    if request.method == 'POST':
        form = VehicleRentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Vehicle rent created successfully.")
            return redirect('vehicle_rent:list')
    else:
        form = VehicleRentForm()

    context = {
        'form': form,
        'vehicles': Vehicle.objects.filter(is_active=True),
    }
    return render(request, 'vehicle_rent/create.html', context)


@login_required
def vehicle_rent_update(request, pk):
    if not checkUserPermission(request, "can_update", "/backend/vehicle-rent/"):
        messages.error(request, "You do not have permission to update vehicle rents.")
        return render(request, "403.html", status=403)

    rent = get_object_or_404(VehicleRent, pk=pk)
    
    if request.method == 'POST':
        form = VehicleRentForm(request.POST, instance=rent)
        if form.is_valid():
            form.save()
            messages.success(request, "Vehicle rent updated successfully.")
            return redirect('vehicle_rent:list')
    else:
        form = VehicleRentForm(instance=rent)

    context = {
        'form': form,
        'rent': rent,
        'vehicles': Vehicle.objects.filter(is_active=True),
    }
    return render(request, 'vehicle_rent/update.html', context)


@login_required
def vehicle_rent_delete(request, pk):
    if not checkUserPermission(request, "can_delete", "/backend/vehicle-rent/"):
        messages.error(request, "You do not have permission to delete vehicle rents.")
        return render(request, "403.html", status=403)

    rent = get_object_or_404(VehicleRent, pk=pk)
    rent.delete()
    messages.success(request, "Vehicle rent deleted successfully.")
    return redirect('vehicle_rent:list')


# ========================================
# VEHICLE MAINTENANCE VIEWS
# ========================================
@method_decorator(login_required, name='dispatch')
class VehicleMaintenanceListView(ListView):
    model = VehicleMaintenance
    template_name = "vehicle_maintenance/list.html"
    paginate_by = None

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/vehicle-maintenance/"):
            messages.error(request, "You do not have permission to view vehicle maintenance.")
            return render(request, "403.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = VehicleMaintenance.objects.all().order_by('-maintenance_date')
        
        plate_no = self.request.GET.get('plate_no', '')
        status = self.request.GET.get('status', '')
        
        if plate_no:
            queryset = queryset.filter(vehicle__vehicle__plate_no__icontains=plate_no)
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['maintenances'] = self.get_queryset()
        context['page_num'] = self.request.GET.get('page', 1)
        context['paginator_list'], context['paginator'], context['last_page_number'] = paginate_data(
            self.request, context['page_num'], context['maintenances']
        )
        get_param = self.request.GET.copy()
        if 'page' in get_param:
            get_param.pop('page')
        context['get_param'] = get_param.urlencode()
        
        # Add data for select2 dropdowns
        context['all_vehicles'] = Vehicle.objects.filter(is_active=True, deleted=False).order_by('plate_no')
        
        return context


@login_required
def vehicle_maintenance_create(request):
    if not checkUserPermission(request, "can_add", "/backend/vehicle-maintenance/"):
        messages.error(request, "You do not have permission to add vehicle maintenance.")
        return render(request, "403.html", status=403)

    if request.method == 'POST':
        form = VehicleMaintenanceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Vehicle maintenance created successfully.")
            return redirect('vehicle_maintenance:list')
    else:
        form = VehicleMaintenanceForm()

    context = {
        'form': form,
        'vehicles': Vehicle.objects.filter(is_active=True),
    }
    return render(request, 'vehicle_maintenance/create.html', context)


@login_required
def vehicle_maintenance_update(request, pk):
    if not checkUserPermission(request, "can_update", "/backend/vehicle-maintenance/"):
        messages.error(request, "You do not have permission to update vehicle maintenance.")
        return render(request, "403.html", status=403)

    maintenance = get_object_or_404(VehicleMaintenance, pk=pk)
    
    if request.method == 'POST':
        form = VehicleMaintenanceForm(request.POST, instance=maintenance)
        if form.is_valid():
            form.save()
            messages.success(request, "Vehicle maintenance updated successfully.")
            return redirect('vehicle_maintenance:list')
    else:
        form = VehicleMaintenanceForm(instance=maintenance)

    context = {
        'form': form,
        'maintenance': maintenance,
        'vehicles': Vehicle.objects.filter(is_active=True),
    }
    return render(request, 'vehicle_maintenance/update.html', context)


@login_required
def vehicle_maintenance_detail(request, pk):
    if not checkUserPermission(request, "can_view", "/backend/vehicle-maintenance/"):
        messages.error(request, "You do not have permission to view vehicle maintenance details.")
        return render(request, "403.html", status=403)

    maintenance = get_object_or_404(VehicleMaintenance, pk=pk)
    context = {'maintenance': maintenance}
    return render(request, 'vehicle_maintenance/detail.html', context)


@login_required
def vehicle_maintenance_delete(request, pk):
    if not checkUserPermission(request, "can_delete", "/backend/vehicle-maintenance/"):
        messages.error(request, "You do not have permission to delete vehicle maintenance.")
        return render(request, "403.html", status=403)

    maintenance = get_object_or_404(VehicleMaintenance, pk=pk)
    maintenance.delete()
    messages.success(request, "Vehicle maintenance deleted successfully.")
    return redirect('vehicle_maintenance:list')


# ========================================
# VEHICLE ACCIDENT VIEWS
# ========================================
@method_decorator(login_required, name='dispatch')
class VehicleAccidentListView(ListView):
    model = VehicleAccident
    template_name = "vehicle_accident/list.html"
    paginate_by = None

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/vehicle-accident/"):
            messages.error(request, "You do not have permission to view vehicle accidents.")
            return render(request, "403.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = VehicleAccident.objects.all().order_by('-accident_date')
        
        plate_no = self.request.GET.get('plate_no', '')
        employee = self.request.GET.get('employee', '')
        insurance_claimed = self.request.GET.get('insurance_claimed', '')
        
        if plate_no:
            queryset = queryset.filter(vehicle__vehicle__plate_no=plate_no)
        if employee:
            queryset = queryset.filter(employee_id=employee)
        if insurance_claimed:
            queryset = queryset.filter(insurance_claimed=(insurance_claimed == 'true'))
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['accidents'] = self.get_queryset()
        context['page_num'] = self.request.GET.get('page', 1)
        context['paginator_list'], context['paginator'], context['last_page_number'] = paginate_data(
            self.request, context['page_num'], context['accidents']
        )
        
        # Add data for select2 dropdowns
        context['all_vehicles'] = Vehicle.objects.filter(is_active=True, deleted=False).select_related('employee').order_by('plate_no')
        context['all_employees'] = Employee.objects.filter(is_active=True).order_by('first_name', 'last_name')
        
        get_param = self.request.GET.copy()
        if 'page' in get_param:
            get_param.pop('page')
        context['get_param'] = get_param.urlencode()
        return context


@login_required
def vehicle_accident_create(request):
    if not checkUserPermission(request, "can_add", "/backend/vehicle-accident/"):
        messages.error(request, "You do not have permission to add vehicle accidents.")
        return render(request, "403.html", status=403)

    if request.method == 'POST':
        form = VehicleAccidentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Vehicle accident created successfully.")
            return redirect('vehicle_accident:list')
    else:
        form = VehicleAccidentForm()

    context = {
        'form': form,
        'vehicles': Vehicle.objects.filter(is_active=True),
        'employees': Employee.objects.filter(is_active=True),
    }
    return render(request, 'vehicle_accident/create.html', context)


@login_required
def vehicle_accident_update(request, pk):
    if not checkUserPermission(request, "can_update", "/backend/vehicle-accident/"):
        messages.error(request, "You do not have permission to update vehicle accidents.")
        return render(request, "403.html", status=403)

    accident = get_object_or_404(VehicleAccident, pk=pk)
    
    if request.method == 'POST':
        form = VehicleAccidentForm(request.POST, instance=accident)
        if form.is_valid():
            form.save()
            messages.success(request, "Vehicle accident updated successfully.")
            return redirect('vehicle_accident:list')
    else:
        form = VehicleAccidentForm(instance=accident)

    context = {
        'form': form,
        'accident': accident,
        'vehicles': Vehicle.objects.filter(is_active=True),
        'employees': Employee.objects.filter(is_active=True),
    }
    return render(request, 'vehicle_accident/update.html', context)


@login_required
def vehicle_accident_detail(request, pk):
    if not checkUserPermission(request, "can_view", "/backend/vehicle-accident/"):
        messages.error(request, "You do not have permission to view vehicle accident details.")
        return render(request, "403.html", status=403)

    accident = get_object_or_404(VehicleAccident, pk=pk)
    context = {'accident': accident}
    return render(request, 'vehicle_accident/detail.html', context)


@login_required
def vehicle_accident_delete(request, pk):
    if not checkUserPermission(request, "can_delete", "/backend/vehicle-accident/"):
        messages.error(request, "You do not have permission to delete vehicle accidents.")
        return render(request, "403.html", status=403)

    accident = get_object_or_404(VehicleAccident, pk=pk)
    accident.delete()
    messages.success(request, "Vehicle accident deleted successfully.")
    return redirect('vehicle_accident:list')


# ========================================
# VEHICLE INSTALLMENT VIEWS
# ========================================
@method_decorator(login_required, name='dispatch')
class VehicleInstallmentListView(ListView):
    model = VehicleInstallment
    template_name = "vehicle_installment/list.html"
    paginate_by = None

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/vehicle-installment/"):
            messages.error(request, "You do not have permission to view vehicle installments.")
            return render(request, "403.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = VehicleInstallment.objects.all().order_by('-due_date')
        
        plate_no = self.request.GET.get('plate_no', '')
        is_paid = self.request.GET.get('is_paid', '')
        
        if plate_no:
            queryset = queryset.filter(vehicle__vehicle__plate_no=plate_no)
        if is_paid:
            queryset = queryset.filter(is_paid=(is_paid == 'true'))
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['installments'] = self.get_queryset()
        context['page_num'] = self.request.GET.get('page', 1)
        context['paginator_list'], context['paginator'], context['last_page_number'] = paginate_data(
            self.request, context['page_num'], context['installments']
        )
        get_param = self.request.GET.copy()
        if 'page' in get_param:
            get_param.pop('page')
        context['get_param'] = get_param.urlencode()
        
        # Add data for select2 dropdowns
        context['all_vehicles'] = Vehicle.objects.filter(is_active=True, deleted=False).order_by('plate_no')
        
        return context


@login_required
def vehicle_installment_create(request):
    if not checkUserPermission(request, "can_add", "/backend/vehicle-installment/"):
        messages.error(request, "You do not have permission to add vehicle installments.")
        return render(request, "403.html", status=403)

    if request.method == 'POST':
        form = VehicleInstallmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Vehicle installment created successfully.")
            return redirect('vehicle_installment:list')
    else:
        form = VehicleInstallmentForm()

    context = {
        'form': form,
        'vehicles': Vehicle.objects.filter(is_active=True),
    }
    return render(request, 'vehicle_installment/create.html', context)


@login_required
def vehicle_installment_update(request, pk):
    if not checkUserPermission(request, "can_update", "/backend/vehicle-installment/"):
        messages.error(request, "You do not have permission to update vehicle installments.")
        return render(request, "403.html", status=403)

    installment = get_object_or_404(VehicleInstallment, pk=pk)
    
    if request.method == 'POST':
        form = VehicleInstallmentForm(request.POST, instance=installment)
        if form.is_valid():
            form.save()
            messages.success(request, "Vehicle installment updated successfully.")
            return redirect('vehicle_installment:list')
    else:
        form = VehicleInstallmentForm(instance=installment)

    context = {
        'form': form,
        'installment': installment,
        'vehicles': Vehicle.objects.filter(is_active=True),
    }
    return render(request, 'vehicle_installment/update.html', context)


@login_required
def vehicle_installment_delete(request, pk):
    if not checkUserPermission(request, "can_delete", "/backend/vehicle-installment/"):
        messages.error(request, "You do not have permission to delete vehicle installments.")
        return render(request, "403.html", status=403)

    installment = get_object_or_404(VehicleInstallment, pk=pk)
    installment.delete()
    messages.success(request, "Vehicle installment deleted successfully.")
    return redirect('vehicle_installment:list')


# ========================================
# VEHICLE ITEM VIEWS
# ========================================
@method_decorator(login_required, name='dispatch')
class VehicleItemListView(ListView):
    model = VehicleItem
    template_name = "vehicle_item/list.html"
    paginate_by = None

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/vehicle-item/"):
            messages.error(request, "You do not have permission to view vehicle items.")
            return render(request, "403.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = VehicleItem.objects.all().order_by('-issued_date')
        
        plate_no = self.request.GET.get('plate_no', '')
        item_name = self.request.GET.get('item_name', '')
        is_missing = self.request.GET.get('is_missing', '')
        
        if plate_no:
            queryset = queryset.filter(vehicle__vehicle__plate_no=plate_no)
        if item_name:
            queryset = queryset.filter(item_name__icontains=item_name)
        if is_missing:
            queryset = queryset.filter(is_missing=(is_missing == 'true'))
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.get_queryset()
        context['page_num'] = self.request.GET.get('page', 1)
        context['paginator_list'], context['paginator'], context['last_page_number'] = paginate_data(
            self.request, context['page_num'], context['items']
        )
        get_param = self.request.GET.copy()
        if 'page' in get_param:
            get_param.pop('page')
        context['get_param'] = get_param.urlencode()
        
        # Add data for select2 dropdowns
        context['all_vehicles'] = Vehicle.objects.filter(is_active=True).select_related('vehicle_info').order_by('vehicle_info__plate_no')
        
        return context


@login_required
def vehicle_item_create(request):
    if not checkUserPermission(request, "can_add", "/backend/vehicle-item/"):
        messages.error(request, "You do not have permission to add vehicle items.")
        return render(request, "403.html", status=403)

    if request.method == 'POST':
        form = VehicleItemForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Vehicle item created successfully.")
            return redirect('vehicle_item:list')
    else:
        form = VehicleItemForm()

    context = {
        'form': form,
        'vehicles': Vehicle.objects.filter(is_active=True),
    }
    return render(request, 'vehicle_item/create.html', context)


@login_required
def vehicle_item_update(request, pk):
    if not checkUserPermission(request, "can_update", "/backend/vehicle-item/"):
        messages.error(request, "You do not have permission to update vehicle items.")
        return render(request, "403.html", status=403)

    item = get_object_or_404(VehicleItem, pk=pk)
    
    if request.method == 'POST':
        form = VehicleItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, "Vehicle item updated successfully.")
            return redirect('vehicle_item:list')
    else:
        form = VehicleItemForm(instance=item)

    context = {
        'form': form,
        'item': item,
        'vehicles': Vehicle.objects.filter(is_active=True),
    }
    return render(request, 'vehicle_item/update.html', context)


@login_required
def vehicle_item_delete(request, pk):
    if not checkUserPermission(request, "can_delete", "/backend/vehicle-item/"):
        messages.error(request, "You do not have permission to delete vehicle items.")
        return render(request, "403.html", status=403)

    item = get_object_or_404(VehicleItem, pk=pk)
    item.delete()
    messages.success(request, "Vehicle item deleted successfully.")
    return redirect('vehicle_item:list')