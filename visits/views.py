from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView, View
from rest_framework import viewsets
from django.http import JsonResponse
from datetime import datetime, timedelta, time
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.timezone import make_aware, get_current_timezone
from django.urls import reverse
import json
import logging

logger = logging.getLogger(__name__)

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


def is_slot_available(staff, datetime_start, duration):
    """Verifica disponibilidad del slot considerando citas y otros slots"""
    datetime_end = datetime_start + timedelta(minutes=duration)
    
    # Verificar solapamiento con otras citas
    overlapping_appointments = Appointment.objects.filter(
        staff=staff,
        date__lt=datetime_end,
        date__gt=datetime_start - timedelta(minutes=duration)
    ).exists()
    
    if overlapping_appointments:
        logger.warning(f"Encontrado solapamiento con citas existentes para {staff}")
        return False

    # Verificar solapamiento con otros slots
    overlapping_slots = AvailabilitySlot.objects.filter(
        staff=staff,
        date=datetime_start.date(),
        is_active=True
    ).exclude(
        start_time__gte=datetime_end.time()
    ).exclude(
        end_time__lte=datetime_start.time()
    ).exists()

    if overlapping_slots:
        logger.warning(f"Encontrado solapamiento con slots existentes para {staff}")
        return False

    return True


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'visits/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if hasattr(self.request.user, 'staffprofile'):
            context['appointments'] = Appointment.objects.filter(
                staff=self.request.user.staffprofile
            ).select_related('stage')
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
    
    def get_queryset(self):
        if hasattr(self.request.user, 'staffprofile'):
            return self.queryset.filter(staff=self.request.user.staffprofile)
        return self.queryset.none()


def staff_by_stage(request, stage_id):
    staff = StaffProfile.objects.filter(allowed_stages=stage_id)
    data = [{'id': s.id, 'name': s.user.get_full_name()} for s in staff]
    return JsonResponse(data, safe=False)


def get_stage_availability(request, stage_id):
    try:
        date_param = request.GET.get('date')
        logger.debug(f"Parámetros recibidos: stage_id={stage_id}, date={date_param}")
        
        if date_param:
            try:
                date = datetime.strptime(date_param, '%Y-%m-%d').date()
                
                # Filtrar slots y verificar que existan
                slots = AvailabilitySlot.objects.filter(
                    stage_id=stage_id,
                    date=date,
                    is_active=True,
                    start_time__gte=time(8, 0),    # No mostrar slots antes de las 8:00
                    end_time__lte=time(20, 0)       # No mostrar slots después de las 20:00
                ).select_related('staff', 'staff__user')

                logger.debug(f"Slots encontrados: {slots.count()}")
                
                serializer = AvailabilitySlotSerializer(slots, many=True)
                data = serializer.data
                
                return JsonResponse(data, safe=False)

            except ValueError as e:
                logger.error(f"Error parseando fecha: {e}")
                return JsonResponse([], safe=False)
        else:
            # Para vista mensual
            start_date = datetime.now().date()
            end_date = start_date + timedelta(days=90)
            
            # Obtenemos días con slots
            slots = AvailabilitySlot.objects.filter(
                stage_id=stage_id,
                date__range=(start_date, end_date),
                is_active=True,
                start_time__gte=time(8, 0),
                end_time__lte=time(20, 0)
            ).values('date').distinct()
            
            logger.debug(f"Vista mensual - Fechas encontradas: {slots.count()}")
            
            available_dates = [{
                'date': slot['date'].isoformat(),
                'available': True
            } for slot in slots]
            
            return JsonResponse(available_dates, safe=False)
            
    except Exception as e:
        logger.error(f"Error en get_stage_availability: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


def book_appointment(request, stage_id, slot_id):
    stage = get_object_or_404(SchoolStage, id=stage_id)
    slot = get_object_or_404(AvailabilitySlot, id=slot_id, stage_id=stage_id, is_active=True)

    if request.method == 'POST':
        try:
            logger.info(f"Procesando reserva para slot: {slot_id}")

            # Validar teléfono
            phone = request.POST.get('visitor_phone', '').strip()
            if not phone.isdigit() or len(phone) != 9:
                logger.warning(f"Teléfono inválido: {phone}")
                return JsonResponse({
                    'error': 'Se esperan 9 cifras'
                }, status=400)

            # Construir datetime para la cita sin ajustar zona horaria
            appointment_datetime = datetime.combine(slot.date, slot.start_time)
            
            logger.info(f"Fecha y hora de la cita: {appointment_datetime}")

            # Crear la cita
            appointment = Appointment.objects.create(
                stage=stage,
                staff=slot.staff,
                visitor_name=request.POST.get('visitor_name'),
                visitor_email=request.POST.get('visitor_email'),
                visitor_phone=phone,
                comments=request.POST.get('comments', ''),
                date=appointment_datetime
            )

            logger.info(f"Cita creada: {appointment.id}")

            # Desactivar TODOS los slots que coincidan con la hora de la cita
            slots_updated = AvailabilitySlot.objects.filter(
                date=slot.date,
                start_time=slot.start_time
            ).update(is_active=False)

            logger.info(f"Slots desactivados: {slots_updated}")

            return JsonResponse({
                'status': 'success',
                'appointment_id': appointment.id,
                'redirect_url': reverse('appointment_confirmation', kwargs={'appointment_id': appointment.id})
            })

        except Exception as e:
            logger.error(f"Error en book_appointment: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)

    context = {
        'stage': stage,
        'slot': slot,
        'staff_name': slot.staff.user.get_full_name()
    }
    return render(request, 'visits/book_appointment.html', context)
    stage = get_object_or_404(SchoolStage, id=stage_id)
    slot = get_object_or_404(AvailabilitySlot, id=slot_id, stage_id=stage_id, is_active=True)

    if request.method == 'POST':
        try:
            logger.info(f"Procesando reserva para slot: {slot_id}")

            # Validar teléfono
            phone = request.POST.get('visitor_phone', '').strip()
            if not phone.isdigit() or len(phone) != 9:
                logger.warning(f"Teléfono inválido: {phone}")
                return JsonResponse({
                    'error': 'Se esperan 9 cifras'
                }, status=400)

            # Construir datetime para la cita
            appointment_datetime = datetime.combine(slot.date, slot.start_time)
            appointment_datetime = make_aware(appointment_datetime, get_current_timezone())
            
            logger.info(f"Fecha y hora de la cita: {appointment_datetime}")

            # Crear la cita
            appointment = Appointment.objects.create(
                stage=stage,
                staff=slot.staff,
                visitor_name=request.POST.get('visitor_name'),
                visitor_email=request.POST.get('visitor_email'),
                visitor_phone=phone,
                comments=request.POST.get('comments', ''),
                date=appointment_datetime
            )

            logger.info(f"Cita creada: {appointment.id}")

            # Desactivar slots del mismo profesor en ese horario
            slots_updated = AvailabilitySlot.objects.filter(
                staff=slot.staff,
                date=slot.date,
                start_time=slot.start_time
            ).update(is_active=False)

            logger.info(f"Slots actualizados: {slots_updated}")

            return JsonResponse({
                'status': 'success',
                'appointment_id': appointment.id,
                'redirect_url': reverse('appointment_confirmation', kwargs={'appointment_id': appointment.id})
            })

        except Exception as e:
            logger.error(f"Error en book_appointment: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)

    context = {
        'stage': stage,
        'slot': slot,
        'staff_name': slot.staff.user.get_full_name()
    }
    return render(request, 'visits/book_appointment.html', context)
    stage = get_object_or_404(SchoolStage, id=stage_id)
    slot = get_object_or_404(AvailabilitySlot, id=slot_id, stage_id=stage_id, is_active=True)

    if request.method == 'POST':
        try:
            logger.info(f"Procesando reserva para slot: {slot_id}")

            # Validar teléfono
            phone = request.POST.get('visitor_phone', '').strip()
            if not phone.isdigit() or len(phone) != 9:
                logger.warning(f"Teléfono inválido: {phone}")
                return JsonResponse({
                    'error': 'El número de teléfono debe contener exactamente 9 dígitos'
                }, status=400)

            # Construir datetime para la cita
            appointment_datetime = datetime.combine(slot.date, slot.start_time)
            appointment_datetime = make_aware(appointment_datetime, get_current_timezone())
            
            logger.info(f"Fecha y hora de la cita: {appointment_datetime}")

            # Verificar disponibilidad del slot y solapamientos
            if not is_slot_available(slot.staff, appointment_datetime, slot.duration):
                logger.warning(f"Slot no disponible: {slot_id}")
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
                date=appointment_datetime
            )

            logger.info(f"Cita creada: {appointment.id}")

            # Desactivar slots del mismo profesor en ese horario
            slots_updated = AvailabilitySlot.objects.filter(
                staff=slot.staff,
                date=slot.date,
                start_time=slot.start_time
            ).update(is_active=False)

            logger.info(f"Slots actualizados: {slots_updated}")

            return JsonResponse({
                'status': 'success',
                'appointment_id': appointment.id,
                'redirect_url': reverse('appointment_confirmation', kwargs={'appointment_id': appointment.id})
            })

        except Exception as e:
            logger.error(f"Error en book_appointment: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)

    context = {
        'stage': stage,
        'slot': slot,
        'staff_name': slot.staff.user.get_full_name()
    }
    return render(request, 'visits/book_appointment.html', context)


class StaffAvailabilityView(LoginRequiredMixin, View):
    template_name = 'visits/staff_availability.html'

    def get(self, request):
        # Obtener todos los slots
        slots = AvailabilitySlot.objects.filter(
            staff=request.user.staffprofile,
            is_active=True,
            date__gte=datetime.now().date(),
            start_time__gte=time(8, 0),
            end_time__lte=time(20, 0)
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
            logger.info(f"Creando nuevo slot para {request.user.get_full_name()}")
            repeat_type = request.POST.get('repeat_type')
            staff_profile = request.user.staffprofile
            
            # Validar horario
            start_time = datetime.strptime(request.POST.get('start_time'), '%H:%M').time()
            end_time = datetime.strptime(request.POST.get('end_time'), '%H:%M').time()
            
            if start_time < time(8, 0) or end_time > time(20, 0):
                return JsonResponse({
                    'error': 'Los horarios deben estar entre 8:00 y 20:00'
                }, status=400)
            
            # Datos base del slot
            base_slot_data = {
                'staff': staff_profile,
                'start_time': start_time,
                'end_time': end_time,
                'duration': int(request.POST.get('duration')),
                'repeat_type': repeat_type,
                'is_active': True
            }

            if repeat_type == 'weekly':
                base_slot_data.update({
                    'month': int(request.POST.get('month')),
                    'weekday': int(request.POST.get('weekday'))
                })
            else:
                date_str = request.POST.get('date')
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                # Verificar que la fecha no sea pasada
                if date_obj < datetime.now().date():
                    return JsonResponse({
                        'error': 'No se pueden crear slots para fechas pasadas'
                    }, status=400)
                    
                base_slot_data['date'] = date_obj

            logger.info(f"Creando slots para las etapas: {[stage.name for stage in staff_profile.allowed_stages.all()]}")

            # Verificar solapamientos antes de crear (para slots 'once')
            if repeat_type == 'once':
                if staff_profile.has_overlapping_slots(
                    base_slot_data['date'], start_time, end_time):
                    return JsonResponse({
                        'error': 'Ya existen slots en este horario'
                    }, status=400)

            # Crear slots para cada etapa asignada al profesor
            created_slots = []
            for stage in staff_profile.allowed_stages.all():
                base_slot = AvailabilitySlot(
                    **base_slot_data,
                    stage=stage
                )
                slots_generated = base_slot.generate_slots()
                created = AvailabilitySlot.objects.bulk_create(slots_generated)
                created_slots.extend(created)
                logger.info(f"Creados {len(created)} slots para la etapa {stage.name}")

            logger.info(f"Total slots creados: {len(created_slots)}")
            
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
            
            return JsonResponse({'slots': list(grouped_slots.values())})
            
        except Exception as e:
            logger.error(f"Error creando slots: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)

    def delete(self, request, slot_id):
        try:
            # Obtener el slot base a eliminar
            base_slot = get_object_or_404(
                AvailabilitySlot, 
                id=slot_id, 
                staff=request.user.staffprofile
            )
            
            # No permitir eliminar slots con citas existentes
            has_appointments = Appointment.objects.filter(
                staff=base_slot.staff,
                date__date=base_slot.date,
                date__time__range=(base_slot.start_time, base_slot.end_time)
            ).exists()
            
            if has_appointments:
                logger.warning(f"Intento de eliminar slot {slot_id} con citas existentes")
                return JsonResponse({
                    'error': 'No se puede eliminar un slot con citas programadas'
                }, status=400)
            
            # Eliminar todos los slots relacionados
            slots_to_delete = AvailabilitySlot.objects.filter(
                staff=base_slot.staff,
                date=base_slot.date,
                start_time=base_slot.start_time,
                end_time=base_slot.end_time
            )
            
            count = slots_to_delete.delete()[0]
            logger.info(f"Eliminados {count} slots relacionados con {slot_id}")
            
            return JsonResponse({
                'status': 'success', 
                'deleted_count': count
            })
            
        except Exception as e:
            logger.error(f"Error eliminando slots: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)


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
