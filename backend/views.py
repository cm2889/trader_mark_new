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
)

from backend.forms import (
    CustomUserLoginForm, NationalityForm, EmployeeForm, EmploymentForm, 
    PassportForm, DrivingLicenseForm, HealthInsuranceForm, ContactForm, 
    AddressForm, VehicleForm,  UserCreateForm

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

    return data_list, paginator_list, last_page_number



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
class EmployeementListView(ListView):
    model = Employment 
    template_name = "employeement/list.html"
    context_object_name = 'employeements'

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/employeement/"):
            messages.error(request, "You do not have permission to view employeements.")
            return render(request, "403.html", status=403) 
        return super().dispatch(request, *args, **kwargs)

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

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/employeement/"):
            messages.error(request, "You do not have permission to view employeement details.")
            return render(request, "403.html") 
        return super().dispatch(request, *args, **kwargs) 


@method_decorator(login_required, name='dispatch')
class PassportListView(ListView):
    model = Passport 
    template_name = "passport/list.html" 
    context_object_name = 'passports'


    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/passport/"):
            messages.error(request, "You do not have permission to view passports.")
            return render(request, "403.html") 
        return super().dispatch(request, *args, **kwargs) 

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

    if not checkUserPermission(request, "can_delete", "/backend/passport/"):
        messages.error(request, "You do not have permission to delete passports.")
        return render(request, "403.html") 
    
    passport = Passport.objects.get(pk=pk)
    passport.is_active = False
    passport.save()
    return redirect('passport:list') 


@method_decorator(login_required, name='dispatch')
class PassportDetailView(DetailView):
    model = Passport 
    template_name = "passport/detail.html" 
    context_object_name = 'passport'

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/passport/"):
            messages.error(request, "You do not have permission to view passport details.")
            return render(request, "403.html") 
        return super().dispatch(request, *args, **kwargs) 


@method_decorator(login_required, name='dispatch')
class DrivingLicenseListView(ListView):
    model = DrivingLicense 
    template_name = "driving_license/list.html" 
    context_object_name = 'driving_licenses'

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/driving_license/"):
            messages.error(request, "You do not have permission to view driving licenses.")
            return render(request, "403.html") 
        return super().dispatch(request, *args, **kwargs) 

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
    if not checkUserPermission(request, "can_delete", "/backend/driving_license/"):
        messages.error(request, "You do not have permission to delete driving licenses.")
        return render(request, "403.html") 
    driving_license = DrivingLicense.objects.get(pk=pk)
    driving_license.is_active = False
    driving_license.save()
    return redirect('driving_license:list') 


@method_decorator(login_required, name='dispatch')
class DrivingLicenseDetailView(DetailView):
    model = DrivingLicense 
    template_name = "driving_license/detail.html" 
    context_object_name = 'driving_license'

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/driving_license/"):
            messages.error(request, "You do not have permission to view driving license details.")
            return render(request, "403.html") 
        return super().dispatch(request, *args, **kwargs) 


@method_decorator(login_required, name='dispatch')
class HealthInsuranceListView(ListView):
    model = HealthInsurance 
    template_name = "health_insurance/list.html" 
    context_object_name = 'health_insurances'

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/health_insurance/"):
            messages.error(request, "You do not have permission to view health insurances.")
            return render(request, "403.html") 
        return super().dispatch(request, *args, **kwargs) 

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

    if not checkUserPermission(request, "can_delete", "/backend/health_insurance/"):
        messages.error(request, "You do not have permission to delete health insurances.")
        return render(request, "403.html") 
    
    health_insurance = HealthInsurance.objects.get(pk=pk)
    health_insurance.is_active = False
    health_insurance.save()
    return redirect('health_insurance:list') 


@method_decorator(login_required, name='dispatch')
class HealthInsuranceDetailView(DetailView):
    model = HealthInsurance 
    template_name = "health_insurance/detail.html" 
    context_object_name = 'health_insurance'

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/health_insurance/"):
            messages.error(request, "You do not have permission to view health insurance details.")
            return render(request, "403.html") 
        return super().dispatch(request, *args, **kwargs) 


@method_decorator(login_required, name='dispatch')
class ContactListView(ListView):
    model = Contact 
    template_name = "contact/list.html" 
    context_object_name = 'contacts'

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/contact/"):
            messages.error(request, "You do not have permission to view contacts.")
            return render(request, "403.html") 
        return super().dispatch(request, *args, **kwargs) 

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
    if not checkUserPermission(request, "can_delete", "/backend/contact/"):
        messages.error(request, "You do not have permission to delete contacts.")
        return render(request, "403.html") 
    
    contact = Contact.objects.get(pk=pk)
    contact.is_active = False
    contact.save()
    return redirect('contact:list') 


@method_decorator(login_required, name='dispatch')
class ContactDetailView(DetailView):
    model = Contact 
    template_name = "contact/detail.html" 
    context_object_name = 'contact'

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/contact/"):
            messages.error(request, "You do not have permission to view contact details.")
            return render(request, "403.html") 
        return super().dispatch(request, *args, **kwargs) 


@method_decorator(login_required, name='dispatch')
class AddressListView(ListView):
    model = Address 
    template_name = "address/list.html" 
    context_object_name = 'addresses'

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/address/"):
            messages.error(request, "You do not have permission to view addresses.")
            return render(request, "403.html") 
        return super().dispatch(request, *args, **kwargs) 

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
    if not checkUserPermission(request, "can_delete", "/backend/address/"):
        messages.error(request, "You do not have permission to delete addresses.")
        return render(request, "403.html") 
    
    address = Address.objects.get(pk=pk)
    address.is_active = False
    address.save()
    return redirect('address:list') 


@method_decorator(login_required, name='dispatch')
class AddressDetailView(DetailView):
    model = Address 
    template_name = "address/detail.html" 
    context_object_name = 'address'

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/address/"):
            messages.error(request, "You do not have permission to view address details.")
            return render(request, "403.html") 
        return super().dispatch(request, *args, **kwargs) 


@method_decorator(login_required, name='dispatch')
class VehicleListView(ListView):
    model = Vehicle 
    template_name = "vehicle/list.html" 
    context_object_name = 'vehicles'

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/vehicle/"):
            messages.error(request, "You do not have permission to view vehicles.")
            return render(request, "403.html") 
        return super().dispatch(request, *args, **kwargs) 

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
    if not checkUserPermission(request, "can_delete", "/backend/vehicle/"):
        messages.error(request, "You do not have permission to delete vehicles.")
        return render(request, "403.html") 


    vehicle = Vehicle.objects.get(pk=pk)
    vehicle.is_active = False
    vehicle.save()
    return redirect('vehicle:list') 


@method_decorator(login_required, name='dispatch')
class VehicleDetailView(DetailView):
    model = Vehicle 
    template_name = "vehicle/detail.html" 
    context_object_name = 'vehicle'

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/vehicle/"):
            messages.error(request, "You do not have permission to view vehicle details.")
            return render(request, "403.html") 
        return super().dispatch(request, *args, **kwargs) 