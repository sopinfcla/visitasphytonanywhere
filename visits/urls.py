# visits/urls.py
from django.urls import path, include
from django.contrib.auth import views as auth_views
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'appointments', views.AppointmentViewSet)

urlpatterns = [
    # Autenticación
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='public_booking'), name='logout'),
    
    # Vistas públicas
    path('', views.PublicBookingView.as_view(), name='public_booking'),
    path('stage/<int:stage_id>/', views.StageBookingView.as_view(), name='stage_booking'),
    path('stage/<int:stage_id>/book/<int:slot_id>/', views.book_appointment, name='book_appointment'),
    path('appointment/<int:appointment_id>/confirmation/', 
         views.AppointmentConfirmationView.as_view(), 
         name='appointment_confirmation'),
    path('privacy-policy/', views.PrivacyPolicyView.as_view(), name='privacy_policy'),
    
    # Vistas del panel de administración
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('availability/', views.StaffAvailabilityView.as_view(), name='staff_availability'),
    path('appointments/', views.AppointmentsCRUDView.as_view(), name='appointments_crud'),
    
    # API endpoints
    path('api/', include(router.urls)),
    path('api/stage/<int:stage_id>/availability/', views.get_stage_availability, name='stage_availability'),
    path('api/stage/<int:stage_id>/staff/', views.staff_by_stage, name='staff_by_stage'),
    path('api/availability/', views.StaffAvailabilityView.as_view(), name='api_availability'),
    path('api/availability/<int:slot_id>/', views.StaffAvailabilityView.as_view(), name='api_delete_availability'),
    path('api/appointments/', views.AppointmentAPIView.as_view(), name='api_appointments'),
    path('api/appointments/<int:appointment_id>/', views.AppointmentAPIView.as_view(), name='api_appointment_detail'),
]