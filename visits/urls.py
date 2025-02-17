from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import (
    StaffProfileView,
    StaffPasswordChangeView,
    StaffLoginView,
    DashboardView,
    DashboardStatsView,
    DashboardCalendarView,
    AppointmentExportView  # Añadimos el nuevo import
)

urlpatterns = [
    # Autenticación
    path('login/', StaffLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(
        next_page='public_booking',
        template_name=None
    ), name='logout'),
    
    # Vistas públicas
    path('', views.PublicBookingView.as_view(), name='public_booking'),
    path('stage/<int:stage_id>/', views.StageBookingView.as_view(), name='stage_booking'),
    path('stage/<int:stage_id>/book/<int:slot_id>/', views.book_appointment, name='book_appointment'),
    path('appointment/<int:appointment_id>/confirmation/', 
         views.AppointmentConfirmationView.as_view(), 
         name='appointment_confirmation'),
    path('privacy-policy/', views.PrivacyPolicyView.as_view(), name='privacy_policy'),
    
    # Vistas del panel de administración
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('dashboard/stats/', DashboardStatsView.as_view(), name='dashboard_stats'),
    path('dashboard/calendar/', DashboardCalendarView.as_view(), name='dashboard_calendar'),
    path('availability/', views.StaffAvailabilityView.as_view(), name='staff_availability'),
    path('appointments/', views.AppointmentsCRUDView.as_view(), name='appointments_crud'),
    
    # API endpoints
    path('api/stage/<int:stage_id>/availability/', views.get_stage_availability, name='stage_availability'),
    path('api/stage/<int:stage_id>/staff/', views.staff_by_stage, name='staff_by_stage'),
    path('api/availability/', views.StaffAvailabilityView.as_view(), name='api_availability'),
    path('api/availability/<int:slot_id>/', views.StaffAvailabilityView.as_view(), name='api_delete_availability'),
    
    # API Appointments
    path('api/appointments/', views.AppointmentAPIView.as_view(), name='api_appointments'),
    path('api/appointments/<int:appointment_id>/', views.AppointmentAPIView.as_view(), name='api_appointment_detail'),
    
    # Nuevos endpoints para exportación
    path('api/appointments/export/', AppointmentExportView.as_view(), name='appointment_export'),
    path('api/appointments/<int:appointment_id>/export/', AppointmentExportView.as_view(), name='appointment_single_export'),

    # Staff Profile Management
    path('staff/profile/', StaffProfileView.as_view(), name='staff_profile'),
    path('staff/profile/password/', StaffPasswordChangeView.as_view(), name='staff_password_change'),
]