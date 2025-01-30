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
        for stage in SchoolStage.objects.all().prefetch_related('staffprofile_set'):
            stage_data = {
                'id': stage.id,
                'name': stage.name,
                'description': stage.description,
                'staff': [{'id': s.id, 'name': s.user.get_full_name()} 
                         for s in stage.staffprofile_set.all()]
            }
            
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
        date_param = request.GET.get('date')
        print(f"DEBUG - Parámetros recibidos: stage_id={stage_id}, date={date_param}")
        
        if date_param:
            try:
                date = datetime.strptime(date_param, '%Y-%m-%d').date()
                
                # Filtramos slots y verificamos que existan
                slots = AvailabilitySlot.objects.filter(
                    stage_id=stage_id,
                    date=date,
                    is_active=True
                ).select_related('staff', 'staff__user')

                print(f"DEBUG - Query SQL: {slots.query}")
                print(f"DEBUG - Slots encontrados: {slots.count()}")
                
                # Mostramos cada slot para debug
                for slot in slots:
                    print(f"DEBUG - Slot: id={slot.id}, date={slot.date}, time={slot.start_time}")
                
                serializer = AvailabilitySlotSerializer(slots, many=True)
                data = serializer.data
                
                print(f"DEBUG - Datos serializados: {data}")
                return JsonResponse(data, safe=False)

            except ValueError as e:
                print(f"Error parseando fecha: {e}")
                return JsonResponse([], safe=False)
        else:
            # Para vista mensual
            start_date = datetime.now().date()
            end_date = start_date + timedelta(days=90)
            
            # Obtenemos días con slots
            slots = AvailabilitySlot.objects.filter(
                stage_id=stage_id,
                date__range=(start_date, end_date),
                is_active=True
            ).values('date').distinct()
            
            print(f"DEBUG - Monthly view - Found dates count: {slots.count()}")
            
            available_dates = [{
                'date': slot['date'].isoformat(),
                'available': True
            } for slot in slots]
            
            print(f"DEBUG - Monthly view - Response data: {available_dates}")
            return JsonResponse(available_dates, safe=False)
            
    except Exception as e:
        print(f"ERROR en get_stage_availability: {str(e)}")
        import traceback
        print(f"DEBUG - Full traceback: {traceback.format_exc()}")
        return JsonResponse({'error': str(e)}, status=500)
class StaffAvailabilityView(LoginRequiredMixin, View):
    template_name = 'visits/staff_availability.html'

    def get(self, request):
        # Obtener todos los slots
        slots = AvailabilitySlot.objects.filter(
            staff=request.user.staffprofile,
            is_active=True,
            date__gte=datetime.now().date()
        ).select_related('stage')
        
        # Agrupar slots por fecha y hora
        grouped_slots = {}
        for slot in slots:
            key = (slot.date, slot.start_time, slot.end_time)
            if key not in grouped_slots:
                grouped_slots[key] = {
                    'id': slot.id,
                    'date': slot.date.strftime('%d/%m/%Y'),
                    'start_time': slot.start_time.strftime('%H:%M'),
                    'end_time': slot.end_time.strftime('%H:%M'),
                    'duration': slot.duration,
                    'stages': [slot.stage.name]
                }
            else:
                grouped_slots[key]['stages'].append(slot.stage.name)

        slots_data = list(grouped_slots.values())

        context = {
            'slots_json': json.dumps(slots_data),
            'now': datetime.now().date()
        }
        return render(request, self.template_name, context)

    def post(self, request):
        try:
            repeat_type = request.POST.get('repeat_type')
            user_profile = request.user.staffprofile
            
            # Datos base del slot
            base_slot_data = {
                'staff': user_profile,
                'start_time': datetime.strptime(request.POST.get('start_time'), '%H:%M').time(),
                'end_time': datetime.strptime(request.POST.get('end_time'), '%H:%M').time(),
                'duration': int(request.POST.get('duration')),
                'repeat_type': repeat_type,
                'is_active': True  # Aseguramos que se crea activo
            }

            if repeat_type == 'weekly':
                base_slot_data.update({
                    'month': int(request.POST.get('month')),
                    'weekday': int(request.POST.get('weekday'))
                })
            else:
                base_slot_data['date'] = datetime.strptime(request.POST.get('date'), '%Y-%m-%d').date()

            print("Creando slots para las etapas:", [stage.name for stage in user_profile.allowed_stages.all()])

            # Crear slots para cada etapa asignada al profesor
            created_slots = []
            for stage in user_profile.allowed_stages.all():
                base_slot = AvailabilitySlot(
                    **base_slot_data,
                    stage=stage
                )
                slots = base_slot.generate_slots()
                created = AvailabilitySlot.objects.bulk_create(slots)
                created_slots.extend(created)
                print(f"Creados {len(created)} slots para la etapa {stage.name}")

            print(f"Total slots creados: {len(created_slots)}")
            
            # Agrupar slots por fecha y hora para la respuesta
            grouped_slots = {}
            for slot in created_slots:
                key = (slot.date, slot.start_time, slot.end_time)
                if key not in grouped_slots:
                    grouped_slots[key] = {
                        'id': slot.id,
                        'date': slot.date.strftime('%d/%m/%Y'),
                        'start_time': slot.start_time.strftime('%H:%M'),
                        'end_time': slot.end_time.strftime('%H:%M'),
                        'duration': slot.duration,
                        'stages': [slot.stage.name]
                    }
                else:
                    grouped_slots[key]['stages'].append(slot.stage.name)
            
            response_data = {
                'slots': list(grouped_slots.values())
            }
            
            return JsonResponse(response_data)
        except Exception as e:
            print(f"Error creando slots: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)

    def delete(self, request, slot_id):
        try:
            # Obtenemos el slot a eliminar
            base_slot = get_object_or_404(AvailabilitySlot, id=slot_id, staff=request.user.staffprofile)
            
            # Eliminamos todos los slots del mismo profesor, fecha y hora
            slots_to_delete = AvailabilitySlot.objects.filter(
                staff=base_slot.staff,
                date=base_slot.date,
                start_time=base_slot.start_time,
                end_time=base_slot.end_time
            )
            
            count = slots_to_delete.delete()[0]
            print(f"Eliminados {count} slots")
            
            return JsonResponse({'status': 'success', 'deleted_count': count})
        except AvailabilitySlot.DoesNotExist:
            return JsonResponse({'error': 'Slot not found'}, status=404)
        except Exception as e:
            print(f"Error eliminando slots: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)

def book_appointment(request, stage_id, slot_id):
    stage = get_object_or_404(SchoolStage, id=stage_id)
    slot = get_object_or_404(AvailabilitySlot, id=slot_id, stage_id=stage_id, is_active=True)

    if request.method == 'POST':
        try:
            # Debug info
            print(f"DEBUG - Processing appointment for slot: {slot_id}")
            print(f"DEBUG - Date: {slot.date}, Start time: {slot.start_time}")

            # Validar teléfono (9 dígitos)
            phone = request.POST.get('visitor_phone')
            if not phone.isdigit() or len(phone) != 9:
                return JsonResponse({
                    'error': 'El número de teléfono debe contener 9 dígitos'
                }, status=400)

            # Construir datetime para la cita
            appointment_datetime = datetime.combine(slot.date, slot.start_time)
            
            # Ajustar la zona horaria si se proporciona
            timezone_offset = request.POST.get('timezone_offset')
            if timezone_offset:
                try:
                    offset_hours = int(timezone_offset) / 60
                    appointment_datetime = appointment_datetime - timedelta(hours=offset_hours)
                except (ValueError, TypeError):
                    print(f"DEBUG - Invalid timezone offset: {timezone_offset}")
                    pass

            # Verificar disponibilidad del slot
            appointment_exists = Appointment.objects.filter(
                staff=slot.staff,
                date=make_aware(appointment_datetime)
            ).exists()

            if appointment_exists:
                return JsonResponse({
                    'error': 'Horario no disponible',
                    'redirect_url': reverse('stage_booking', kwargs={'stage_id': stage_id})
                }, status=400)

            # Crear la cita
            appointment = Appointment.objects.create(
                stage=stage,
                staff=slot.staff,
                visitor_name=request.POST.get('visitor_name'),
                visitor_email=request.POST.get('visitor_email'),
                visitor_phone=phone,
                comments=request.POST.get('comments', ''),
                date=make_aware(appointment_datetime)
            )

            print(f"DEBUG - Created appointment: {appointment.id}")

            # Desactivar slots del mismo profesor
            slots_updated = AvailabilitySlot.objects.filter(
                staff=slot.staff,
                date=slot.date,
                start_time=slot.start_time
            ).update(is_active=False)

            print(f"DEBUG - Updated {slots_updated} availability slots")

            return JsonResponse({
                'status': 'success',
                'appointment_id': appointment.id,
                'redirect_url': reverse('appointment_confirmation', kwargs={'appointment_id': appointment.id})
            })

        except Exception as e:
            print(f"ERROR en book_appointment: {str(e)}")
            import traceback
            print(f"DEBUG - Full traceback: {traceback.format_exc()}")
            return JsonResponse({'error': str(e)}, status=500)

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