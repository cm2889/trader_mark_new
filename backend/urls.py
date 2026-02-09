from django.urls import path, include
from . import views

# Nationality URL patterns
nationality_patterns = ([
    path('', views.NationalityListView.as_view(), name='list'),
    path('create/', views.NationalityCreateView.as_view(), name='create'),
    path('update/<int:pk>/', views.NationalityUpdateView.as_view(), name='update'),
    path('delete/<int:pk>/', views.nationality_delete, name='delete'),
], 'nationality')

visitor_patterns = ([
    path('', views.VisitorListView.as_view(), name='list'),
    path('create/', views.VisitorCreateView.as_view(), name='create'),
    path('update/<int:pk>/', views.VisitorUpdateView.as_view(), name='update'),
    path('delete/<int:pk>/', views.visitor_delete, name='delete'),
], 'visitor')

# Employee URL patterns
employee_patterns = ([
    path('', views.EmployeeListView.as_view(), name='list'),
    path('create/', views.employee_create, name='create'),
    path('update/<int:pk>/', views.employee_update, name='update'),
    path('delete/<int:pk>/', views.employee_delete, name='delete'),
    path('detail/<int:pk>/', views.EmployeeDetailView.as_view(), name='detail'),
    path('profile/<int:pk>/', views.employee_profile, name='profile'),
], 'employee')

vehicle_assign_patterns = ([
    path('', views.VehicleAssignListView.as_view(), name='list'),
    path('create/', views.VehicleAssignCreateView.as_view(), name='create'),
    path('update/<int:pk>/', views.VehicleAssignUpdateView.as_view(), name='update'),
    path('delete/<int:pk>/', views.vehicle_assign_delete, name='delete'),
], 'vehicle_assign')

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

# Traffic violation Type URL patterns
violation_type_patterns = ([
    path('', views.ViolationTypeListView.as_view(), name='list'),
    path('create/', views.ViolationTypeCreateView.as_view(), name='create'),
    path('update/<int:pk>/', views.ViolationTypeUpdateView.as_view(), name='update'),
    path('delete/<int:pk>/', views.violation_type_delete, name='delete'),
], 'violation_type') 

# Traffic Violation URL patterns
traffic_violation_patterns = ([
    path('', views.TrafficViolationListView.as_view(), name='list'),
    path('create/', views.traffic_violation_create, name='create'),
    path('update/<int:pk>/', views.traffic_violation_update, name='update'),
    path('detail/<int:pk>/', views.traffic_violation_detail, name='detail'),
    path('delete/<int:pk>/', views.traffic_violation_delete, name='delete'),
], 'traffic_violation')

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
    path('pay/<int:pk>/', views.installment_pay, name='pay'),
], 'vehicle_installment')

# Vehicle Purchase URL patterns
vehicle_purchase_patterns = ([
    path('', views.vehicle_purchase_list, name='list'),
    path('create/', views.vehicle_purchase_create, name='create'),
    path('detail/<int:pk>/', views.vehicle_purchase_detail, name='detail'),
    path('delete/<int:pk>/', views.vehicle_purchase_delete, name='delete'),
    path('<int:pk>/installments/', views.purchase_installments_list, name='installments'),
], 'vehicle_purchase')

# Traffic Violation Penalty URL patterns
traffic_violation_penalty_patterns = ([
    path('', views.TrafficViolationPenaltyListView.as_view(), name='list'),
    path('create/', views.TrafficViolationPenaltyCreateView.as_view(), name='create'),
    path('update/<int:pk>/', views.TrafficViolationPenaltyUpdateView.as_view(), name='update'),
    path('detail/<int:pk>/', views.TrafficViolationPenaltyDetailView.as_view(), name='detail'),
    path('delete/<int:pk>/', views.traffic_violation_penalty_delete, name='delete'),
], 'traffic_violation_penalty')

# Insurance Claim URL patterns
insurance_claim_patterns = ([
    path('', views.InsuranceClaimListView.as_view(), name='list'),
    path('create/', views.InsuranceClaimCreateView.as_view(), name='create'),
    path('update/<int:pk>/', views.InsuranceClaimUpdateView.as_view(), name='update'),
    path('detail/<int:pk>/', views.InsuranceClaimDetailView.as_view(), name='detail'),
    path('delete/<int:pk>/', views.insurance_claim_delete, name='delete'),
], 'insurance_claim')

# Vehicle Maintenance Type URL patterns
vehicle_maintanance_type_patterns = ([
    path('', views.VehicleMaintananceTypeListView.as_view(), name='list'),
    path('create/', views.VehicleMaintananceTypeCreateView.as_view(), name='create'),
    path('update/<int:pk>/', views.VehicleMaintananceTypeUpdateView.as_view(), name='update'),
    path('delete/<int:pk>/', views.vehicle_maintanance_type_delete, name='delete'),
], 'vehicle_maintanance_type')

# Uniform URL patterns
uniform_patterns = ([
    path('', views.UniformListView.as_view(), name='list'),
    path('create/', views.UniformCreateView.as_view(), name='create'),
    path('update/<int:pk>/', views.UniformUpdateView.as_view(), name='update'),
    path('delete/<int:pk>/', views.uniform_delete, name='delete'),
    path('report/', views.uniform_report, name='report'),
], 'uniform')

# Uniform Stock URL patterns
uniform_stock_patterns = ([
    path('', views.UniformStockListView.as_view(), name='list'),
    path('create/', views.UniformStockCreateView.as_view(), name='create'),
    path('update/<int:pk>/', views.UniformStockUpdateView.as_view(), name='update'),
    path('delete/<int:pk>/', views.uniform_stock_delete, name='delete'),
], 'uniform_stock')

# Uniform Issuance URL patterns
uniform_issuance_patterns = ([
    path('', views.UniformIssuanceListView.as_view(), name='list'),
    path('create/', views.UniformIssuanceCreateView.as_view(), name='create'),
    path('update/<int:pk>/', views.UniformIssuanceUpdateView.as_view(), name='update'),
    path('delete/<int:pk>/', views.uniform_issuance_delete, name='delete'),
], 'uniform_issuance')

# Uniform Clearance URL patterns
uniform_clearance_patterns = ([
    path('', views.UniformClearanceListView.as_view(), name='list'),
    path('create/', views.UniformClearanceCreateView.as_view(), name='create'),
    path('update/<int:pk>/', views.UniformClearanceUpdateView.as_view(), name='update'),
    path('delete/<int:pk>/', views.uniform_clearance_delete, name='delete'),
], 'uniform_clearance')


backend_patterns = ([
    path("api/menu-search/", views.search_backend_menus, name="search_backend_menus"),
    path("api/get-visitor/", views.get_visitor_by_contact, name="get_visitor_by_contact"),
    # Image optimization
    path("image/<str:unique_key>/", views.serve_optimized_image, name="serve_optimized_image"),
    path('', views.backend_dashboard, name='backend_dashboard'),
    path('login/', views.backend_login, name='backend_login'),
    path('logout/', views.backend_logout, name='backend_logout'),
    path('<str:menu_slug>-menu/', views.menu_wise_dashboard, name='menu_wise_dashboard'),

    path('user/', views.UserListView.as_view(), name='user_list'),
    path('user/update/<str:data_id>/', views.user_update, name='user_update'),
    path('user/password/reset/<str:data_id>/', views.reset_password, name='reset_password'),
    path('user/permission/<int:user_id>/', views.user_permission, name='user_permission'),
    
    # Vehicle Management Dashboard
    path('vehicle-management/', views.vehicle_management, name='vehicle_management'),

], 'backend')


urlpatterns = [
    path('', include(backend_patterns)),
    path('nationality/', include(nationality_patterns)), 
    path('visitor/', include(visitor_patterns)), 
    path('employee/', include(employee_patterns)),
    path('vehicle-info/', include(vehicle_patterns)),
    path('vehicle-assign/', include(vehicle_assign_patterns)), 
    path('vehicle-handover/', include(vehicle_handover_patterns)),
    path('violation-type/', include(violation_type_patterns)),
    path('traffic-violation/', include(traffic_violation_patterns)),
    path('traffic-violation-penalty/', include(traffic_violation_penalty_patterns)),
    path('insurance-claim/', include(insurance_claim_patterns)),
    path('vehicle-maintenance-type/', include(vehicle_maintanance_type_patterns)),
    path('vehicle-maintenance/', include(vehicle_maintenance_patterns)),
    path('vehicle-accident/', include(vehicle_accident_patterns)),
    path('vehicle-purchase/', include(vehicle_purchase_patterns)),
    path('vehicle-installment/', include(vehicle_installment_patterns)),
    path('uniform/', include(uniform_patterns)),
    path('uniform-stock/', include(uniform_stock_patterns)),
    path('uniform-issuance/', include(uniform_issuance_patterns)),
    path('uniform-clearance/', include(uniform_clearance_patterns)),
]
