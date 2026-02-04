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

# Vehicle Info URL patterns
vehicle_patterns = ([
    path('', views.VehicleListView.as_view(), name='list'),
    path('create/', views.VehicleCreateView.as_view(), name='create'),
    path('update/<int:pk>/', views.VehicleUpdateView.as_view(), name='update'),
    path('delete/<int:pk>/', views.vehicle_delete, name='delete'),
], 'vehicle_info')

# Vehicle Handover URL patterns
vehicle_handover_patterns = ([
    path('', views.VehicleHandoverListView.as_view(), name='list'),
    path('create/', views.vehicle_handover_create, name='create'),
    path('update/<int:pk>/', views.vehicle_handover_update, name='update'),
    path('detail/<int:pk>/', views.vehicle_handover_detail, name='detail'),
    path('delete/<int:pk>/', views.vehicle_handover_delete, name='delete'),
], 'vehicle_handover')

# Traffic Violation URL patterns
traffic_violation_patterns = ([
    path('', views.TrafficViolationListView.as_view(), name='list'),
    path('create/', views.traffic_violation_create, name='create'),
    path('update/<int:pk>/', views.traffic_violation_update, name='update'),
    path('detail/<int:pk>/', views.traffic_violation_detail, name='detail'),
    path('delete/<int:pk>/', views.traffic_violation_delete, name='delete'),
], 'traffic_violation')

# Vehicle Rent URL patterns
vehicle_rent_patterns = ([
    path('', views.VehicleRentListView.as_view(), name='list'),
    path('create/', views.vehicle_rent_create, name='create'),
    path('update/<int:pk>/', views.vehicle_rent_update, name='update'),
    path('delete/<int:pk>/', views.vehicle_rent_delete, name='delete'),
], 'vehicle_rent')

# Vehicle Maintenance URL patterns
vehicle_maintenance_patterns = ([
    path('', views.VehicleMaintenanceListView.as_view(), name='list'),
    path('create/', views.vehicle_maintenance_create, name='create'),
    path('update/<int:pk>/', views.vehicle_maintenance_update, name='update'),
    path('detail/<int:pk>/', views.vehicle_maintenance_detail, name='detail'),
    path('delete/<int:pk>/', views.vehicle_maintenance_delete, name='delete'),
], 'vehicle_maintenance')

# Vehicle Accident URL patterns
vehicle_accident_patterns = ([
    path('', views.VehicleAccidentListView.as_view(), name='list'),
    path('create/', views.vehicle_accident_create, name='create'),
    path('update/<int:pk>/', views.vehicle_accident_update, name='update'),
    path('detail/<int:pk>/', views.vehicle_accident_detail, name='detail'),
    path('delete/<int:pk>/', views.vehicle_accident_delete, name='delete'),
], 'vehicle_accident')

# Vehicle Installment URL patterns
vehicle_installment_patterns = ([
    path('', views.VehicleInstallmentListView.as_view(), name='list'),
    path('create/', views.vehicle_installment_create, name='create'),
    path('update/<int:pk>/', views.vehicle_installment_update, name='update'),
    path('delete/<int:pk>/', views.vehicle_installment_delete, name='delete'),
], 'vehicle_installment')

# Vehicle Item URL patterns
vehicle_item_patterns = ([
    path('', views.VehicleItemListView.as_view(), name='list'),
    path('create/', views.vehicle_item_create, name='create'),
    path('update/<int:pk>/', views.vehicle_item_update, name='update'),
    path('delete/<int:pk>/', views.vehicle_item_delete, name='delete'),
], 'vehicle_item')


backend_patterns = ([
    path("api/menu-search/", views.search_backend_menus, name="search_backend_menus"),
    # Image optimization
    path("image/<str:unique_key>/", views.serve_optimized_image, name="serve_optimized_image"),
    path('', views.backend_dashboard, name='backend_dashboard'),
    path('login/', views.backend_login, name='backend_login'),
    path('logout/', views.backend_logout, name='backend_logout'),
    path('<str:menu_slug>-menu/', views.menu_wise_dashboard, name='menu_wise_dashboard'),

    path('user/', views.UserListView.as_view(), name='user_list'),
    path('user/add/', views.user_add, name='user_add'),
    path('user/update/<str:data_id>/', views.user_update, name='user_update'),
    path('user/password/reset/<str:data_id>/', views.reset_password, name='reset_password'),
    path('user/permission/<int:user_id>/', views.user_permission, name='user_permission'),
    
    # Vehicle Management Dashboard
    path('vehicle-management/', views.vehicle_management, name='vehicle_management'),

], 'backend')


urlpatterns = [
    # User Management
 
    path('', include(backend_patterns)),
    path('nationality/', include(nationality_patterns)), 
    path('employee/', include(employee_patterns)),
    path('vehicle-info/', include(vehicle_patterns)),
    path('vehicle-handover/', include(vehicle_handover_patterns)),
    path('traffic-violation/', include(traffic_violation_patterns)),
    path('vehicle-rent/', include(vehicle_rent_patterns)),
    path('vehicle-maintenance/', include(vehicle_maintenance_patterns)),
    path('vehicle-accident/', include(vehicle_accident_patterns)),
    path('vehicle-installment/', include(vehicle_installment_patterns)),
    path('vehicle-item/', include(vehicle_item_patterns)),
]
