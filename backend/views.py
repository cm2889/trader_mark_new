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
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.conf import settings
from django.core.cache import cache
from PIL import Image
from io import BytesIO
from django.utils.text import slugify 
from django.utils import timezone
from datetime import datetime 
from django.db.models import Sum, Count, Q, F
from backend.models import UniformStockTransactionLog

from backend.models import (
    WebImages, SiteSettings, LoginLog, UserMenuPermission, 
    BackendMenu, 
    Visitor, 
    Nationality, Employee, Employment, Passport, DrivingLicense, 
    HealthInsurance, Contact, Address, Vehicle, InsuranceClaim, 
    VehicleHandover, TrafficViolation,ViolationType, TrafficViolationPenalty, 
    VehicleInstallment, VehicleMaintenance, VehicleAccident, VehicleAssign, 
    ViolationType, VehicleMaintananceType, 
    Uniform, UniformStock, UniformIssuance, UniformClearance, VehiclePurchase 
)

from backend.forms import (
    CustomUserLoginForm, NationalityForm, EmployeeForm, EmploymentForm, VehicleMaintananceTypeForm, 
    PassportForm, DrivingLicenseForm, HealthInsuranceForm, ContactForm, 
    AddressForm, UserCreateForm, VehicleForm, VisitorForm, InsuranceClaimForm, 
    VehicleHandoverForm, TrafficViolationForm, ViolationTypeForm, TrafficViolationPenaltyForm, 
    VehicleInstallmentForm, VehicleMaintenanceForm, VehicleAccidentForm, VehicleAssignForm, 
    UniformForm, UniformStockForm, UniformIssuanceForm, UniformClearanceForm,
    VehiclePurchaseForm, InstallmentPaymentForm
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


# @login_required
# def user_add(request):
#     if not checkUserPermission(request, "can_add", "/backend/user/"):
#         return render(request, "403.html", status=403)

#     if request.method == 'POST':
#         form = UserCreateForm(request.POST, request.FILES)
#         if form.is_valid():
#             form.save()
#             messages.success(request, 'New user has been added successfully!')
#             return redirect('backend:user_list')
#         else:
#             for field, errors in form.errors.items():
#                 for error in errors:
#                     messages.error(request, f"{field}: {error}")
#     else:
#         form = UserCreateForm()

#     return render(request, 'user/add.html', {'form': form})


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
        queryset = Nationality.objects.filter(is_active=True)

        name_id = self.request.GET.get('name', '') 
        code_id = self.request.GET.get('code', '')

        if name_id:
            queryset = queryset.filter(id=name_id)
        if code_id:
            queryset = queryset.filter(id=code_id)

        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nationalities'] = self.get_queryset()
        context['all_nationalities'] = Nationality.objects.filter(is_active=True).order_by('name')
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


@method_decorator(login_required, name='dispatch')
class VisitorListView(ListView):
    model = Visitor 
    template_name = "visitor/list.html" 
    paginate_by = None 

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/visitor/"):
            messages.error(request, "You do not have permission to view visitors.")
            return render(request, "403.html", status=403)
        return super().dispatch(request, *args, **kwargs) 
    
    def get_queryset(self):
        queryset = Visitor.objects.filter(is_active=True)

        name_id = self.request.GET.get('name', '')
        email = self.request.GET.get('email', '')
        phone = self.request.GET.get('phone', '') 

        if name_id:
            queryset = queryset.filter(id=name_id)
        if email:
            queryset = queryset.filter(email=email)
        if phone:
            queryset = queryset.filter(phone_number=phone)

        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['visitors'] = self.get_queryset()
        context['all_visitors'] = Visitor.objects.filter(is_active=True).order_by('first_name', 'last_name')
        context['page_num'] = self.request.GET.get('page', 1)
        context['paginator_list'], context['paginator'], context['last_page_number'] = paginate_data(self.request, context['page_num'], context['visitors'])

        get_param = self.request.GET.copy()
        if 'page' in get_param:
            get_param.pop('page')
        context['get_param'] = get_param.urlencode() 
        return context
    

@method_decorator(login_required, name='dispatch')
class VisitorCreateView(CreateView):
    model = Visitor
    template_name = "visitor/create.html"
    form_class = VisitorForm
    success_url = reverse_lazy('visitor:list')

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_add", "/backend/visitor/"):
            messages.error(request, "You do not have permission to add visitors.")
            return render(request, "403.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form) 
    

@method_decorator(login_required, name='dispatch')
class VisitorUpdateView(UpdateView):
    model = Visitor
    template_name = "visitor/update.html"
    form_class = VisitorForm
    success_url = reverse_lazy('visitor:list')

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_update", "/backend/visitor/"):
            messages.error(request, "You do not have permission to update visitors.")
            return render(request, "403.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form) 


@login_required
def visitor_delete(request, pk):
    if not checkUserPermission(request, "can_delete", "/backend/visitor/"):
        messages.error(request, "You do not have permission to delete visitors.")
        return render(request, "403.html", status=403)
    
    visitor = Visitor.objects.get(pk=pk)
    visitor.is_active = False
    visitor.save()
    return redirect('visitor:list') 


@login_required
def get_visitor_by_contact(request):
    """
    AJAX endpoint to fetch visitor data by email or phone number
    """
    email = request.GET.get('email', '').strip()
    phone = request.GET.get('phone', '').strip()
    
    visitor = None
    matched_by = None
    
    # Try to find visitor by email first
    if email:
        visitor = Visitor.objects.filter(email__iexact=email, is_active=True).first()
        if visitor:
            matched_by = 'email'
    
    # If not found by email, try by phone
    if not visitor and phone:
        visitor = Visitor.objects.filter(phone_number__iexact=phone, is_active=True).first()
        if visitor:
            matched_by = 'phone'
    
    if visitor:
        return JsonResponse({
            'found': True,
            'matched_by': matched_by,
            'data': {
                'first_name': visitor.first_name or '',
                'last_name': visitor.last_name or '',
                'email': visitor.email or '',
                'phone_number': visitor.phone_number or '',
            },
            'message': f'Visitor data found: {visitor.first_name} {visitor.last_name}'
        })
    else:
        return JsonResponse({'found': False, 'message': ''})


@login_required
def employee_create(request):

    if not checkUserPermission(request, "can_add", "/backend/employee/"):
        messages.error(request, "You do not have permission to add employees.")
        return render(request, "403.html", status=403)

    if request.method == 'POST':
        employee_form = EmployeeForm(request.POST, request.FILES, prefix='employee')
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

            # Save Multiple Employment forms
            employment_index = 0
            while True:
                # Check if employment data exists for this index
                employment_prefix = f'employment-{employment_index}'
                joining_date_key = f'{employment_prefix}-joining_date'
                
                if joining_date_key not in request.POST:
                    break
                
                # Extract employment data for this index
                employment_data = {
                    'joining_date': request.POST.get(f'{employment_prefix}-joining_date'),
                    'work_status': request.POST.get(f'{employment_prefix}-work_status'),
                    'rp_expiry_date': request.POST.get(f'{employment_prefix}-rp_expiry_date'),
                    'work_permit_no': request.POST.get(f'{employment_prefix}-work_permit_no'),
                    'work_id': request.POST.get(f'{employment_prefix}-work_id'),
                    'qid_renew_status': request.POST.get(f'{employment_prefix}-qid_renew_status'),
                    'qid_lost_status': request.POST.get(f'{employment_prefix}-qid_lost_status'),
                }
                
                # Check if any data is provided
                has_data = any([v for v in employment_data.values() if v not in [None, '', []]])
                
                if has_data:
                    employment = Employment(
                        employee=employee,
                        created_by=request.user,
                        updated_by=request.user
                    )
                    
                    if employment_data['joining_date']:
                        employment.joining_at = employment_data['joining_date']
                    if employment_data['work_status']:
                        employment.work_status = employment_data['work_status']
                    if employment_data['rp_expiry_date']:
                        employment.rp_expiry_date = employment_data['rp_expiry_date']
                    if employment_data['work_permit_no']:
                        employment.work_permit_no = employment_data['work_permit_no']
                    if employment_data['work_id']:
                        employment.work_id = employment_data['work_id']
                    if employment_data['qid_renew_status']:
                        employment.qid_renew_status = employment_data['qid_renew_status']
                    if employment_data['qid_lost_status']:
                        employment.qid_lost_status = employment_data['qid_lost_status']
                    
                    employment.save()
                
                employment_index += 1

            # Save Multiple Passport forms
            passport_index = 0
            while True:
                # Check if passport data exists for this index
                passport_prefix = f'passport-{passport_index}'
                passport_no_key = f'{passport_prefix}-passport_no'
                
                if passport_no_key not in request.POST:
                    break
                
                # Extract passport data for this index
                passport_data = {
                    'passport_no': request.POST.get(f'{passport_prefix}-passport_no'),
                    'passport_expiry_date': request.POST.get(f'{passport_prefix}-passport_expiry_date'),
                    'passport_renewed': request.POST.get(f'{passport_prefix}-passport_renewed'),
                }
                
                # Check if any data is provided
                has_data = any([v for v in passport_data.values() if v not in [None, '', []]])
                
                if has_data:
                    passport = Passport(
                        employee=employee,
                        created_by=request.user,
                        updated_by=request.user
                    )
                    
                    if passport_data['passport_no']:
                        passport.passport_no = passport_data['passport_no']
                    if passport_data['passport_expiry_date']:
                        passport.passport_expiry_date = passport_data['passport_expiry_date']
                    if passport_data['passport_renewed']:
                        passport.passport_renewed = True
                    
                    passport.save()
                
                passport_index += 1

            # Save Multiple Driving License forms
            license_index = 0
            while True:
                # Check if driving license data exists for this index
                license_prefix = f'driving_license-{license_index}'
                license_no_key = f'{license_prefix}-license_no'
                
                if license_no_key not in request.POST:
                    break
                
                # Extract driving license data for this index
                license_data = {
                    'license_no': request.POST.get(f'{license_prefix}-license_no'),
                    'license_expiry_date': request.POST.get(f'{license_prefix}-license_expiry_date'),
                    'license_renewed': request.POST.get(f'{license_prefix}-license_renewed'),
                    'license_renew_status': request.POST.get(f'{license_prefix}-license_renew_status'),
                }
                
                # Check if any data is provided
                has_data = any([v for v in license_data.values() if v not in [None, '', []]])
                
                if has_data:
                    driving_license = DrivingLicense(
                        employee=employee,
                        created_by=request.user,
                        updated_by=request.user
                    )
                    
                    if license_data['license_no']:
                        driving_license.license_no = license_data['license_no']
                    if license_data['license_expiry_date']:
                        driving_license.license_expiry_date = license_data['license_expiry_date']
                    if license_data['license_renewed']:
                        driving_license.license_renewed = True
                    if license_data['license_renew_status']:
                        driving_license.license_renew_status = license_data['license_renew_status']
                    
                    driving_license.save()
                
                license_index += 1

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
        passport_form = PassportForm(prefix='passport')
        driving_license_form = DrivingLicenseForm(prefix='driving_license')
        health_insurance_form = HealthInsuranceForm(prefix='health_insurance')
        contact_form = ContactForm(prefix='contact')
        address_form = AddressForm(prefix='address')

    context = {
        'employee_form': employee_form,
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
    employments = Employment.objects.filter(employee=employee, is_active=True)
    health_insurance = HealthInsurance.objects.filter(employee=employee, is_active=True).first()
    contact = Contact.objects.filter(employee=employee, is_active=True).first()
    address = Address.objects.filter(employee=employee, is_active=True).first()

    if request.method == 'POST':
        employee_form = EmployeeForm(request.POST, request.FILES, instance=employee, prefix='employee')
        health_insurance_form = HealthInsuranceForm(request.POST, instance=health_insurance, prefix='health_insurance')
        contact_form = ContactForm(request.POST, instance=contact, prefix='contact')
        address_form = AddressForm(request.POST, instance=address, prefix='address')

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

            # Handle deleted employments
            deleted_ids = request.POST.get('employment-DELETED_IDS', '')
            if deleted_ids:
                deleted_id_list = [int(id) for id in deleted_ids.split(',') if id]
                Employment.objects.filter(id__in=deleted_id_list, employee=employee).update(is_active=False, deleted=True)

            # Handle multiple employment forms
            employment_index = 0
            while True:
                employment_prefix = f'employment-{employment_index}'
                joining_date_key = f'{employment_prefix}-joining_date'
                
                if joining_date_key not in request.POST:
                    break
                
                # Extract employment data for this index
                employment_id = request.POST.get(f'{employment_prefix}-id')
                employment_data = {
                    'joining_date': request.POST.get(f'{employment_prefix}-joining_date'),
                    'work_status': request.POST.get(f'{employment_prefix}-work_status'),
                    'rp_expiry_date': request.POST.get(f'{employment_prefix}-rp_expiry_date'),
                    'work_permit_no': request.POST.get(f'{employment_prefix}-work_permit_no'),
                    'work_id': request.POST.get(f'{employment_prefix}-work_id'),
                    'qid_renew_status': request.POST.get(f'{employment_prefix}-qid_renew_status'),
                    'qid_lost_status': request.POST.get(f'{employment_prefix}-qid_lost_status'),
                }
                
                # Check if any data is provided
                has_data = any([v for v in employment_data.values() if v not in [None, '', []]])
                
                if has_data:
                    if employment_id:
                        # Update existing employment
                        try:
                            emp_obj = Employment.objects.get(id=employment_id, employee=employee)
                            emp_obj.updated_by = request.user
                        except Employment.DoesNotExist:
                            emp_obj = Employment(employee=employee, created_by=request.user, updated_by=request.user)
                    else:
                        # Create new employment
                        emp_obj = Employment(employee=employee, created_by=request.user, updated_by=request.user)
                    
                    if employment_data['joining_date']:
                        emp_obj.joining_at = employment_data['joining_date']
                    if employment_data['work_status']:
                        emp_obj.work_status = employment_data['work_status']
                    if employment_data['rp_expiry_date']:
                        emp_obj.rp_expiry_date = employment_data['rp_expiry_date']
                    if employment_data['work_permit_no']:
                        emp_obj.work_permit_no = employment_data['work_permit_no']
                    if employment_data['work_id']:
                        emp_obj.work_id = employment_data['work_id']
                    if employment_data['qid_renew_status']:
                        emp_obj.qid_renew_status = employment_data['qid_renew_status']
                    if employment_data['qid_lost_status']:
                        emp_obj.qid_lost_status = employment_data['qid_lost_status']
                    
                    emp_obj.save()
                
                employment_index += 1

            # Handle multiple passport forms
            passport_index = 0
            while True:
                passport_prefix = f'passport-{passport_index}'
                passport_no_key = f'{passport_prefix}-passport_no'
                
                if passport_no_key not in request.POST:
                    break
                
                passport_data = {
                    'passport_no': request.POST.get(f'{passport_prefix}-passport_no'),
                    'passport_expiry_date': request.POST.get(f'{passport_prefix}-passport_expiry_date'),
                    'passport_renewed': request.POST.get(f'{passport_prefix}-passport_renewed') == 'on',
                }
                
                # Check if any data is provided
                has_data = any([v for k, v in passport_data.items() if v not in [None, '', [], False] and k != 'passport_renewed'])
                
                if has_data:
                    # Try to find existing passport by passport_no or create new
                    passport_obj = None
                    if passport_data['passport_no']:
                        passport_obj = Passport.objects.filter(
                            employee=employee, 
                            passport_no=passport_data['passport_no']
                        ).first()
                    
                    if passport_obj:
                        # Update existing
                        passport_obj.updated_by = request.user
                    else:
                        # Create new
                        passport_obj = Passport(employee=employee, created_by=request.user, updated_by=request.user)
                    
                    if passport_data['passport_no']:
                        passport_obj.passport_no = passport_data['passport_no']
                    if passport_data['passport_expiry_date']:
                        passport_obj.passport_expiry_date = passport_data['passport_expiry_date']
                    passport_obj.passport_renewed = passport_data['passport_renewed']
                    
                    passport_obj.save()
                
                passport_index += 1

            # Handle multiple driving license forms
            license_index = 0
            while True:
                license_prefix = f'driving_license-{license_index}'
                license_no_key = f'{license_prefix}-license_no'
                
                if license_no_key not in request.POST:
                    break
                
                license_data = {
                    'license_no': request.POST.get(f'{license_prefix}-license_no'),
                    'license_expiry_date': request.POST.get(f'{license_prefix}-license_expiry_date'),
                    'license_renewed': request.POST.get(f'{license_prefix}-license_renewed') == 'on',
                    'license_renew_status': request.POST.get(f'{license_prefix}-license_renew_status'),
                }
                
                # Check if any data is provided
                has_data = any([v for k, v in license_data.items() if v not in [None, '', [], False] and k != 'license_renewed'])
                
                if has_data:
                    # Try to find existing license by license_no or create new
                    license_obj = None
                    if license_data['license_no']:
                        license_obj = DrivingLicense.objects.filter(
                            employee=employee,
                            license_no=license_data['license_no']
                        ).first()
                    
                    if license_obj:
                        # Update existing
                        license_obj.updated_by = request.user
                    else:
                        # Create new
                        license_obj = DrivingLicense(employee=employee, created_by=request.user, updated_by=request.user)
                    
                    if license_data['license_no']:
                        license_obj.license_no = license_data['license_no']
                    if license_data['license_expiry_date']:
                        license_obj.license_expiry_date = license_data['license_expiry_date']
                    license_obj.license_renewed = license_data['license_renewed']
                    if license_data['license_renew_status']:
                        license_obj.license_renew_status = license_data['license_renew_status']
                    
                    license_obj.save()
                
                license_index += 1

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

            messages.success(request, 'Employee updated successfully!')
            return redirect('employee:list')
    else:
        employee_form = EmployeeForm(instance=employee, prefix='employee')
        health_insurance_form = HealthInsuranceForm(instance=health_insurance, prefix='health_insurance')
        contact_form = ContactForm(instance=contact, prefix='contact')
        address_form = AddressForm(instance=address, prefix='address')

    # Get all passports and driving licenses for display
    passports = Passport.objects.filter(employee=employee, is_active=True).order_by('-created_at')
    driving_licenses = DrivingLicense.objects.filter(employee=employee, is_active=True).order_by('-created_at')

    context = {
        'employee': employee,
        'employee_form': employee_form,
        'employments': employments,
        'passports': passports,
        'driving_licenses': driving_licenses,
        'health_insurance_form': health_insurance_form,
        'contact_form': contact_form,
        'address_form': address_form,
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
def employee_profile(request, pk):
    """
    Comprehensive employee profile view showing all details and history
    """
    if not checkUserPermission(request, "can_view", "/backend/employee/"):
        messages.error(request, "You do not have permission to view employee profile.")
        return render(request, "403.html", status=403)

    employee = get_object_or_404(Employee, pk=pk, is_active=True)
    
    # Basic Employee Information
    employments = Employment.objects.filter(employee=employee, is_active=True).order_by('-created_at')
    employment_history = Employment.objects.filter(employee=employee).order_by('-created_at')
    
    # Passport Information
    passports = Passport.objects.filter(employee=employee, is_active=True).order_by('-created_at')
    passport_history = Passport.objects.filter(employee=employee).order_by('-created_at')
    
    # Driving License Information
    driving_licenses = DrivingLicense.objects.filter(employee=employee, is_active=True).order_by('-created_at')
    driving_license_history = DrivingLicense.objects.filter(employee=employee).order_by('-created_at')
    
    # Health Insurance & Contact
    health_insurance = HealthInsurance.objects.filter(employee=employee, is_active=True).first()
    contact = Contact.objects.filter(employee=employee, is_active=True).first()
    address = Address.objects.filter(employee=employee, is_active=True).first()
    
    # ============================================
    # UNIFORM STATISTICS & HISTORY
    # ============================================
    
    # Total uniforms issued to employee
    uniform_issuances = UniformIssuance.objects.filter(
        employee=employee, is_active=True
    ).select_related('uniform_stock__uniform').order_by('-issued_date')
    
    # Count uniforms by status
    total_uniforms_issued = uniform_issuances.aggregate(total=Sum('quantity'))['total'] or 0
    total_uniforms_active = uniform_issuances.filter(status='ISSUED').aggregate(total=Sum('quantity'))['total'] or 0
    total_uniforms_returned = uniform_issuances.filter(status='RETURNED').aggregate(total=Sum('quantity'))['total'] or 0
    total_uniforms_lost = uniform_issuances.filter(status='LOST').aggregate(total=Sum('quantity'))['total'] or 0
    total_uniforms_damaged = uniform_issuances.filter(status='DAMAGED').aggregate(total=Sum('quantity'))['total'] or 0
    
    # Uniform breakdown by type
    uniform_by_type = uniform_issuances.values(
        'uniform_stock__uniform__name',
        'uniform_stock__uniform__uniform_type',
        'uniform_stock__size',
        'status'
    ).annotate(
        total_qty=Sum('quantity')
    ).order_by('uniform_stock__uniform__name')
    
    # Uniform clearance history
    uniform_clearances = UniformClearance.objects.filter(
        employee=employee, is_active=True
    ).select_related('uniform_stock__uniform').order_by('-clearance_date')
    
    # ============================================
    # VEHICLE STATISTICS & HISTORY
    # ============================================
    
    # Current vehicle assignment
    current_vehicle_assign = VehicleAssign.objects.filter(
        employee=employee, is_active=True, deleted=False
    ).select_related('vehicle').first()
    
    # All vehicle assignments history
    vehicle_assignments = VehicleAssign.objects.filter(
        employee=employee, deleted=False
    ).select_related('vehicle').order_by('-assigned_date')
    
    total_vehicles_assigned = vehicle_assignments.count()
    
    # Vehicle handover history (both from and to)
    vehicle_handovers_from = VehicleHandover.objects.filter(
        from_employee=employee, is_active=True
    ).select_related('vehicle', 'to_employee').order_by('-handover_date')
    
    vehicle_handovers_to = VehicleHandover.objects.filter(
        to_employee=employee, is_active=True
    ).select_related('vehicle', 'from_employee').order_by('-handover_date')
    
    # Vehicle purchases by employee
    vehicle_purchases = VehiclePurchase.objects.filter(
        employee=employee, is_active=True
    ).select_related('vehicle').order_by('-purchase_date')
    
    total_vehicle_purchases = vehicle_purchases.count()
    total_purchase_amount = vehicle_purchases.aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Vehicle installments
    vehicle_installments = VehicleInstallment.objects.filter(
        purchase__employee=employee, is_active=True
    ).select_related('purchase__vehicle').order_by('-due_date')
    
    total_installments = vehicle_installments.count()
    paid_installments = vehicle_installments.filter(is_paid=True).count()
    pending_installments = vehicle_installments.filter(is_paid=False).count()
    total_installment_amount = vehicle_installments.aggregate(total=Sum('amount'))['total'] or 0
    paid_installment_amount = vehicle_installments.filter(is_paid=True).aggregate(total=Sum('amount'))['total'] or 0
    pending_installment_amount = total_installment_amount - (paid_installment_amount or 0)
    
    # Traffic violations (through assigned vehicles)
    traffic_violations = TrafficViolation.objects.filter(
        vehicle__vehicle_assignments__employee=employee,
        vehicle__vehicle_assignments__is_active=True
    ).select_related('vehicle', 'violation_type').order_by('-violation_date')
    
    total_traffic_violations = traffic_violations.count()
    
    # Vehicle maintenance history
    vehicle_maintenances = VehicleMaintenance.objects.filter(
        vehicle__vehicle_assignments__employee=employee,
        vehicle__vehicle_assignments__is_active=True
    ).select_related('vehicle', 'maintenance_type').order_by('-maintenance_date')
    
    total_maintenance_cost = vehicle_maintenances.aggregate(total=Sum('cost'))['total'] or 0
    
    # Vehicle accidents
    vehicle_accidents = VehicleAccident.objects.filter(
        vehicle__vehicle_assignments__employee=employee,
        vehicle__vehicle_assignments__is_active=True
    ).select_related('vehicle').order_by('-accident_date')
    
    total_accidents = vehicle_accidents.count()
    total_accident_damage = vehicle_accidents.aggregate(total=Sum('damage_cost'))['total'] or 0

    context = {
        'employee': employee,
        
        # Employment Details
        'employments': employments,
        'employment_history': employment_history,
        'current_employment': employments.first() if employments.exists() else None,
        
        # Passport & License
        'passports': passports,
        'passport_history': passport_history,
        'current_passport': passports.first() if passports.exists() else None,
        'driving_licenses': driving_licenses,
        'driving_license_history': driving_license_history,
        'current_license': driving_licenses.first() if driving_licenses.exists() else None,
        
        # Health & Contact
        'health_insurance': health_insurance,
        'contact': contact,
        'address': address,
        
        # Uniform Statistics
        'uniform_stats': {
            'total_issued': total_uniforms_issued,
            'active': total_uniforms_active,
            'returned': total_uniforms_returned,
            'lost': total_uniforms_lost,
            'damaged': total_uniforms_damaged,
        },
        'uniform_issuances': uniform_issuances,
        'uniform_by_type': uniform_by_type,
        'uniform_clearances': uniform_clearances,
        
        # Vehicle Statistics
        'vehicle_stats': {
            'total_assigned': total_vehicles_assigned,
            'current_vehicle': current_vehicle_assign.vehicle if current_vehicle_assign else None,
            'total_purchases': total_vehicle_purchases,
            'total_purchase_amount': total_purchase_amount,
            'total_violations': total_traffic_violations,
            'total_accidents': total_accidents,
            'total_accident_damage': total_accident_damage,
            'total_maintenance_cost': total_maintenance_cost,
        },
        'current_vehicle_assign': current_vehicle_assign,
        'vehicle_assignments': vehicle_assignments,
        'vehicle_handovers_from': vehicle_handovers_from,
        'vehicle_handovers_to': vehicle_handovers_to,
        'vehicle_purchases': vehicle_purchases,
        'vehicle_installments': vehicle_installments,
        'installment_stats': {
            'total': total_installments,
            'paid': paid_installments,
            'pending': pending_installments,
            'total_amount': total_installment_amount,
            'paid_amount': paid_installment_amount or 0,
            'pending_amount': pending_installment_amount,
        },
        'traffic_violations': traffic_violations,
        'vehicle_maintenances': vehicle_maintenances,
        'vehicle_accidents': vehicle_accidents,
    }

    return render(request, 'employee/profile.html', context)


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

        # Get all related records
        context['employments'] = Employment.objects.filter(employee=employee, is_active=True).order_by('-created_at')
        context['employment_history'] = Employment.objects.filter(employee=employee).order_by('-created_at')
        
        # Passport - get all passports (active and history)
        context['passports'] = Passport.objects.filter(employee=employee, is_active=True).order_by('-created_at')
        context['passport'] = Passport.objects.filter(employee=employee, is_active=True).first()
        context['passport_history'] = Passport.objects.filter(employee=employee).order_by('-created_at')
        
        # Driving License - get all licenses (active and history)
        context['driving_licenses'] = DrivingLicense.objects.filter(employee=employee, is_active=True).order_by('-created_at')
        context['driving_license'] = DrivingLicense.objects.filter(employee=employee, is_active=True).first()
        context['driving_license_history'] = DrivingLicense.objects.filter(employee=employee).order_by('-created_at')
        
        context['health_insurance'] = HealthInsurance.objects.filter(employee=employee, is_active=True).first()
        context['contact'] = Contact.objects.filter(employee=employee, is_active=True).first()
        context['address'] = Address.objects.filter(employee=employee, is_active=True).first()
        
        # Get vehicle through VehicleAssign relationship
        vehicle_assign = VehicleAssign.objects.filter(employee=employee, is_active=True, deleted=False).select_related('vehicle').first()
        context['vehicle'] = vehicle_assign.vehicle if vehicle_assign else None
        context['vehicle_assign'] = vehicle_assign
        context['vehicle_assignments'] = VehicleAssign.objects.filter(employee=employee, deleted=False).select_related('vehicle').order_by('-created_at')

        return context

# =============================================
# Uniform Report View
# =============================================
@login_required
def uniform_report(request):
    if not checkUserPermission(request, "can_view", "/backend/uniform/report/"):
        messages.error(request, "You do not have permission to view uniform reports.")
        return render(request, "403.html", status=403) 
    # Filter parameters
    employee_id = request.GET.get('employee', '')
    uniform_id = request.GET.get('uniform', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    # Employee-wise uniform issuance summary
    employee_filter = Q(is_active=True)
    if employee_id:
        employee_filter &= Q(employee_id=employee_id)
    if date_from:
        employee_filter &= Q(issued_date__gte=date_from)
    if date_to:
        employee_filter &= Q(issued_date__lte=date_to)
    if uniform_id:
        employee_filter &= Q(uniform_stock__uniform_id=uniform_id)

    employee_report = UniformIssuance.objects.filter(employee_filter).values(
        'employee__id',
        'employee__hr_file_no',
        'employee__first_name',
        'employee__last_name',
        'uniform_stock__uniform__name',
        'uniform_stock__uniform__uniform_type',
        'uniform_stock__size',
        'status'
    ).annotate(
        total_quantity=Sum('quantity')
    ).order_by('employee__first_name', 'uniform_stock__uniform__name')

    # Group by employee for better display
    employees_data = {}
    for record in employee_report:
        emp_id = record['employee__id']
        if emp_id not in employees_data:
            employees_data[emp_id] = {
                'employee_id': emp_id,
                'hr_file_no': record['employee__hr_file_no'],
                'full_name': f"{record['employee__first_name']} {record['employee__last_name']}",
                'uniforms': [],
                'total_issued': 0,
                'total_active': 0,
                'total_returned': 0,
                'total_lost': 0,
                'total_damaged': 0,
            }
        
        uniform_detail = {
            'name': record['uniform_stock__uniform__name'],
            'type': record['uniform_stock__uniform__uniform_type'],
            'size': record['uniform_stock__size'],
            'quantity': record['total_quantity'],
            'status': record['status'],
        }
        employees_data[emp_id]['uniforms'].append(uniform_detail)
        employees_data[emp_id]['total_issued'] += record['total_quantity']
        
        if record['status'] == 'ISSUED':
            employees_data[emp_id]['total_active'] += record['total_quantity']
        elif record['status'] == 'RETURNED':
            employees_data[emp_id]['total_returned'] += record['total_quantity']
        elif record['status'] == 'LOST':
            employees_data[emp_id]['total_lost'] += record['total_quantity']
        elif record['status'] == 'DAMAGED':
            employees_data[emp_id]['total_damaged'] += record['total_quantity']

    # Overall statistics
    total_uniforms_issued = UniformIssuance.objects.filter(
        is_active=True
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_uniforms_active = UniformIssuance.objects.filter(
        is_active=True, status='ISSUED'
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_uniforms_returned = UniformClearance.objects.filter(
        is_active=True, status='RETURNED'
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_uniforms_lost = UniformIssuance.objects.filter(
        is_active=True, status='LOST'
    ).aggregate(total=Sum('quantity'))['total'] or 0

    total_uniforms_damaged = UniformIssuance.objects.filter(
        is_active=True, status='DAMAGED'
    ).aggregate(total=Sum('quantity'))['total'] or 0

    # Stock summary by uniform type
    stock_summary = UniformStock.objects.filter(
        is_active=True
    ).values(
        'uniform__name',
        'uniform__uniform_type',
        'size'
    ).annotate(
        available_quantity=Sum('quantity')
    ).order_by('uniform__name', 'size')

    # Group stock by uniform
    stock_by_uniform = {}
    total_stock_quantity = 0
    for stock in stock_summary:
        uniform_name = stock['uniform__name']
        if uniform_name not in stock_by_uniform:
            stock_by_uniform[uniform_name] = {
                'name': uniform_name,
                'type': stock['uniform__uniform_type'],
                'sizes': [],
                'total_qty': 0
            }
        stock_by_uniform[uniform_name]['sizes'].append({
            'size': stock['size'],
            'quantity': stock['available_quantity']
        })
        stock_by_uniform[uniform_name]['total_qty'] += stock['available_quantity']
        total_stock_quantity += stock['available_quantity']

    # Recent transactions
    transaction_filter = Q()
    if date_from:
        transaction_filter &= Q(created_at__date__gte=date_from)
    if date_to:
        transaction_filter &= Q(created_at__date__lte=date_to)
    if uniform_id:
        transaction_filter &= Q(uniform_stock__uniform_id=uniform_id)
    if employee_id:
        transaction_filter &= Q(
            Q(issuance__employee_id=employee_id) | Q(clearance__employee_id=employee_id)
        )

    recent_transactions = UniformStockTransactionLog.objects.filter(
        transaction_filter
    ).select_related(
        'uniform_stock__uniform',
        'issuance__employee',
        'clearance__employee',
        'created_by'
    ).order_by('-created_at')[:50]

    # Uniform type distribution
    uniform_type_distribution = UniformIssuance.objects.filter(
        is_active=True, status='ISSUED'
    ).values(
        'uniform_stock__uniform__uniform_type'
    ).annotate(
        count=Sum('quantity')
    ).order_by('-count')

    context = {
        'employees_data': list(employees_data.values()),
        'total_employees': len(employees_data),
        'total_uniforms_issued': total_uniforms_issued,
        'total_uniforms_active': total_uniforms_active,
        'total_uniforms_returned': total_uniforms_returned,
        'total_uniforms_lost': total_uniforms_lost,
        'total_uniforms_damaged': total_uniforms_damaged,
        'stock_by_uniform': list(stock_by_uniform.values()),
        'total_stock_quantity': total_stock_quantity,
        'recent_transactions': recent_transactions,
        'uniform_type_distribution': uniform_type_distribution,
        'all_employees': Employee.objects.filter(is_active=True).order_by('first_name', 'last_name'),
        'all_uniforms': Uniform.objects.filter(is_active=True).order_by('name'),
        'filters': {
            'employee': employee_id,
            'uniform': uniform_id,
            'date_from': date_from,
            'date_to': date_to,
        }
    } 

    return render(request, "uniform/report.html", context)


@login_required
def uniform_log(request):
    if not checkUserPermission(request, "can_view", "/backend/uniform/log/"):
        messages.error(request, "You do not have permission to view uniform logs.")
        return render(request, "403.html", status=403) 
    
    # Filter parameters
    employee_id = request.GET.get('employee', '')
    uniform_id = request.GET.get('uniform', '')
    transaction_type = request.GET.get('transaction_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    # Build query filters
    filters = Q()
    
    if employee_id:
        filters &= Q(
            Q(issuance__employee_id=employee_id) | Q(clearance__employee_id=employee_id)
        )
    
    if uniform_id:
        filters &= Q(uniform_stock__uniform_id=uniform_id)
    
    if transaction_type:
        filters &= Q(transaction_type=transaction_type)
    
    if date_from:
        filters &= Q(created_at__date__gte=date_from)
    
    if date_to:
        filters &= Q(created_at__date__lte=date_to)

    # Get transaction logs
    transaction_logs = UniformStockTransactionLog.objects.filter(
        filters
    ).select_related(
        'uniform_stock__uniform',
        'issuance__employee',
        'clearance__employee',
        'created_by'
    ).order_by('-created_at')

    # Pagination
    page_num = request.GET.get('page', 1)
    paginator_list, paginator, last_page_number = paginate_data(request, page_num, transaction_logs)

    context = {
        'transaction_logs': paginator,
        'paginator': paginator,
        'paginator_list': paginator_list,
        'last_page_number': last_page_number,
        'page_num': page_num,
        'all_employees': Employee.objects.filter(is_active=True).order_by('first_name', 'last_name'),
        'all_uniforms': Uniform.objects.filter(is_active=True).order_by('name'),
        'transaction_types': UniformStockTransactionLog.TRANSACTION_TYPE_CHOICES,
        'filters': {
            'employee': employee_id,
            'uniform': uniform_id,
            'transaction_type': transaction_type,
            'date_from': date_from,
            'date_to': date_to,
        }
    }

    return render(request, "uniform/log.html", context)


# ============================================= 
# Uniform ListView 
# ============================================= 
class UniformListView(ListView):
    model = Uniform
    template_name = "uniform/list.html"
    paginate_by = None

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/uniform/"):
            messages.error(request, "You do not have permission to view uniforms.")
            return render(request, "403.html", status=403) 
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        filters = {
            'is_active': True, 
        }
        
        name = self.request.GET.get('name', '') 
        uniform_type = self.request.GET.get('uniform_type', '')
        
        if name:
            filters['id'] = name
        if uniform_type:
            filters['uniform_type'] = uniform_type
       
        return Uniform.objects.filter(**filters)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['uniforms'] = self.get_queryset()
        context['page_num'] = self.request.GET.get('page', 1)
        context['paginator_list'], context['paginator'], context['last_page_number'] = paginate_data(self.request, context['page_num'], context['uniforms'])

        # Add all uniforms for select2 dropdown
        context['all_uniforms'] = Uniform.objects.filter(is_active=True).order_by('name')

        get_param = self.request.GET.copy()
        if 'page' in get_param:
            get_param.pop('page')
        context['get_param'] = get_param.urlencode() 

        return context

# ============================================
# Uniform CreateView
# ============================================
class UniformCreateView(CreateView):
    model = Uniform
    template_name = "uniform/create.html"
    form_class = UniformForm
    success_url = reverse_lazy('uniform:list')

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_add", "/backend/uniform/"):
            messages.error(request, "You do not have permission to add uniforms.")
            return render(request, "403.html", status=403) 
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form) 
    

# ============================================
# Uniform UpdateView
# ============================================
class UniformUpdateView(UpdateView):
    model = Uniform
    template_name = "uniform/update.html"
    form_class = UniformForm
    success_url = reverse_lazy('uniform:list')

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_update", "/backend/uniform/"):
            messages.error(request, "You do not have permission to edit uniforms.")
            return render(request, "403.html", status=403) 
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form) 

# ============================================
# Uniform Delete View
# ============================================
@login_required
def uniform_delete(request, pk):
    if not checkUserPermission(request, "can_delete", "/backend/uniform/"):
        messages.error(request, "You do not have permission to delete uniforms.")
        return render(request, "403.html", status=403) 
    uniform = Uniform.objects.get(pk=pk)
    uniform.is_active = False
    uniform.save()
    return redirect('uniform:list') 


# ============================================
# Uniform Stock ListView
# ============================================
class UniformStockListView(ListView):
    model = UniformStock
    template_name = "uniform_stock/list.html"
    paginate_by = None

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/uniform-stock/"):
            messages.error(request, "You do not have permission to view uniform stocks.")
            return render(request, "403.html", status=403) 
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        filters = {
            'is_active': True, 
        }
        
        uniform = self.request.GET.get('uniform', '') 
        
        if uniform:
            filters['uniform_id'] = uniform
       
        return UniformStock.objects.filter(**filters)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['uniform_stocks'] = self.get_queryset()
        context['page_num'] = self.request.GET.get('page', 1)
        context['paginator_list'], context['paginator'], context['last_page_number'] = paginate_data(self.request, context['page_num'], context['uniform_stocks'])

        # Add all uniforms for select2 dropdown
        from backend.models import Uniform
        context['all_uniforms'] = Uniform.objects.filter(is_active=True).order_by('name')

        get_param = self.request.GET.copy()
        if 'page' in get_param:
            get_param.pop('page')
        context['get_param'] = get_param.urlencode() 

        return context

# ============================================
# Uniform Stock CreateView
# ============================================
class UniformStockCreateView(CreateView):
    model = UniformStock
    template_name = "uniform_stock/create.html"
    form_class = UniformStockForm
    success_url = reverse_lazy('uniform_stock:list')

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_add", "/backend/uniform-stock/"):
            messages.error(request, "You do not have permission to add uniform stocks.")
            return render(request, "403.html", status=403) 
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form) 

# ============================================
# Uniform Stock UpdateView
# ============================================
class UniformStockUpdateView(UpdateView):
    model = UniformStock
    template_name = "uniform_stock/update.html"
    form_class = UniformStockForm
    success_url = reverse_lazy('uniform_stock:list')

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_update", "/backend/uniform-stock/"):
            messages.error(request, "You do not have permission to edit uniform stocks.")
            return render(request, "403.html", status=403) 
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form) 
    
# ============================================
# Uniform Stock Delete View
# ============================================
@login_required
def uniform_stock_delete(request, pk):
    if not checkUserPermission(request, "can_delete", "/backend/uniform-stock/"):
        messages.error(request, "You do not have permission to delete uniform stocks.")
        return render(request, "403.html", status=403) 
    uniform_stock = UniformStock.objects.get(pk=pk)
    uniform_stock.is_active = False
    uniform_stock.save()
    return redirect('uniform_stock:list') 


# ============================================
# Uniform Issuance ListView
# ============================================
class UniformIssuanceListView(ListView):
    model = UniformIssuance
    template_name = "uniform_issuance/list.html"
    paginate_by = None

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/uniform-issuance/"):
            messages.error(request, "You do not have permission to view uniform issuances.")
            return render(request, "403.html", status=403) 
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        filters = {
            'is_active': True, 
        }
        
        employee = self.request.GET.get('employee', '').strip()
        status = self.request.GET.get('status', '').strip()
        quantity = self.request.GET.get('quantity', '').strip()
        issue_date_from = self.request.GET.get('issue_date_from', '').strip()
        issue_date_to = self.request.GET.get('issue_date_to', '').strip() 
        expected_return_date_from = self.request.GET.get('expected_return_date_from', '').strip()
        expected_return_date_to = self.request.GET.get('expected_return_date_to', '').strip() 
        
        if employee:
            filters['employee_id'] = employee

        if status:
            filters['status'] = status 
        
        if quantity:
            filters['quantity'] = quantity
        
        if issue_date_from:
            filters['issued_date__gte'] = issue_date_from
        if issue_date_to:
            filters['issued_date__lte'] = issue_date_to

        if expected_return_date_from:
            filters['expected_return_date__gte'] = expected_return_date_from
        if expected_return_date_to:
            filters['expected_return_date__lte'] = expected_return_date_to
        
        return UniformIssuance.objects.filter(**filters)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['uniform_issuances'] = self.get_queryset()
        context['page_num'] = self.request.GET.get('page', 1)
        context['paginator_list'], context['paginator'], context['last_page_number'] = paginate_data(self.request, context['page_num'], context['uniform_issuances'])

        # Add all employees for select2 dropdown
        context['all_employees'] = Employee.objects.filter(is_active=True).order_by('first_name', 'last_name')

        get_param = self.request.GET.copy()
        if 'page' in get_param:
            get_param.pop('page')
        context['get_param'] = get_param.urlencode() 

        return context

@method_decorator(login_required, name='dispatch')
class UniformIssuanceDetailView(DetailView):
    model = UniformIssuance
    template_name = "uniform_issuance/detail.html"
    context_object_name = 'uniform_issuance'

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/uniform-issuance/"):
            messages.error(request, "You do not have permission to view uniform issuance details.")
            return render(request, "403.html", status=403) 
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        uniform_issuance = self.object
        
        employee = uniform_issuance.employee
        
        employee_issuances = UniformIssuance.objects.filter(
            employee=employee, 
            is_active=True
        ).select_related('uniform_stock__uniform', 'created_by').order_by('-issued_date')
        
        employee_clearances = UniformClearance.objects.filter(
            employee=employee,
            is_active=True
        ).select_related('uniform_stock__uniform', 'created_by').order_by('-clearance_date')
        
        issuance_transaction_logs = UniformStockTransactionLog.objects.filter(
            issuance=uniform_issuance
        ).select_related('uniform_stock__uniform', 'created_by').order_by('-created_at')
        
        stock_transaction_logs = UniformStockTransactionLog.objects.filter(
            uniform_stock=uniform_issuance.uniform_stock
        ).select_related('issuance__employee', 'clearance__employee', 'created_by').order_by('-created_at')[:20]
        
        uniform_stock = uniform_issuance.uniform_stock
        
        # Calculate employee uniform statistics
        total_issued = UniformIssuance.objects.filter(employee=employee, is_active=True).aggregate(total=Sum('quantity'))['total'] or 0
        
        total_active = UniformIssuance.objects.filter(employee=employee, is_active=True, status='ISSUED').aggregate(total=Sum('quantity'))['total'] or 0
        
        total_returned = UniformClearance.objects.filter(employee=employee, is_active=True, status='RETURNED').aggregate(total=Sum('quantity'))['total'] or 0
        
        total_lost = UniformIssuance.objects.filter(employee=employee, is_active=True, status='LOST').aggregate(total=Sum('quantity'))['total'] or 0
        
        total_damaged = UniformIssuance.objects.filter(employee=employee, is_active=True, status='DAMAGED').aggregate(total=Sum('quantity'))['total'] or 0
        
        # Get uniform type breakdown for this employee
        uniform_by_type = employee_issuances.values('uniform_stock__uniform__name', 'uniform_stock__uniform__uniform_type', 'status').annotate(total_quantity=Sum('quantity')).order_by('uniform_stock__uniform__name')
        
        # Check if there are any issues/alerts
        issues = []
        
        # Check if expected return date has passed
        if uniform_issuance.expected_return_date and uniform_issuance.status == 'ISSUED':
            from datetime import date
            if uniform_issuance.expected_return_date < date.today():
                days_overdue = (date.today() - uniform_issuance.expected_return_date).days
                issues.append({
                    'type': 'overdue',
                    'severity': 'high',
                    'message': f'Uniform is overdue by {days_overdue} days'
                })
        
        # Check if uniform is lost or damaged
        if uniform_issuance.status == 'LOST':
            issues.append({
                'type': 'lost',
                'severity': 'critical',
                'message': 'Uniform has been marked as LOST'
            })
        elif uniform_issuance.status == 'DAMAGED':
            issues.append({
                'type': 'damaged',
                'severity': 'high',
                'message': 'Uniform has been marked as DAMAGED'
            })
        
        # Check stock availability
        if uniform_stock.quantity < 5:
            issues.append({
                'type': 'low_stock',
                'severity': 'warning',
                'message': f'Low stock alert: Only {uniform_stock.quantity} units remaining'
            })
        
        context.update({
            'employee': employee,
            'employee_issuances': employee_issuances,
            'employee_clearances': employee_clearances,
            'issuance_transaction_logs': issuance_transaction_logs,
            'stock_transaction_logs': stock_transaction_logs,
            'uniform_stock': uniform_stock,
            'employee_uniform_stats': {
                'total_issued': total_issued,
                'total_active': total_active,
                'total_returned': total_returned,
                'total_lost': total_lost,
                'total_damaged': total_damaged,
            },
            'uniform_by_type': uniform_by_type,
            'issues': issues,
        })
        
        return context 
    


# ============================================
# Uniform Issuance CreateView
# ============================================
class UniformIssuanceCreateView(CreateView):
    model = UniformIssuance
    template_name = "uniform_issuance/create.html"
    form_class = UniformIssuanceForm
    success_url = reverse_lazy('uniform_issuance:list')

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_add", "/backend/uniform-issuance/"):
            messages.error(request, "You do not have permission to add uniform issuances.")
            return render(request, "403.html", status=403) 
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()

        employee_id = self.request.GET.get('employee')
        if employee_id:
            try:
                employee = Employee.objects.get(pk=employee_id, is_active=True)
                initial['employee'] = employee
            except Employee.DoesNotExist:
                pass

        return initial

    def form_valid(self, form):
        
        try:
            form.instance.created_by = self.request.user
            response = super().form_valid(form)
            messages.success(self.request, "Uniform issued successfully and stock updated!")
            return response
        except ValidationError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)

# ============================================
# Uniform Issuance UpdateView
# ============================================
class UniformIssuanceUpdateView(UpdateView):
    model = UniformIssuance
    template_name = "uniform_issuance/update.html"
    form_class = UniformIssuanceForm
    success_url = reverse_lazy('uniform_issuance:list')

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_update", "/backend/uniform-issuance/"):
            messages.error(request, "You do not have permission to edit uniform issuances.")
            return render(request, "403.html", status=403) 
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Uniform issuance updated successfully!")
        return super().form_valid(form)

# ============================================
# Uniform Issuance Delete View
# ============================================
@login_required
def uniform_issuance_delete(request, pk):
    if not checkUserPermission(request, "can_delete", "/backend/uniform-issuance/"):
        messages.error(request, "You do not have permission to delete uniform issuances.")
        return render(request, "403.html", status=403) 
    uniform_issuance = UniformIssuance.objects.get(pk=pk)
    uniform_issuance.is_active = False
    uniform_issuance.save()
    return redirect('uniform_issuance:list') 


# ============================================
# Uniform Clearance ListView
# ============================================
class UniformClearanceListView(ListView):
    model = UniformClearance
    template_name = "uniform_clearance/list.html"
    paginate_by = None

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/uniform-clearance/"):
            messages.error(request, "You do not have permission to view uniform clearances.")
            return render(request, "403.html", status=403) 
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        filters = {
            'is_active': True, 
        }
        
        employee = self.request.GET.get('employee', '') 
        
        if employee:
            filters['employee_id'] = employee
       
        return UniformClearance.objects.filter(**filters)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['uniform_clearances'] = self.get_queryset()
        context['page_num'] = self.request.GET.get('page', 1)
        context['paginator_list'], context['paginator'], context['last_page_number'] = paginate_data(self.request, context['page_num'], context['uniform_clearances'])

        # Add all employees for select2 dropdown
        context['all_employees'] = Employee.objects.filter(is_active=True).order_by('first_name', 'last_name')

        get_param = self.request.GET.copy()
        if 'page' in get_param:
            get_param.pop('page')
        context['get_param'] = get_param.urlencode() 

        return context

# ============================================
# Uniform Clearance CreateView
# ============================================
class UniformClearanceCreateView(CreateView):
    model = UniformClearance
    template_name = "uniform_clearance/create.html"
    form_class = UniformClearanceForm
    success_url = reverse_lazy('uniform_clearance:list')

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_add", "/backend/uniform-clearance/"):
            messages.error(request, "You do not have permission to add uniform clearances.")
            return render(request, "403.html", status=403) 
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        if form.instance.status == 'RETURNED':
            messages.success(self.request, "Uniform cleared successfully and stock updated!")
        else:
            messages.success(self.request, f"Uniform cleared successfully with status: {form.instance.get_status_display()}!")
        return response

# ============================================
# Uniform Clearance UpdateView
# ============================================
class UniformClearanceUpdateView(UpdateView):
    model = UniformClearance
    template_name = "uniform_clearance/update.html"
    form_class = UniformClearanceForm
    success_url = reverse_lazy('uniform_clearance:list')

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_update", "/backend/uniform-clearance/"):
            messages.error(request, "You do not have permission to edit uniform clearances.")
            return render(request, "403.html", status=403) 
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Uniform clearance updated successfully!")
        return super().form_valid(form)

# ============================================
# Uniform Clearance Delete View
# ============================================
@login_required
def uniform_clearance_delete(request, pk):
    if not checkUserPermission(request, "can_delete", "/backend/uniform-clearance/"):
        messages.error(request, "You do not have permission to delete uniform clearances.")
        return render(request, "403.html", status=403) 
    
    uniform_clearance = UniformClearance.objects.get(pk=pk)
    uniform_clearance.is_active = False
    uniform_clearance.save()

    return redirect('uniform_clearance:list') 


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
        
        plate_no = self.request.GET.get('plate_no', '').strip()
        vehicle_type = self.request.GET.get('vehicle_type', '').strip()
        chassee_no = self.request.GET.get('chassee_no', '').strip()
        ownership = self.request.GET.get('ownership', '').strip()
        engine_no = self.request.GET.get('engine_no', '').strip()
        
        if plate_no:
            filters['plate_no'] = plate_no
        if vehicle_type:
            filters['vehicle_type'] = vehicle_type
        if chassee_no:
            filters['chassee_no__icontains'] = chassee_no
        if engine_no:
            filters['engine_no__icontains'] = engine_no 

        if ownership:
            filters['ownership'] = ownership
       
        return Vehicle.objects.filter(**filters)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vehicle_infos = self.get_queryset()
        
        # Get current vehicle assignments
        vehicle_assignments = {}
        for assignment in VehicleAssign.objects.filter(is_active=True, deleted=False).select_related('employee', 'vehicle'):
            vehicle_assignments[assignment.vehicle_id] = assignment.employee
        
        # Add current_employee to each vehicle
        for vehicle in vehicle_infos:
            vehicle.current_employee = vehicle_assignments.get(vehicle.id)
        
        context['vehicle_infos'] = vehicle_infos
        context['page_num'] = self.request.GET.get('page', 1)
        context['paginator_list'], context['paginator'], context['last_page_number'] = paginate_data(self.request, context['page_num'], context['vehicle_infos'])

        # Add all vehicles for select2 dropdown with current assignment
        all_vehicles = Vehicle.objects.filter(is_active=True).order_by('plate_no')
        for vehicle in all_vehicles:
            vehicle.current_employee = vehicle_assignments.get(vehicle.id)
        context['all_vehicles'] = all_vehicles

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


@method_decorator(login_required, name='dispatch')
class VehicleAssignListView(ListView):
    model = VehicleAssign
    template_name = "vehicle_assign/list.html"
    paginate_by = None

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/vehicle-assign/"):
            messages.error(request, "You do not have permission to view vehicle assignments.")
            return render(request, "403.html") 
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = VehicleAssign.objects.filter(is_active=True).select_related('vehicle', 'employee').order_by('-created_at')
        
        employee = self.request.GET.get('employee', '')
        vehicle = self.request.GET.get('vehicle', '')
        
        if employee:
            queryset = queryset.filter(employee_id=employee)

        if vehicle:
            queryset = queryset.filter(vehicle_id=vehicle)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['vehicle_assignments'] = self.get_queryset()
        context['page_num'] = self.request.GET.get('page', 1)
        context['paginator_list'], context['paginator'], context['last_page_number'] = paginate_data(self.request, context['page_num'], context['vehicle_assignments'])
        
        # Add filter options
        context['all_vehicles'] = Vehicle.objects.filter(is_active=True).order_by('plate_no')
        context['all_employees'] = Employee.objects.filter(is_active=True).order_by('first_name', 'last_name')
        
        get_param = self.request.GET.copy()

        if 'page' in get_param:
            get_param.pop('page')

        context['get_param'] = get_param.urlencode() 

        return context  

@method_decorator(login_required, name='dispatch')
class VehicleAssignCreateView(CreateView):
    model = VehicleAssign
    template_name = "vehicle_assign/create.html"
    form_class = VehicleAssignForm
    success_url = reverse_lazy('vehicle_assign:list')

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_add", "/backend/vehicle-assign/"):
            messages.error(request, "You do not have permission to add vehicle assignments.")
            return render(request, "403.html") 
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        # Pre-fill vehicle if passed in query params
        vehicle_id = self.request.GET.get('vehicle')
        if vehicle_id:
            try:
                vehicle = Vehicle.objects.get(pk=vehicle_id, is_active=True)
                initial['vehicle'] = vehicle
            except Vehicle.DoesNotExist:
                pass
        
        # Pre-fill employee if passed in query params
        employee_id = self.request.GET.get('employee')
        if employee_id:
            try:
                employee = Employee.objects.get(pk=employee_id, is_active=True)
                initial['employee'] = employee
            except Employee.DoesNotExist:
                pass
        
        return initial

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

@method_decorator(login_required, name='dispatch')
class VehicleAssignUpdateView(UpdateView):
    model = VehicleAssign
    template_name = "vehicle_assign/update.html"
    form_class = VehicleAssignForm
    success_url = reverse_lazy('vehicle_assign:list')

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_update", "/backend/vehicle-assign/"):
            messages.error(request, "You do not have permission to edit vehicle assignments.")
            return render(request, "403.html") 
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form) 


@login_required
def vehicle_assign_delete(request, pk):
    if not checkUserPermission(request, "can_delete", "/backend/vehicle-assign/"):
        messages.error(request, "You do not have permission to delete vehicle assignments.")
        return render(request, "403.html") 
    vehicle_assign = VehicleAssign.objects.get(pk=pk)
    vehicle_assign.is_active = False
    vehicle_assign.deleted = True
    vehicle_assign.save()
    return redirect('vehicle_assign:list') 

@login_required
def vehicle_management(request):
    if not checkUserPermission(request, "can_view", "/backend/vehicle-management/"):
        messages.error(request, "You do not have permission to view vehicle management.")
        return render(request, "403.html") 

    # Get counts for dashboard
    total_vehicles = Vehicle.objects.filter(is_active=True).count()
    total_handovers = VehicleHandover.objects.count()
    total_violations = TrafficViolation.objects.count()
    unpaid_violations = TrafficViolation.objects.filter(is_paid=False).count()
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
            queryset = queryset.filter(vehicle__plate_no=plate_no)
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

# ================================================
# VIOLATION TYPE VIEWS
# ================================================ 
@method_decorator(login_required, name='dispatch') 
class ViolationTypeListView(ListView):
    model = ViolationType
    template_name = "violation_type/list.html"
    paginate_by = None

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/violation-type/"):
            messages.error(request, "You do not have permission to view violation types.")
            return render(request, "403.html", status=403)
        return super().dispatch(request, *args, **kwargs)


    def get_queryset(self):

        filters = {
            'is_active' : True,
        }

        name = self.request.GET.get('name', '')
        
        if name:
            filters['name__icontains'] = name
        return ViolationType.objects.filter(**filters).order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['violation_types'] = self.get_queryset()
        context['all_violation_types'] = ViolationType.objects.filter(is_active=True).order_by('name')
        context['page_num'] = self.request.GET.get('page', 1)
        page_numbers, context['paginator_list'], context['last_page_number'] = paginate_data(
            self.request, context['page_num'], context['violation_types']
        )
        context['paginator'] = context['paginator_list']
        get_param = self.request.GET.copy()
        if 'page' in get_param:
            get_param.pop('page')
        context['get_param'] = get_param.urlencode()
        
        return context 


@method_decorator(login_required, name='dispatch')
class ViolationTypeCreateView(CreateView):
    model = ViolationType
    template_name = "violation_type/create.html"
    form_class = ViolationTypeForm
    success_url = reverse_lazy('violation_type:list')

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_add", "/backend/violation-type/"):
            messages.error(request, "You do not have permission to add violation types.")
            return render(request, "403.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

@method_decorator(login_required, name='dispatch')
class ViolationTypeUpdateView(UpdateView):
    model = ViolationType
    template_name = "violation_type/update.html"
    form_class = ViolationTypeForm
    success_url = reverse_lazy('violation_type:list')

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_update", "/backend/violation-type/"):
            messages.error(request, "You do not have permission to edit violation types.")
            return render(request, "403.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form) 

@login_required
def violation_type_delete(request, pk):
    if not checkUserPermission(request, "can_delete", "/backend/violation-type/"):
        messages.error(request, "You do not have permission to delete violation types.")
        return render(request, "403.html", status=403)
    violation_type = ViolationType.objects.get(pk=pk)
    violation_type.is_active = False
    violation_type.deleted = True
    violation_type.save()
    messages.success(request, "Violation type deleted successfully.")
    return redirect('violation_type:list')

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
        violation_type = self.request.GET.get('violation_type', '')
        is_paid = self.request.GET.get('is_paid', '')
        
        if plate_no:
            queryset = queryset.filter(vehicle__plate_no=plate_no)
        if violation_type:
            queryset = queryset.filter(violation_type_id=violation_type)
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
        context['all_violation_types'] = ViolationType.objects.filter(is_active=True).order_by('name')
        
        return context


@login_required
def traffic_violation_create(request):
    if not checkUserPermission(request, "can_add", "/backend/traffic-violation/"):
        messages.error(request, "You do not have permission to add traffic violations.")
        return render(request, "403.html", status=403)

    if request.method == 'POST':
        form = TrafficViolationForm(request.POST)
        if form.is_valid():
            violation = form.save(commit=False)
            violation.created_by = request.user
            violation.save()
            messages.success(request, "Traffic violation created successfully.")
            return redirect('traffic_violation:list')
    else:
        form = TrafficViolationForm()

    context = {
        'form': form,
        'vehicles': Vehicle.objects.filter(is_active=True, deleted=False),
        'violation_types': ViolationType.objects.filter(is_active=True),
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
            violation = form.save(commit=False)
            violation.updated_by = request.user
            violation.save()
            messages.success(request, "Traffic violation updated successfully.")
            return redirect('traffic_violation:list')
    else:
        form = TrafficViolationForm(instance=violation)

    context = {
        'form': form,
        'violation': violation,
        'vehicles': Vehicle.objects.filter(is_active=True, deleted=False),
        'violation_types': ViolationType.objects.filter(is_active=True),
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


@method_decorator(login_required, name='dispatch')
class TrafficViolationPenaltyListView(ListView):
    model = TrafficViolationPenalty
    template_name = "traffic_violation_penalty/list.html"
    paginate_by = None

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/traffic-violation-penalty/"):
            messages.error(request, "You do not have permission to view traffic violation penalties.")
            return render(request, "403.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = TrafficViolationPenalty.objects.all().order_by('-created_at')
        
        plate_no = self.request.GET.get('plate_no', '')
        violation_type = self.request.GET.get('violation_type', '')
        
        if plate_no:
            queryset = queryset.filter(traffic_violation__vehicle__plate_no=plate_no)
        if violation_type:
            queryset = queryset.filter(traffic_violation__violation_type_id=violation_type)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['penalties'] = self.get_queryset()
        context['page_num'] = self.request.GET.get('page', 1)
        context['paginator_list'], context['paginator'], context['last_page_number'] = paginate_data(
            self.request, context['page_num'], context['penalties']
        )
        get_param = self.request.GET.copy()
        if 'page' in get_param:
            get_param.pop('page')
        context['get_param'] = get_param.urlencode()
        
        # Add data for select2 dropdowns
        context['all_vehicles'] = Vehicle.objects.filter(is_active=True, deleted=False).order_by('plate_no')
        context['all_violation_types'] = ViolationType.objects.filter(is_active=True).order_by('name')
        
        return context 
    
@method_decorator(login_required, name='dispatch')
class TrafficViolationPenaltyCreateView(CreateView):
    model = TrafficViolationPenalty
    template_name = "traffic_violation_penalty/create.html"
    form_class = TrafficViolationPenaltyForm
    success_url = reverse_lazy('traffic_violation_penalty:list')

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_add", "/backend/traffic-violation-penalty/"):
            messages.error(request, "You do not have permission to add traffic violation penalties.")
            return render(request, "403.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form) 
    

@method_decorator(login_required, name='dispatch')
class TrafficViolationPenaltyUpdateView(UpdateView):
    model = TrafficViolationPenalty
    template_name = "traffic_violation_penalty/update.html"
    form_class = TrafficViolationPenaltyForm
    success_url = reverse_lazy('traffic_violation_penalty:list')

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_update", "/backend/traffic-violation-penalty/"):
            messages.error(request, "You do not have permission to edit traffic violation penalties.")
            return render(request, "403.html", status=403)
        return super().dispatch(request, *args, **kwargs) 
    
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form) 
    

@login_required
def traffic_violation_penalty_delete(request, pk):
    if not checkUserPermission(request, "can_delete", "/backend/traffic-violation-penalty/"):
        messages.error(request, "You do not have permission to delete traffic violation penalties.")
        return render(request, "403.html", status=403)

    penalty = get_object_or_404(TrafficViolationPenalty, pk=pk)
    penalty.delete()
    messages.success(request, "Traffic violation penalty deleted successfully.")
    return redirect('traffic_violation_penalty:list')


@method_decorator(login_required, name='dispatch')
class TrafficViolationPenaltyDetailView(DetailView):
    model = TrafficViolationPenalty
    template_name = "traffic_violation_penalty/detail.html"
    context_object_name = 'penalty'

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/traffic-violation-penalty/"):
            messages.error(request, "You do not have permission to view traffic violation penalty details.")
            return render(request, "403.html", status=403) 
        return super().dispatch(request, *args, **kwargs)


@method_decorator(login_required, name='dispatch')
class InsuranceClaimListView(ListView):
    model = InsuranceClaim
    template_name = "insurance_claim/list.html"
    paginate_by = None

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/insurance-claim/"):
            messages.error(request, "You do not have permission to view insurance claims.")
            return render(request, "403.html", status=403) 
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = InsuranceClaim.objects.all().order_by('-claim_date')
        
        plate_no = self.request.GET.get('plate_no', '')
        claim_status = self.request.GET.get('claim_status', '')
        
        if plate_no:
            queryset = queryset.filter(accident__vehicle__plate_no=plate_no)
        if claim_status:
            queryset = queryset.filter(claim_status=claim_status)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['claims'] = self.get_queryset()
        context['page_num'] = self.request.GET.get('page', 1)
        context['paginator_list'], context['paginator'], context['last_page_number'] = paginate_data(
            self.request, context['page_num'], context['claims']
        )
        get_param = self.request.GET.copy()
        if 'page' in get_param:
            get_param.pop('page')
        context['get_param'] = get_param.urlencode()
        
        # Add data for select2 dropdowns
        context['all_vehicles'] = Vehicle.objects.filter(is_active=True, deleted=False).order_by('plate_no')
        
        return context 
    

@method_decorator(login_required, name='dispatch')
class InsuranceClaimDetailView(DetailView):
    model = InsuranceClaim
    template_name = "insurance_claim/detail.html"
    context_object_name = 'claim'

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/insurance-claim/"):
            messages.error(request, "You do not have permission to view insurance claim details.")
            return render(request, "403.html", status=403) 
        return super().dispatch(request, *args, **kwargs)


@method_decorator(login_required, name='dispatch')
class InsuranceClaimCreateView(CreateView):
    model = InsuranceClaim
    template_name = "insurance_claim/create.html"
    form_class = InsuranceClaimForm
    success_url = reverse_lazy('insurance_claim:list')

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_add", "/backend/insurance-claim/"):
            messages.error(request, "You do not have permission to add insurance claims.")
            return render(request, "403.html", status=403) 
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)
    

@method_decorator(login_required, name='dispatch')
class InsuranceClaimUpdateView(UpdateView):
    model = InsuranceClaim
    template_name = "insurance_claim/update.html"
    form_class = InsuranceClaimForm
    success_url = reverse_lazy('insurance_claim:list')

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_update", "/backend/insurance-claim/"):
            messages.error(request, "You do not have permission to edit insurance claims.")
            return render(request, "403.html", status=403) 
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


@login_required
def insurance_claim_delete(request, pk):
    if not checkUserPermission(request, "can_delete", "/backend/insurance-claim/"):
        messages.error(request, "You do not have permission to delete insurance claims.")
        return render(request, "403.html", status=403) 
    
    claim = get_object_or_404(InsuranceClaim, pk=pk)
    claim.delete()
    messages.success(request, "Insurance claim deleted successfully.")
    return redirect('insurance_claim:list') 


@method_decorator(login_required, name='dispatch')
class VehicleMaintananceTypeListView(ListView):
    model = VehicleMaintananceType
    template_name = "vehicle_maintanance_type/list.html"
    paginate_by = None

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_view", "/backend/vehicle-maintenance-type/"):
            messages.error(request, "You do not have permission to view vehicle maintenance types.")
            return render(request, "403.html", status=403) 
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        filters = {
            'is_active' : True,
        }

        name = self.request.GET.get('name', '')
        
        if name:
            filters['name__icontains'] = name
        return VehicleMaintananceType.objects.filter(**filters).order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['maintenance_types'] = self.get_queryset()
        context['all_maintenance_types'] = VehicleMaintananceType.objects.filter(is_active=True).order_by('name')
        context['page_num'] = self.request.GET.get('page', 1)
        page_numbers, context['paginator_list'], context['last_page_number'] = paginate_data(
            self.request, context['page_num'], context['maintenance_types']
        )
        context['paginator'] = context['paginator_list']
        get_param = self.request.GET.copy()
        if 'page' in get_param:
            get_param.pop('page')
        context['get_param'] = get_param.urlencode()
        
        return context 

@method_decorator(login_required, name='dispatch')
class VehicleMaintananceTypeCreateView(CreateView):
    model = VehicleMaintananceType
    template_name = "vehicle_maintanance_type/create.html"
    form_class = VehicleMaintananceTypeForm
    success_url = reverse_lazy('vehicle_maintanance_type:list')

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_add", "/backend/vehicle-maintenance-type/"):
            messages.error(request, "You do not have permission to add vehicle maintenance types.")
            return render(request, "403.html", status=403) 
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form) 


@method_decorator(login_required, name='dispatch')
class VehicleMaintananceTypeUpdateView(UpdateView):
    model = VehicleMaintananceType
    template_name = "vehicle_maintanance_type/update.html"
    form_class = VehicleMaintananceTypeForm
    success_url = reverse_lazy('vehicle_maintanance_type:list')

    def dispatch(self, request, *args, **kwargs):
        if not checkUserPermission(request, "can_update", "/backend/vehicle-maintenance-type/"):
            messages.error(request, "You do not have permission to edit vehicle maintenance types.")
            return render(request, "403.html", status=403) 
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


@login_required
def vehicle_maintanance_type_delete(request, pk):
    if not checkUserPermission(request, "can_delete", "/backend/vehicle-maintenance-type/"):
        messages.error(request, "You do not have permission to delete vehicle maintenance types.")
        return render(request, "403.html", status=403) 
    maintenance_type = VehicleMaintananceType.objects.get(pk=pk)
    maintenance_type.is_active = False
    maintenance_type.deleted = True
    maintenance_type.save()
    messages.success(request, "Vehicle maintenance type deleted successfully.")
    return redirect('vehicle_maintanance_type:list') 


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
            queryset = queryset.filter(vehicle__plate_no__icontains=plate_no)
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
            maintenance = form.save(commit=False)
            maintenance.created_by = request.user
            maintenance.save()
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
            maintenance = form.save(commit=False)
            maintenance.updated_by = request.user
            maintenance.save()
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
        insurance_claimed = self.request.GET.get('insurance_claimed', '')
        
        if plate_no:
            queryset = queryset.filter(vehicle__plate_no=plate_no)
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
        all_vehicles = Vehicle.objects.filter(is_active=True, deleted=False).order_by('plate_no')
        context['all_employees'] = Employee.objects.filter(is_active=True).order_by('first_name', 'last_name')
        
        # Get current vehicle assignments
        vehicle_assignments = {}
        for assignment in VehicleAssign.objects.filter(is_active=True, deleted=False).select_related('employee', 'vehicle'):
            vehicle_assignments[assignment.vehicle_id] = assignment.employee
        
        # Add current_employee to each vehicle
        for vehicle in all_vehicles:
            vehicle.current_employee = vehicle_assignments.get(vehicle.id)
        context['all_vehicles'] = all_vehicles
        
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
            accident = form.save(commit=False)
            accident.created_by = request.user
            accident.save()
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
            accident = form.save(commit=False)
            accident.updated_by = request.user
            accident.save()
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

# ============================================= 
# Vehicle Purchase 
# ============================================= 
@login_required
def vehicle_purchase_list(request):
    if not checkUserPermission(request, "can_view", "/backend/vehicle-purchase/"):
        messages.error(request, "You do not have permission to view vehicle purchases.")
        return render(request, "403.html", status=403)

    filters = {
        'is_active': True,
        'deleted': False,
    }

    plate_no = request.GET.get('plate_no', '')
    employee_name = request.GET.get('employee_name', '')
    
    if plate_no:
        filters['vehicle__plate_no__icontains'] = plate_no
    if employee_name:
        filters['employee__first_name__icontains'] = employee_name

    purchases_qs = VehiclePurchase.objects.filter(**filters).select_related('vehicle', 'employee').order_by('-purchase_date')

    page_num = request.GET.get('page', 1)
    paginator_list, page_obj, last_page_number = paginate_data(request, page_num, purchases_qs)
    paginator = page_obj.paginator

    get_param = request.GET.copy()
    if 'page' in get_param:
        get_param.pop('page')
    
    context = {
        'purchases': page_obj,
        'page_obj': page_obj,
        'paginator_list': paginator_list,
        'page_num': page_obj.number,
        'paginator': paginator,
        'last_page_number': last_page_number,
        'get_param': get_param.urlencode(),
    }
    return render(request, 'vehicle_purchase/list.html', context)


@login_required
def vehicle_purchase_create(request):
    if not checkUserPermission(request, "can_add", "/backend/vehicle-purchase/"):
        messages.error(request, "You do not have permission to add vehicle purchases.")
        return render(request, "403.html", status=403)

    if request.method == 'POST':
        form = VehiclePurchaseForm(request.POST)
        if form.is_valid():
            try:
                vehicle_defaults = {
                    'vehicle_type': form.cleaned_data['vehicle_type'],
                    'ownership': form.cleaned_data['ownership'],
                    'chassee_no': form.cleaned_data['chassee_no'],
                    'engine_no': form.cleaned_data['engine_no'],
                    'istemara_expiry_date': form.cleaned_data['istemara_expiry_date'],
                    'insurance_name': form.cleaned_data['insurance_name'],
                    'insurance_expiry_date': form.cleaned_data['insurance_expiry_date'],
                    'is_active': True,
                    'deleted': False,
                }

                # Update existing vehicle (matched by plate) or create a new one
                vehicle, created = Vehicle.objects.get_or_create(
                    plate_no=form.cleaned_data['plate_no'],
                    defaults={
                        **vehicle_defaults,
                        'created_by': request.user,
                    }
                )

                if not created:
                    for field, value in vehicle_defaults.items():
                        setattr(vehicle, field, value)
                    vehicle.updated_by = request.user
                    vehicle.is_active = True
                    vehicle.deleted = False
                    vehicle.save(update_fields=[
                        'vehicle_type', 'ownership', 'chassee_no', 'engine_no', 'istemara_expiry_date',
                        'insurance_name', 'insurance_expiry_date', 'updated_by', 'is_active', 'deleted'
                    ])

                purchase = VehiclePurchase(
                    vehicle=vehicle,
                    purchase_date=form.cleaned_data['purchase_date'],
                    total_amount=form.cleaned_data['total_amount'],
                    down_payment=form.cleaned_data['down_payment'],
                    installment_amount=form.cleaned_data['installment_amount'],
                    start_date=form.cleaned_data['start_date'],
                    payment_period=form.cleaned_data['payment_period'],
                    payment_method=form.cleaned_data['payment_method'],
                    created_by=request.user
                )
                purchase.save()
                purchase.generate_installment_schedule(request.user)

                messages.success(request, "Vehicle purchase created successfully with installment schedule.")
                return redirect('vehicle_purchase:list')
            except Exception as exc:
                messages.error(request, f"Unable to create vehicle purchase: {exc}")
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = VehiclePurchaseForm()

    context = {
        'form': form,
    }
    return render(request, 'vehicle_purchase/create.html', context)


@login_required
def vehicle_purchase_detail(request, pk):
    if not checkUserPermission(request, "can_view", "/backend/vehicle-purchase/"):
        messages.error(request, "You do not have permission to view vehicle purchase details.")
        return render(request, "403.html", status=403)

    purchase = get_object_or_404(VehiclePurchase, pk=pk)
    installments_qs = purchase.installments.all().order_by('installment_no')
    
    # Calculate payment statistics
    total_paid = sum(inst.amount for inst in installments_qs if inst.is_paid)
    total_pending = sum(inst.amount for inst in installments_qs if not inst.is_paid)
    paid_count = installments_qs.filter(is_paid=True).count()
    pending_count = installments_qs.filter(is_paid=False).count()
    
    context = {
        'purchase': purchase,
        'installments': installments_qs,
        'total_paid': total_paid,
        'total_pending': total_pending,
        'paid_count': paid_count,
        'pending_count': pending_count,
    }
    return render(request, 'vehicle_purchase/detail.html', context)


@login_required
def vehicle_purchase_delete(request, pk):
    if not checkUserPermission(request, "can_delete", "/backend/vehicle-purchase/"):
        messages.error(request, "You do not have permission to delete vehicle purchases.")
        return render(request, "403.html", status=403)

    purchase = get_object_or_404(VehiclePurchase, pk=pk)
    purchase.is_active = False
    purchase.deleted = True
    purchase.save()
    messages.success(request, "Vehicle purchase deleted successfully.")
    return redirect('vehicle_purchase:list') 


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
        queryset = VehicleInstallment.objects.select_related('purchase', 'purchase__vehicle', 'purchase__employee').all().order_by('-due_date')
        
        plate_no = self.request.GET.get('plate_no', '')
        is_paid = self.request.GET.get('is_paid', '')
        purchase_id = self.request.GET.get('purchase_id', '')
        
        if plate_no:
            queryset = queryset.filter(purchase__vehicle__plate_no__icontains=plate_no)
        if is_paid:
            queryset = queryset.filter(is_paid=(is_paid == 'true'))
        if purchase_id:
            queryset = queryset.filter(purchase_id=purchase_id)
        
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
        context['all_purchases'] = VehiclePurchase.objects.filter(is_active=True, deleted=False).select_related('vehicle', 'employee').order_by('-purchase_date')
        
        return context


@login_required
def installment_pay(request, pk):
    """View to pay an installment - user only needs to select payment method"""
    if not checkUserPermission(request, "can_update", "/backend/vehicle-installment/"):
        messages.error(request, "You do not have permission to pay vehicle installments.")
        return render(request, "403.html", status=403)

    installment = get_object_or_404(VehicleInstallment, pk=pk)
    
    if installment.is_paid:
        messages.warning(request, "This installment has already been paid.")
        return redirect('vehicle_installment:list')
    
    if request.method == 'POST':
        form = InstallmentPaymentForm(request.POST, instance=installment)
        if form.is_valid():
            installment = form.save(commit=False)
            installment.is_paid = True
            installment.paid_date = timezone.now().date()
            installment.payment_status = 'PAID'
            installment.updated_by = request.user
            installment.save()
            messages.success(request, f"Installment #{installment.installment_no} paid successfully.")
            return redirect('vehicle_purchase:installments', pk=installment.purchase.pk)
    else:
        form = InstallmentPaymentForm(instance=installment)

    context = {
        'form': form,
        'installment': installment,
    }
    return render(request, 'vehicle_installment/pay.html', context)


@login_required
def purchase_installments_list(request, pk):
    """View to show all installments for a specific purchase"""
    if not checkUserPermission(request, "can_view", "/backend/vehicle-purchase/"):
        messages.error(request, "You do not have permission to view vehicle purchase installments.")
        return render(request, "403.html", status=403)

    purchase = get_object_or_404(VehiclePurchase, pk=pk)
    installments_qs = purchase.installments.all().order_by('installment_no')
    
    # Calculate payment statistics
    total_paid = sum(inst.amount for inst in installments_qs if inst.is_paid)
    total_pending = sum(inst.amount for inst in installments_qs if not inst.is_paid)
    paid_count = installments_qs.filter(is_paid=True).count()
    pending_count = installments_qs.filter(is_paid=False).count()
    
    page_num = request.GET.get('page', 1)
    paginator_list, page_obj, last_page_number = paginate_data(request, page_num, installments_qs)
    paginator = page_obj.paginator

    context = {
        'purchase': purchase,
        'installments': page_obj,
        'paginator_list': paginator_list,
        'page_num': page_obj.number,
        'paginator': paginator,
        'last_page_number': last_page_number,
        'total_paid': total_paid,
        'total_pending': total_pending,
        'paid_count': paid_count,
        'pending_count': pending_count,
    }
    return render(request, 'vehicle_purchase/installments.html', context)


@login_required
def vehicle_installment_create(request):
    if not checkUserPermission(request, "can_add", "/backend/vehicle-installment/"):
        messages.error(request, "You do not have permission to add vehicle installments.")
        return render(request, "403.html", status=403)

    if request.method == 'POST':
        form = VehicleInstallmentForm(request.POST)
        if form.is_valid():
            installment = form.save(commit=False)
            installment.created_by = request.user
            installment.save()
            messages.success(request, "Vehicle installment created successfully.")
            return redirect('vehicle_installment:list')
    else:
        form = VehicleInstallmentForm()

    context = {
        'form': form,
        'purchases': VehiclePurchase.objects.filter(is_active=True, deleted=False),
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
            installment = form.save(commit=False)
            installment.updated_by = request.user
            installment.save()
            messages.success(request, "Vehicle installment updated successfully.")
            return redirect('vehicle_installment:list')
    else:
        form = VehicleInstallmentForm(instance=installment)

    context = {
        'form': form,
        'installment': installment,
        'purchases': VehiclePurchase.objects.filter(is_active=True, deleted=False),
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


