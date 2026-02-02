from django.urls import path, include
from . import views



# Nationality URL patterns
nationality_patterns = ([
    path('', views.NationalityListView.as_view(), name='list'),
    path('create/', views.NationalityCreateView.as_view(), name='create'),
    path('update/<int:pk>/', views.NationalityUpdateView.as_view(), name='update'),
    path('delete/<int:pk>/', views.nationality_delete, name='delete'),
], 'nationality')

# Employee URL patterns
employee_patterns = ([
    path('', views.EmployeeListView.as_view(), name='list'),
    path('create/', views.employee_create, name='create'),
    path('update/<int:pk>/', views.employee_update, name='update'),
    path('delete/<int:pk>/', views.employee_delete, name='delete'),
    path('detail/<int:pk>/', views.EmployeeDetailView.as_view(), name='detail'),
], 'employee')

# Employment URL patterns
employment_patterns = ([
    path('', views.EmployeementListView.as_view(), name='list'),
    path('delete/<int:pk>/', views.employeement_delete, name='delete'),
    path('detail/<int:pk>/', views.EmployeementDetailView.as_view(), name='detail'),
], 'employeement')

# Passport URL patterns
passport_patterns = ([
    path('', views.PassportListView.as_view(), name='list'),
    path('delete/<int:pk>/', views.passport_delete, name='delete'),
    path('detail/<int:pk>/', views.PassportDetailView.as_view(), name='detail'),
], 'passport')

# Driving License URL patterns
driving_license_patterns = ([
    path('', views.DrivingLicenseListView.as_view(), name='list'),
    path('delete/<int:pk>/', views.driving_license_delete, name='delete'),
    path('detail/<int:pk>/', views.DrivingLicenseDetailView.as_view(), name='detail'),
], 'driving_license')

# Health Insurance URL patterns
health_insurance_patterns = ([
    path('', views.HealthInsuranceListView.as_view(), name='list'),
    path('delete/<int:pk>/', views.health_insurance_delete, name='delete'),
    path('detail/<int:pk>/', views.HealthInsuranceDetailView.as_view(), name='detail'),
], 'health_insurance')

# Contact URL patterns
contact_patterns = ([
    path('', views.ContactListView.as_view(), name='list'),
    path('delete/<int:pk>/', views.contact_delete, name='delete'),
    path('detail/<int:pk>/', views.ContactDetailView.as_view(), name='detail'),
], 'contact')

# Address URL patterns
address_patterns = ([
    path('', views.AddressListView.as_view(), name='list'),
    path('delete/<int:pk>/', views.address_delete, name='delete'),
    path('detail/<int:pk>/', views.AddressDetailView.as_view(), name='detail'),
], 'address')

# Vehicle URL patterns
vehicle_patterns = ([
    path('', views.VehicleListView.as_view(), name='list'),
    path('delete/<int:pk>/', views.vehicle_delete, name='delete'),
    path('detail/<int:pk>/', views.VehicleDetailView.as_view(), name='detail'),
], 'vehicle')


backend_patterns = ([
    path("api/menu-search/", views.search_backend_menus, name="search_backend_menus"),
    # Image optimization
    path("image/<str:unique_key>/", views.serve_optimized_image, name="serve_optimized_image"),
    path('', views.backend_dashboard, name='backend_dashboard'),
    path('login/', views.backend_login, name='backend_login'),
    path('logout/', views.backend_logout, name='backend_logout'),
    path('<str:menu_slug>-menu/', views.menu_wise_dashboard, name='menu_wise_dashboard'),
], 'backend')


urlpatterns = [    

    path('', include(backend_patterns)),
    path('nationality/', include(nationality_patterns)), 
    path('employee/', include(employee_patterns)),
    path('employment/', include(employment_patterns)),
    path('passport/', include(passport_patterns)),
    path('driving-license/', include(driving_license_patterns)),
    path('health-insurance/', include(health_insurance_patterns)),
    path('contact/', include(contact_patterns)),
    path('address/', include(address_patterns)),
    path('vehicle/', include(vehicle_patterns)),
]
