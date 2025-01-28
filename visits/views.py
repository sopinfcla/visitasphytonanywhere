from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView, View
from rest_framework import viewsets
from django.http import JsonResponse
from datetime import datetime, timedelta, time
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.timezone import make_aware
from django.urls import reverse
import json

from .models import (
    Appointment, 
    SchoolStage, 
    StaffProfile, 
    AvailabilitySlot
)
from .serializers import (
    AppointmentSerializer,
    AvailabilitySlotSerializer,
    CalendarDaySerializer
)

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'visits/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if hasattr(self.request.user, 'staffprofile'):
            context['appointments'] = Appointment.objects.filter(staff=self.request.user.staffprofile)
        else:
            context['appointments'] = Appointment.objects.none()
        return context

class PublicBookingView(TemplateView):
    template_name = 'visits/public_booking.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        stages = []
        # Obtener todas las etapas y su personal asignado
        for stage in SchoolStage.objects.all().prefetch_related('staffprofile_set'):
            # Datos base de la etapa desde BD
            stage_data = {
                'id': stage.id,
                'name': stage.name,
                'description': stage.description,
                'staff': [{'id': s.id, 'name': s.user.get_full_name()} 
                         for s in stage.staffprofile_set.all()]
            }
            
            # Metadata adicional por etapa
            metadata = {
                'Escuela Infantil': {
                    'icon': '👶',
                    'features': ['Programa bilingüe', 'Nuevas tecnologías', 'Desarrollo personal']
                },
                'Infantil': {
                    'icon': '🎨',
                    'features': ['Aprendizaje lúdico', 'Desarrollo creativo', 'Socialización']
                },
                'Primaria': {
                    'icon': '📚',
                    'features': ['Ciencias', 'Humanidades', 'Orientación académica']
                },
                'Secundaria': {
                    'icon': '🔬',
                    'features': ['Orientación académica', 'Innovación educativa', 'Formación integral']
                },
                'Bachillerato': {
                    'icon': '🎓',
                    'features': ['Ciencias', 'Humanidades', 'Orientación universitaria']
                }
            }
            
            # Añadir metadata si existe para la etapa
            if stage.name in metadata:
                stage_data.update(metadata[stage.name])
                
            stages.append(stage_data)
        
        context['stages'] = stages
        context['stages_json'] = json.dumps(stages)
        return context

class StageBookingView(TemplateView):
    template_name = 'visits/stage_booking.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stage_id = kwargs.get('stage_id')
        stage = get_object_or_404(SchoolStage, id=stage_id)
        
        context.update({
            'stage': stage,
            'stage_json': json.dumps({
                'id': stage.id,
                'name': stage.name,
                'description': stage.description
            })
        })
        return context

class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer

def staff_by_stage(request, stage_id):
    staff = StaffProfile.objects.filter(allowed_stages=stage_id)
    data = [{'id': s.id, 'name': s.user.get_full_name()} for s in staff]
    return JsonResponse(data, safe=False)

def get_stage_availability(request, stage_id):
    try:
        # Obtener fecha específica si se proporciona
        date_param = request.GET.get('date')
        print(f"Request para stage_id: {stage_id}, date_param: {date_param}")

        if date_param:
            try:
                date = datetime.strptime(date_param, '%Y-%m-%d').date()
                start_date = date
                end_date = date
                print(f"Buscando slots para fecha específica: {date}")
            except ValueError:
                start_date = datetime.now().date()
                end_date = start_date
                print(f"Error en fecha, usando fecha actual: {start_date}")
        else:
            # Para vista mensual, obtener todo el mes actual
            today = datetime.now().date()
            start_date = today.replace(day=1)
            if today.month == 12:
                end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_date = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
            print(f"Buscando slots para mes: {start_date} hasta {end_date}")

        # Obtener slots disponibles
        slots = AvailabilitySlot.objects.filter(
            stage_id=stage_id,
            date__range=(start_date, end_date),
            is_active=True
        ).select_related('staff__user')
        print(f"Slots encontrados en BD: {slots.count()}")

        # Obtener citas existentes
        appointments = Appointment.objects.filter(
            stage_id=stage_id,
            date__range=(
                make_aware(datetime.combine(start_date, time.min)),
                make_aware(datetime.combine(end_date, time.max))
            )
        )
        print(f"Citas existentes: {appointments.count()}")

        # Excluir slots ocupados
        booked_datetimes = set(
            (appt.date.date(), appt.date.time()) 
            for appt in appointments
        )
        
        available_slots = [
            slot for slot in slots 
            if (slot.date, slot.start_time) not in booked_datetimes
        ]
        print(f"Slots disponibles después de filtrar: {len(available_slots)}")

        if date_param:
            # Para día específico: devolver slots detallados ordenados por hora
            serializer = AvailabilitySlotSerializer(
                sorted(available_slots, key=lambda x: x.start_time),
                many=True
            )
            data = serializer.data
            print(f"Devolviendo {len(data)} slots para el día")
        else:
            # Para vista mensual: agrupar por fecha
            dates_with_slots = {}
            for slot in available_slots:
                if slot.date not in dates_with_slots:
                    dates_with_slots[slot.date] = {
                        'date': slot.date.isoformat(),
                        'has_slots': True,
                        'slots_count': 1
                    }
                else:
                    dates_with_slots[slot.date]['slots_count'] += 1
            
            data = list(dates_with_slots.values())
            print(f"Devolviendo {len(data)} días con slots disponibles")
            print(f"Datos devueltos: {data}")

        return JsonResponse(data, safe=False)
        
    except Exception as e:
        print(f"Error en get_stage_availability: {str(e)}")
        return JsonResponse({
            'error': str(e),
            'details': {
                'date_param': date_param if 'date_param' in locals() else None,
                'stage_id': stage_id
            }
        }, status=500)
class StaffAvailabilityView(LoginRequiredMixin, View):
    template_name = 'visits/staff_availability.html'

    def get(self, request):
        slots = AvailabilitySlot.objects.filter(
            staff=request.user.staffprofile,
            is_active=True,
            date__gte=datetime.now().date()
        ).select_related('stage')
        
        slots_data = [{
            'id': slot.id,
            'date': slot.date.strftime('%d/%m/%Y'),
            'start_time': slot.start_time.strftime('%H:%M'),
            'end_time': slot.end_time.strftime('%H:%M'),
            'duration': slot.duration
        } for slot in slots]

        context = {
            'slots_json': json.dumps(slots_data),
            'now': datetime.now().date()
        }
        return render(request, self.template_name, context)

    def post(self, request):
        try:
            repeat_type = request.POST.get('repeat_type')
            
            if repeat_type == 'weekly':
                base_slot = AvailabilitySlot(
                    staff=request.user.staffprofile,
                    stage_id=request.POST.get('stage'),
                    month=int(request.POST.get('month')),
                    weekday=int(request.POST.get('weekday')),
                    start_time=datetime.strptime(request.POST.get('start_time'), '%H:%M').time(),
                    end_time=datetime.strptime(request.POST.get('end_time'), '%H:%M').time(),
                    duration=int(request.POST.get('duration')),
                    repeat_type='weekly'
                )
            else:
                base_slot = AvailabilitySlot(
                    staff=request.user.staffprofile,
                    stage_id=request.POST.get('stage'),
                    date=datetime.strptime(request.POST.get('date'), '%Y-%m-%d').date(),
                    start_time=datetime.strptime(request.POST.get('start_time'), '%H:%M').time(),
                    end_time=datetime.strptime(request.POST.get('end_time'), '%H:%M').time(),
                    duration=int(request.POST.get('duration')),
                    repeat_type='once'
                )

            slots = base_slot.generate_slots()
            created_slots = AvailabilitySlot.objects.bulk_create(slots)
            
            response_data = {
                'slots': [{
                    'id': slot.id,
                    'date': slot.date.strftime('%d/%m/%Y'),
                    'start_time': slot.start_time.strftime('%H:%M'),
                    'end_time': slot.end_time.strftime('%H:%M'),
                    'duration': slot.duration
                } for slot in created_slots]
            }
            
            return JsonResponse(response_data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    def delete(self, request, slot_id):
        try:
            slot = AvailabilitySlot.objects.get(
                id=slot_id,
                staff=request.user.staffprofile
            )
            slot.delete()
            return JsonResponse({'status': 'success'})
        except AvailabilitySlot.DoesNotExist:
            return JsonResponse({'error': 'Slot not found'}, status=404)

def book_appointment(request, stage_id, slot_id):
    """
    Vista para gestionar la reserva de citas:
    - GET: Muestra el formulario de reserva
    - POST: Procesa la reserva
    """
    if request.method == 'POST':
        if not request.POST.get('privacy_accepted'):
            return JsonResponse({
                'error': 'Debe aceptar la política de privacidad'
            }, status=400)
            
    stage = get_object_or_404(SchoolStage, id=stage_id)
    slot = get_object_or_404(AvailabilitySlot, id=slot_id, stage_id=stage_id, is_active=True)

    if request.method == 'POST':
        try:
            # Verificar que el slot no esté ya reservado
            if Appointment.objects.filter(
                stage=stage,
                date__date=slot.date,
                date__time__range=(slot.start_time, slot.end_time)
            ).exists():
                return JsonResponse({'error': 'Horario no disponible'}, status=400)

            # Crear la cita
            appointment = Appointment.objects.create(
                stage=stage,
                staff=slot.staff,
                visitor_name=request.POST.get('visitor_name'),
                visitor_email=request.POST.get('visitor_email'),
                visitor_phone=request.POST.get('visitor_phone'),
                date=make_aware(datetime.combine(slot.date, slot.start_time))
            )

            # Marcar slot como no disponible
            slot.is_active = False
            slot.save()

            return JsonResponse({
                'status': 'success',
                'appointment_id': appointment.id,
                'redirect_url': reverse('appointment_confirmation', kwargs={'appointment_id': appointment.id})
            })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    # GET: Mostrar formulario
    context = {
        'stage': stage,
        'slot': slot,
        'staff_name': slot.staff.user.get_full_name()
    }
    return render(request, 'visits/book_appointment.html', context)

class PrivacyPolicyView(TemplateView):
    template_name = 'visits/privacy_policy.html'

class AppointmentConfirmationView(TemplateView):
    template_name = 'visits/appointment_confirmation.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        appointment_id = kwargs.get('appointment_id')
        appointment = get_object_or_404(Appointment, id=appointment_id)
        context['appointment'] = appointment
        return context   