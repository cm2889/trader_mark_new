from django.urls import path, include
from . import views
from . import view_copy 

export_import_patterns = ([
    path('import/', view_copy.import_excel, name='import_excel'),
    path('export/', view_copy.export_excel, name='export_excel'), 
], 'import_export')


company_patterns = ([
    path('', views.CompanyListView.as_view(), name='list'),
    path('create/', views.CompanyCreateView.as_view(), name='create'),
    path('update/<int:pk>/', views.CompanyUpdateView.as_view(), name='update'),
    path('delete/<int:pk>/', views.company_delete, name='delete'),
], 'company')


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
    path('convert-to-lead/<int:visitor_id>/', views.visitor_convert_to_lead, name='convert_to_lead'),
], 'visitor')


lead_patterns = ([
    path('', views.LeadListView.as_view(), name='list'),
    path('create/', views.lead_create, name='create'),
    path('update/<int:pk>/', views.lead_update, name='update'),
    path('detail/<int:pk>/', views.lead_detail, name='detail'),
    path('delete/<int:pk>/', views.lead_delete, name='delete'),
    path('convert-to-employee/<int:pk>/', views.lead_convert_to_employee, name='convert_to_employee'),
], 'lead')

lead_source_patterns = ([
    path('', views.LeadSourceListView.as_view(), name='list'),
    path('create/', views.LeadSourceCreateView.as_view(), name='create'),
    path('update/<int:pk>/', views.LeadSourceUpdateView.as_view(), name='update'),
    path('delete/<int:pk>/', views.lead_source_delete, name='delete'),
], 'lead_source')


lead_stage_patterns = ([
    path('', views.LeadStageListView.as_view(), name='list'),
    path('create/', views.LeadStageCreateView.as_view(), name='create'),
    path('update/<int:pk>/', views.LeadStageUpdateView.as_view(), name='update'),
    path('delete/<int:pk>/', views.lead_stage_delete, name='delete'),
], 'lead_stage')


followup_patterns = ([
    path('', views.FollowUpListView.as_view(), name='list'),
    path('create/', views.followup_create, name='create'),
    path('update/<int:pk>/', views.followup_update, name='update'),
    path('delete/<int:pk>/', views.followup_delete, name='delete'),
], 'followup')


reminder_patterns = ([
    path('create/', views.reminder_create, name='create'),
    path('update/<int:pk>/', views.reminder_update, name='update'),
    path('mark-done/<int:pk>/', views.reminder_mark_done, name='mark_done'),
    path('delete/<int:pk>/', views.reminder_delete, name='delete'),
], 'reminder')


employee_patterns = ([
    path('', views.EmployeeListView.as_view(), name='list'),
    path('create/', views.employee_create, name='create'),
    path('update/<int:pk>/', views.employee_update, name='update'),
    path('delete/<int:pk>/', views.employee_delete, name='delete'),
    path('detail/<int:pk>/', views.EmployeeDetailView.as_view(), name='detail'),
    path('info/<int:pk>/', views.employee_profile, name='profile'),
], 'employee')


vehicle_assign_patterns = ([
    path('', views.VehicleAssignListView.as_view(), name='list'),
    path('create/', views.VehicleAssignCreateView.as_view(), name='create'),
    path('update/<int:pk>/', views.VehicleAssignUpdateView.as_view(), name='update'),
    path('delete/<int:pk>/', views.vehicle_assign_delete, name='delete'),
], 'vehicle_assign')


vehicle_patterns = ([
    path('', views.VehicleListView.as_view(), name='list'),
    path('create/', views.VehicleCreateView.as_view(), name='create'),
    path('detail/<int:pk>/', views.VehicleDetailView.as_view(), name='detail'),
    path('update/<int:pk>/', views.VehicleUpdateView.as_view(), name='update'),
    path('delete/<int:pk>/', views.vehicle_delete, name='delete'),
    path('assign/<int:pk>/', views.vehicle_assign_quick, name='assign'),
    path('unassign/<int:pk>/', views.vehicle_unassign, name='unassign'),
], 'vehicle_info')


vehicle_handover_patterns = ([
    path('', views.VehicleHandoverListView.as_view(), name='list'),
    path('create/', views.vehicle_handover_create, name='create'),
    path('update/<int:pk>/', views.vehicle_handover_update, name='update'),
    path('detail/<int:pk>/', views.vehicle_handover_detail, name='detail'),
    path('delete/<int:pk>/', views.vehicle_handover_delete, name='delete'),
], 'vehicle_handover')


violation_type_patterns = ([
    path('', views.ViolationTypeListView.as_view(), name='list'),
    path('create/', views.ViolationTypeCreateView.as_view(), name='create'),
    path('update/<int:pk>/', views.ViolationTypeUpdateView.as_view(), name='update'),
    path('delete/<int:pk>/', views.violation_type_delete, name='delete'),
], 'violation_type') 


traffic_violation_patterns = ([
    path('', views.TrafficViolationListView.as_view(), name='list'),
    path('create/', views.traffic_violation_create, name='create'),
    path('update/<int:pk>/', views.traffic_violation_update, name='update'),
    path('detail/<int:pk>/', views.traffic_violation_detail, name='detail'),
    path('delete/<int:pk>/', views.traffic_violation_delete, name='delete'),
], 'traffic_violation')


vehicle_maintenance_patterns = ([
    path('', views.VehicleMaintenanceListView.as_view(), name='list'),
    path('create/', views.vehicle_maintenance_create, name='create'),
    path('update/<int:pk>/', views.vehicle_maintenance_update, name='update'),
    path('detail/<int:pk>/', views.vehicle_maintenance_detail, name='detail'),
    path('delete/<int:pk>/', views.vehicle_maintenance_delete, name='delete'),
], 'vehicle_maintenance')


vehicle_accident_patterns = ([
    path('', views.VehicleAccidentListView.as_view(), name='list'),
    path('create/', views.vehicle_accident_create, name='create'),
    path('update/<int:pk>/', views.vehicle_accident_update, name='update'),
    path('detail/<int:pk>/', views.vehicle_accident_detail, name='detail'),
    path('delete/<int:pk>/', views.vehicle_accident_delete, name='delete'),
], 'vehicle_accident')


vehicle_installment_patterns = ([
    path('', views.VehicleInstallmentListView.as_view(), name='list'),
    path('create/', views.vehicle_installment_create, name='create'),
    path('update/<int:pk>/', views.vehicle_installment_update, name='update'),
    path('delete/<int:pk>/', views.vehicle_installment_delete, name='delete'),
    path('pay/<int:pk>/', views.installment_pay, name='pay'),
], 'vehicle_installment')


vehicle_purchase_patterns = ([
    path('', views.vehicle_purchase_list, name='list'),
    path('create/', views.vehicle_purchase_create, name='create'),
    path('detail/<int:pk>/', views.vehicle_purchase_detail, name='detail'),
    path('delete/<int:pk>/', views.vehicle_purchase_delete, name='delete'),
    path('<int:pk>/installments/', views.purchase_installments_list, name='installments'),
], 'vehicle_purchase')


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


vehicle_maintanance_type_patterns = ([
    path('', views.VehicleMaintananceTypeListView.as_view(), name='list'),
    path('create/', views.VehicleMaintananceTypeCreateView.as_view(), name='create'),
    path('update/<int:pk>/', views.VehicleMaintananceTypeUpdateView.as_view(), name='update'),
    path('delete/<int:pk>/', views.vehicle_maintanance_type_delete, name='delete'),
], 'vehicle_maintanance_type')


uniform_patterns = ([
    path('', views.UniformListView.as_view(), name='list'),
    path('create/', views.UniformCreateView.as_view(), name='create'),
    path('update/<int:pk>/', views.UniformUpdateView.as_view(), name='update'),
    path('delete/<int:pk>/', views.uniform_delete, name='delete'),
    path('report/', views.uniform_report, name='report'),
    path('log/', views.uniform_log, name='log'),
], 'uniform')


uniform_stock_patterns = ([
    path('', views.UniformStockListView.as_view(), name='list'),
    path('create/', views.UniformStockCreateView.as_view(), name='create'),
    path('update/<int:pk>/', views.UniformStockUpdateView.as_view(), name='update'),
    path('delete/<int:pk>/', views.uniform_stock_delete, name='delete'),
], 'uniform_stock')


uniform_issuance_patterns = ([
    path('', views.UniformIssuanceListView.as_view(), name='list'),
    path('create/', views.UniformIssuanceCreateView.as_view(), name='create'),
    path('update/<int:pk>/', views.UniformIssuanceUpdateView.as_view(), name='update'),
    path('detail/<int:pk>/', views.UniformIssuanceDetailView.as_view(), name='detail'),
    path('return/<int:pk>/', views.uniform_issuance_return, name='return'),
    path('delete/<int:pk>/', views.uniform_issuance_delete, name='delete'),
], 'uniform_issuance')


uniform_clearance_patterns = ([
    path('', views.UniformClearanceListView.as_view(), name='list'),
    path('delete/<int:pk>/', views.uniform_clearance_delete, name='delete'),
], 'uniform_clearance')


mail_log_patterns = ([
    path('expire-report/', views.expire_report, name='expire_report'),
    path('mail-logs/', views.expire_mail_logs, name='mail_logs'),
    path('send-single-mail/', views.send_single_expiry_mail, name='send_single_mail'),
    path('send-bulk-mail/', views.send_bulk_expiry_mail, name='send_bulk_mail'),
], 'mail_log')


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
    
    # Dashboards
    path('dashboard/', views.dash_board, name='dash_board'),
    path('vehicle-management/', views.vehicle_management, name='vehicle_management'),

], 'backend')


urlpatterns = [
    path('', include(backend_patterns)),
    path('company/', include(company_patterns)),
    path('nationality/', include(nationality_patterns)), 
    path('visitor/', include(visitor_patterns)), 
    path('lead/', include(lead_patterns)),
    path('lead-source/', include(lead_source_patterns)),
    path('lead-stage/', include(lead_stage_patterns)),
    path('followup/', include(followup_patterns)),
    path('reminder/', include(reminder_patterns)),
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
    path('', include(mail_log_patterns)),
    # excel data
    path('excel/', include(export_import_patterns)), 
]
