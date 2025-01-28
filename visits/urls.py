# visits/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'appointments', views.AppointmentViewSet)

urlpatterns = [
    # Vistas públicas
    path('', views.PublicBookingView.as_view(), name='public_booking'),
    path('stage/<int:stage_id>/', views.StageBookingView.as_view(), name='stage_booking'),
    
    # Vistas del panel de administración
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('availability/', views.StaffAvailabilityView.as_view(), name='staff_availability'),
    
    # API endpoints
    path('api/', include(router.urls)),
    path('api/stage/<int:stage_id>/availability/', views.get_stage_availability, name='stage_availability'),
    path('api/stage/<int:stage_id>/staff/', views.staff_by_stage, name='staff_by_stage'),
    path('api/availability/', views.StaffAvailabilityView.as_view(), name='api_availability'),
    path('api/availability/<int:slot_id>/', views.StaffAvailabilityView.as_view(), name='api_delete_availability'),
    
    # Reserva
    path('stage/<int:stage_id>/book/<int:slot_id>/', views.book_appointment, name='book_appointment'),
]