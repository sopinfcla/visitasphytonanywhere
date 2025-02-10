# ====================================
# Part 1: Imports and Base Functions
# ====================================

# Importaciones de Django
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, View
from django.http import JsonResponse
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.utils.timezone import make_aware, get_current_timezone

# Importaciones de Rest Framework
from rest_framework import viewsets

# Importaciones de Python
from datetime import datetime, timedelta, time
import calendar
import json
import logging

logger = logging.getLogger(__name__)


from .models import Appointment, SchoolStage, StaffProfile, AvailabilitySlot
from .serializers import AppointmentSerializer, AvailabilitySlotSerializer, CalendarDaySerializer

def is_slot_available(staff, datetime_start, duration):
    logger.debug(f"Comprobando disponibilidad del slot para el profesor {staff} a partir de {datetime_start} durante {duration} minutos")
    datetime_end = datetime_start + timedelta(minutes=duration)
    
    # Se verifica únicamente si ya existe una cita confirmada en ese intervalo.
    overlapping_appointments = Appointment.objects.filter(
        staff=staff,
        date__lt=datetime_end,
        date__gt=datetime_start - timedelta(minutes=duration)
    ).exists()
    
    if overlapping_appointments:
        logger.info(f"Se encontró una cita solapada para el profesor {staff}")
        return False

    return True

# [Continúa en Part 2: Basic Views]

# ====================================
# Part 2: Basic Views
# ====================================

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'visits/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if hasattr(self.request.user, 'staffprofile'):
            logger.debug(f"El usuario {self.request.user} tiene perfil de profesor. Obteniendo citas.")
            context['appointments'] = Appointment.objects.filter(
                staff=self.request.user.staffprofile
            ).select_related('stage')
        else:
            logger.debug(f"El usuario {self.request.user} no tiene perfil de profesor.")
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
                'staff': [{'id': s.id, 'name': s.user.get_full_name()} for s in stage.staffprofile_set.all()]
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
        
        logger.debug("PublicBookingView: Datos de etapas preparados para la vista")
        context['stages'] = stages
        context['stages_json'] = json.dumps(stages)
        return context

# [Continúa en Part 3: Booking Related Views]
# ====================================
# Part 3: Booking Related Views
# ====================================

class StageBookingView(TemplateView):
    template_name = 'visits/stage_booking.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stage_id = kwargs.get('stage_id')
        stage = get_object_or_404(SchoolStage, id=stage_id)
        logger.debug(f"StageBookingView para la etapa con id {stage_id}")
        context.update({
            'stage': stage,
            'stage_json': json.dumps({'id': stage.id, 'name': stage.name, 'description': stage.description})
        })
        return context


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    
    def get_queryset(self):
        if hasattr(self.request.user, 'staffprofile'):
            logger.debug(f"AppointmentViewSet: Filtrando citas para el profesor {self.request.user.staffprofile}")
            return self.queryset.filter(staff=self.request.user.staffprofile)
        logger.debug("AppointmentViewSet: No se encontró perfil de profesor, devolviendo queryset vacío")
        return self.queryset.none()


def staff_by_stage(request, stage_id):
    logger.debug(f"Obteniendo profesores para la etapa con id {stage_id}")
    staff = StaffProfile.objects.filter(allowed_stages=stage_id)
    data = [{'id': s.id, 'name': s.user.get_full_name()} for s in staff]
    return JsonResponse(data, safe=False)

# [Continúa en Part 4: Availability Functions]

# ====================================
# Part 4: Availability Functions
# ====================================

def get_stage_availability(request, stage_id):
    try:
        date_param = request.GET.get('date')
        logger.debug(f"get_stage_availability llamado con stage_id={stage_id} y fecha={date_param}")
        if date_param:
            try:
                date = datetime.strptime(date_param, '%Y-%m-%d').date()
                slots = AvailabilitySlot.objects.filter(
                    stage_id=stage_id,
                    date=date,
                    is_active=True,
                    start_time__gte=time(8, 0),
                    end_time__lte=time(20, 0)
                ).select_related('staff', 'staff__user')
                logger.debug(f"Se encontraron {slots.count()} slots para la etapa {stage_id} en {date}")
                serializer = AvailabilitySlotSerializer(slots, many=True)
                return JsonResponse(serializer.data, safe=False)
            except ValueError as e:
                logger.error(f"Error al parsear la fecha: {e}")
                return JsonResponse([], safe=False)
        else:
            start_date = datetime.now().date()
            end_date = start_date + timedelta(days=90)
            slots = AvailabilitySlot.objects.filter(
                stage_id=stage_id,
                date__range=(start_date, end_date),
                is_active=True,
                start_time__gte=time(8, 0),
                end_time__lte=time(20, 0)
            ).values('date').distinct()
            logger.debug(f"Disponibilidad mensual: Se encontraron {slots.count()} fechas distintas con slots")
            available_dates = [{'date': slot['date'].isoformat(), 'available': True} for slot in slots]
            return JsonResponse(available_dates, safe=False)
    except Exception as e:
        logger.error(f"Error en get_stage_availability: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

# [Continúa en Part 5: Booking Management]
# ====================================
# Part 5: Booking Management
# ====================================

def book_appointment(request, stage_id, slot_id):
    logger.debug(f"book_appointment llamado para stage_id {stage_id} y slot_id {slot_id}")
    stage = get_object_or_404(SchoolStage, id=stage_id)
    slot = get_object_or_404(AvailabilitySlot, id=slot_id, stage_id=stage_id, is_active=True)
    if request.method == 'POST':
        try:
            logger.info(f"Procesando reserva de cita para el slot {slot_id}")
            phone = request.POST.get('visitor_phone', '').strip()
            if not phone.isdigit() or len(phone) != 9:
                logger.warning(f"Número de teléfono inválido: {phone}")
                return JsonResponse({'error': 'El número de teléfono debe contener exactamente 9 dígitos'}, status=400)
            appointment_datetime = datetime.combine(slot.date, slot.start_time)
            appointment_datetime = make_aware(appointment_datetime, get_current_timezone())
            logger.debug(f"Datetime de la cita construido: {appointment_datetime}")
            if not is_slot_available(slot.staff, appointment_datetime, slot.duration):
                logger.warning(f"El slot {slot_id} no está disponible")
                return JsonResponse({
                    'error': 'Horario no disponible',
                    'redirect_url': reverse('stage_booking', kwargs={'stage_id': stage_id})
                }, status=400)
            appointment = Appointment.objects.create(
                stage=stage,
                staff=slot.staff,
                visitor_name=request.POST.get('visitor_name'),
                visitor_email=request.POST.get('visitor_email'),
                visitor_phone=phone,
                comments=request.POST.get('comments', ''),
                date=appointment_datetime
            )
            logger.info(f"Cita creada con id {appointment.id}")
            appointment_end = appointment_datetime + timedelta(minutes=slot.duration)
            slots_updated = AvailabilitySlot.objects.filter(
                staff=slot.staff,
                date=slot.date,
                is_active=True
            ).filter(
                start_time__lt=appointment_end.time(),
                end_time__gt=appointment_datetime.time()
            ).update(is_active=False)
            logger.debug(f"Se han desactivado {slots_updated} slots solapados para el profesor {slot.staff}")
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

# [Continúa en Part 6: Staff Availability View]

# ====================================
# Part 6: Staff Availability View
# ====================================

class StaffAvailabilityView(LoginRequiredMixin, View):
    template_name = 'visits/staff_availability.html'
    
    def get(self, request):
        logger.debug(f"Obteniendo slots de disponibilidad para el profesor {request.user.staffprofile}")
        slots = AvailabilitySlot.objects.filter(
            staff=request.user.staffprofile,
            is_active=True,
            date__gte=datetime.now().date(),
            start_time__gte=time(8, 0),
            end_time__lte=time(20, 0)
        ).select_related('stage')
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
        logger.debug("StaffAvailabilityView: Datos de disponibilidad preparados")
        return render(request, self.template_name, context)
    
    def post(self, request):
        try:
            logger.info(f"Creando nuevo slot para el profesor {request.user.get_full_name()}")
            repeat_type = request.POST.get('repeat_type')
            staff_profile = request.user.staffprofile
            start_time = datetime.strptime(request.POST.get('start_time'), '%H:%M').time()
            end_time = datetime.strptime(request.POST.get('end_time'), '%H:%M').time()
            
            # Validar horario
            if start_time < time(8, 0) or end_time > time(20, 0):
                logger.warning("Rango horario inválido para el slot")
                return JsonResponse({'error': 'Los horarios deben estar entre 8:00 y 20:00'}, status=400)
                
            # Validar solapamiento con citas existentes
            if repeat_type == 'once':
                date_str = request.POST.get('date')
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                if staff_profile.has_appointments_in_timeframe(date_obj, start_time, end_time):
                    logger.warning(f"Se encontró una cita que se solapa en {date_obj} de {start_time} a {end_time}")
                    return JsonResponse({
                        'error': 'Ya existe una cita programada en este horario. Por favor, selecciona otro horario.'
                    }, status=400)
            elif repeat_type == 'weekly':
                month = int(request.POST.get('month'))
                weekday = int(request.POST.get('weekday'))
                year = datetime.now().year
                # Verificar todas las fechas del mes para ese día de la semana
                calendar_month = calendar.monthcalendar(year, month)
                for week in calendar_month:
                    if week[weekday] != 0:
                        check_date = datetime(year, month, week[weekday]).date()
                        if check_date >= datetime.now().date():
                            if staff_profile.has_appointments_in_timeframe(check_date, start_time, end_time):
                                logger.warning(f"Se encontró una cita que se solapa en {check_date} de {start_time} a {end_time}")
                                return JsonResponse({
                                    'error': f'Ya existe una cita programada para el {check_date.strftime("%d/%m/%Y")} en este horario.'
                                }, status=400)

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
                if date_obj < datetime.now().date():
                    logger.warning("Intento de crear slot para una fecha pasada")
                    return JsonResponse({'error': 'No se pueden crear slots para fechas pasadas'}, status=400)
                base_slot_data['date'] = date_obj
            
            logger.debug(f"Creando slots para las etapas: {[stage.name for stage in staff_profile.allowed_stages.all()]}")
            if repeat_type == 'once':
                if staff_profile.has_overlapping_slots(base_slot_data['date'], start_time, end_time):
                    logger.warning("Ya existe un slot solapado en ese horario")
                    return JsonResponse({'error': 'Ya existen slots en este horario'}, status=400)
            
            created_slots = []
            for stage in staff_profile.allowed_stages.all():
                base_slot = AvailabilitySlot(**base_slot_data, stage=stage)
                slots_generated = base_slot.generate_slots()
                created = AvailabilitySlot.objects.bulk_create(slots_generated)
                created_slots.extend(created)
                logger.info(f"Se crearon {len(created)} slots para la etapa {stage.name}")
            
            logger.info(f"Total de slots creados: {len(created_slots)}")
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
            logger.error(f"Error al crear slots: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)
    
    def delete(self, request, slot_id):
        try:
            base_slot = get_object_or_404(AvailabilitySlot, id=slot_id, staff=request.user.staffprofile)
            has_appointments = Appointment.objects.filter(
                staff=base_slot.staff,
                date__date=base_slot.date,
                date__time__range=(base_slot.start_time, base_slot.end_time)
            ).exists()
            if has_appointments:
                logger.warning(f"Intento de eliminar el slot {slot_id} con citas programadas")
                return JsonResponse({'error': 'No se puede eliminar un slot con citas programadas'}, status=400)
            slots_to_delete = AvailabilitySlot.objects.filter(
                staff=base_slot.staff,
                date=base_slot.date,
                start_time=base_slot.start_time,
                end_time=base_slot.end_time
            )
            count = slots_to_delete.delete()[0]
            logger.info(f"Eliminados {count} slots relacionados con el slot {slot_id}")
            return JsonResponse({'status': 'success', 'deleted_count': count})
        except Exception as e:
            logger.error(f"Error al eliminar slots: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)

# [Continúa en Part 7: Final Views]

# ====================================
# Part 7: Final Views
# ====================================

class PrivacyPolicyView(TemplateView):
    template_name = 'visits/privacy_policy.html'


class AppointmentConfirmationView(TemplateView):
    template_name = 'visits/appointment_confirmation.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        appointment_id = kwargs.get('appointment_id')
        appointment = get_object_or_404(Appointment, id=appointment_id)
        context['appointment'] = appointment
        logger.debug(f"Confirmación de cita para la cita con id {appointment_id}")
        return context

# ====================================
# Part 8: Appointments CRUD Views
# ====================================

# Part 8: Appointments CRUD Views
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.views.generic import TemplateView, View
from django.http import JsonResponse
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class AppointmentsCRUDView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'visits/appointments_crud.html'
    
    def test_func(self):
        logger.debug(f"Checking access for user {self.request.user}")
        return self.request.user.is_staff
    
    def handle_no_permission(self):
        logger.warning(f"Access denied for user: {self.request.user}")
        messages.error(self.request, 'No tienes permisos para acceder a esta página.')
        return redirect('public_booking')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        logger.debug(f"Getting context data for user: {self.request.user}")
        
        try:
            staff_profile = self.request.user.staffprofile
            allowed_stages = list(staff_profile.allowed_stages.values('id', 'name'))
            
            context.update({
                'staff_name': self.request.user.get_full_name(),
                'allowed_stages': allowed_stages,
                'today': datetime.now().date().isoformat()
            })
            logger.info(f"Context prepared successfully for {staff_profile}")
            
        except Exception as e:
            logger.error(f"Error preparing context: {str(e)}")
            messages.warning(self.request, 'Tu perfil de staff no está configurado correctamente.')
            context.update({
                'staff_name': self.request.user.get_full_name(),
                'allowed_stages': [],
                'today': datetime.now().date().isoformat()
            })
        
        return context

class AppointmentAPIView(LoginRequiredMixin, View):
    def get(self, request, appointment_id=None):
        logger.debug(f"GET request to appointments API - User: {request.user}")
        try:
            if appointment_id:
                appointment = get_object_or_404(
                    Appointment.objects.select_related('stage'), 
                    id=appointment_id,
                    staff=request.user.staffprofile
                )
                return JsonResponse(AppointmentSerializer(appointment).data)
            
            # Base query optimizada
            queryset = Appointment.objects.select_related('stage', 'staff__user').filter(
                staff=request.user.staffprofile
            )
            
            # Paginación
            start = int(request.GET.get('start', 0))
            length = int(request.GET.get('length', 10))
            draw = int(request.GET.get('draw', 1))
            
            # Total records antes de filtrar
            total_records = queryset.count()
            logger.debug(f"Total records: {total_records}")
            
            # Ordenación
            order_column = int(request.GET.get('order[0][column]', 0))
            order_dir = request.GET.get('order[0][dir]', 'desc')
            order_columns = ['date', 'date', 'visitor_name', 'stage__name', 'status']
            
            order = f"-{order_columns[order_column]}" if order_dir == 'desc' else order_columns[order_column]
            queryset = queryset.order_by(order)
            
            # Aplicar paginación después de ordenar
            paginated_queryset = queryset[start:start + length]
            
            # Serializar datos
            serialized_data = []
            for appointment in paginated_queryset:
                serialized_data.append({
                    'id': appointment.id,
                    'date': appointment.date.isoformat() if appointment.date else None,
                    'visitor_name': appointment.visitor_name,
                    'visitor_email': appointment.visitor_email,
                    'stage_name': appointment.stage.name if appointment.stage else '',
                    'status': appointment.status
                })
            
            response_data = {
                'draw': draw,
                'recordsTotal': total_records,
                'recordsFiltered': total_records,
                'data': serialized_data
            }
            
            logger.debug(f"Sending response with {len(serialized_data)} appointments")
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"Error in appointments API: {str(e)}", exc_info=True)
            return JsonResponse({
                'draw': draw,
                'recordsTotal': 0,
                'recordsFiltered': 0,
                'data': []
            })

    def post(self, request):
        try:
            data = json.loads(request.body)
            data['staff'] = request.user.staffprofile.id
            
            serializer = AppointmentSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return JsonResponse(serializer.data)
            return JsonResponse(serializer.errors, status=400)
            
        except Exception as e:
            logger.error(f"Error creating appointment: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)

    def put(self, request, appointment_id):
        try:
            appointment = get_object_or_404(
                Appointment, 
                id=appointment_id,
                staff=request.user.staffprofile
            )
            data = json.loads(request.body)
            
            serializer = AppointmentSerializer(appointment, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return JsonResponse(serializer.data)
            return JsonResponse(serializer.errors, status=400)
            
        except Exception as e:
            logger.error(f"Error updating appointment: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)

    def delete(self, request, appointment_id):
        try:
            appointment = get_object_or_404(
                Appointment, 
                id=appointment_id,
                staff=request.user.staffprofile
            )
            appointment.delete()
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            logger.error(f"Error deleting appointment: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)