# ====================================
# Part 1: Imports and Base Functions
# ====================================

# Importaciones de Django
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import PasswordChangeView, LoginView
from django.contrib.auth.models import User
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, View
from django.http import JsonResponse
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.utils.timezone import make_aware, get_current_timezone
from django.db.models import Q
from django.db.models.functions import ExtractHour
from django.utils.timezone import is_naive, make_aware, localtime
from django.middleware.csrf import get_token
from django.db import transaction


# Importaciones de Python
from datetime import datetime, timedelta, time
import calendar
import json
import logging

logger = logging.getLogger(__name__)

# Importaciones locales
from .models import Appointment, SchoolStage, StaffProfile, AvailabilitySlot
from .serializers import AppointmentSerializer, AvailabilitySlotSerializer, CalendarDaySerializer
from .forms import StaffAuthenticationForm

# ====================================
# Part 1.1: Base Functions
# ====================================

def is_slot_available(staff, datetime_start, duration):
    """
    Comprueba si un slot de tiempo está disponible para un miembro del staff
    
    Args:
        staff (StaffProfile): Perfil del staff a comprobar
        datetime_start (datetime): Fecha y hora de inicio
        duration (int): Duración en minutos
        
    Returns:
        bool: True si el slot está disponible, False si no
    """
    logger.debug(f"Comprobando disponibilidad del slot para el profesor {staff} a partir de {datetime_start} durante {duration} minutos")
    datetime_end = datetime_start + timedelta(minutes=duration)
    
    overlapping_appointments = Appointment.objects.filter(
        staff=staff,
        date__lt=datetime_end,
        date__gt=datetime_start - timedelta(minutes=duration)
    ).exists()
    
    if overlapping_appointments:
        logger.info(f"Se encontró una cita solapada para el profesor {staff}")
        return False

    return True

# ====================================
# Part 1.2: Authentication Views
# ====================================

class StaffLoginView(LoginView):
    """
    Vista personalizada para el login del staff que usa un formulario personalizado
    y maneja la funcionalidad de remember_me
    """
    form_class = StaffAuthenticationForm
    template_name = 'visits/login.html'
    redirect_authenticated_user = True
    next_page = reverse_lazy('dashboard')
    
    def form_valid(self, form):
        """Procesa el formulario cuando es válido y maneja el remember_me"""
        remember_me = form.cleaned_data.get('remember_me', False)
        if not remember_me:
            self.request.session.set_expiry(0)
        return super().form_valid(form)
    
    def get_success_url(self):
        """Determina la URL de redirección tras un login exitoso"""
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return self.next_page
    
    def get_context_data(self, **kwargs):
        """Añade datos adicionales al contexto del template"""
        context = super().get_context_data(**kwargs)
        context['title'] = 'Acceso Staff'
        return context

# ====================================
# Part 2: Basic Views
# ====================================

class PublicBookingView(TemplateView):
    template_name = 'visits/public_booking.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Diccionario con los metadatos, incluyendo la descripción correcta.
        stages_metadata = {
            'Escuela Infantil': {
                'icon': '<i class="fas fa-baby-carriage"></i>',
                'age_range': '(0-3 años)',
                'description': 'Los primeros pasos en un mundo de aprendizaje, cariño y descubrimiento.'
            },
            'Infantil': {
                'icon': '<i class="fas fa-cubes"></i>',
                'age_range': '(3-6 años)',
                'description': 'Una etapa para crecer, jugar y explorar la creatividad en un entorno seguro y estimulante.'
            },
            'Primaria': {
                'icon': '<i class="fas fa-book-open-reader"></i>',
                'age_range': '(6-12 años)',
                'description': 'Fomentamos la curiosidad y sentamos las bases del conocimiento, los valores y la amistad.'
            },
            'Secundaria': {
                'icon': '<i class="fas fa-atom"></i>',
                'age_range': '(12-16 años)',
                'description': 'Acompañamos a los alumnos en su desarrollo académico y personal hacia la madurez.'
            },
            'Bachillerato': {
                'icon': '<i class="fas fa-user-graduate"></i>',
                'age_range': '(16-18 años)',
                'description': 'Preparamos a los estudiantes para la universidad y su futuro profesional con una base sólida.'
            },
            'Ciclos Formativos': {
                'icon': '<i class="fas fa-cogs"></i>',
                'age_range': '(Mayores de 16 años)',
                'description': 'Formación práctica y especializada para una rápida y exitosa inserción en el mundo laboral.'
            }
        }

        stages_list = []
        # Obtenemos todas las etapas de la base de datos
        all_stages_from_db = SchoolStage.objects.all()

        # Usamos enumerate para obtener un índice para la animación
        for i, stage_obj in enumerate(all_stages_from_db):
            # Empezamos con los datos del modelo
            stage_data = {
                'id': stage_obj.id,
                'name': stage_obj.name,
                'description': stage_obj.description, # Descripción por defecto de la BD
                'animation_delay': i * 100,
            }
            
            # Buscamos los metadatos para esta etapa
            metadata = stages_metadata.get(stage_obj.name, {})
            
            # Actualizamos los datos. La descripción de metadata sobreescribirá la de la BD.
            stage_data.update(metadata)
            
            stages_list.append(stage_data)
        
        context['stages'] = stages_list
        return context

class StageBookingView(TemplateView):
    template_name = 'visits/stage_booking.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stage_id = kwargs.get('stage_id')
        stage = get_object_or_404(SchoolStage, id=stage_id)
        context.update({
            'stage': stage,
            'stage_json': json.dumps({'id': stage.id, 'name': stage.name, 'description': stage.description})
        })
        return context

class StaffProfileView(LoginRequiredMixin, View):
    template_name = 'visits/staff_profile.html'

    def get(self, request):
        if not hasattr(request.user, 'staffprofile'):
            messages.error(request, 'No tienes un perfil de staff configurado.')
            return redirect('dashboard')
        
        return render(request, self.template_name, {
            'profile': request.user.staffprofile,
            'all_stages': SchoolStage.objects.all()
        })

    def post(self, request):
        try:
            profile = request.user.staffprofile
            user = request.user

            # Actualizar datos de User
            user.first_name = request.POST.get('first_name', '').strip()
            user.last_name = request.POST.get('last_name', '').strip()
            user.email = request.POST.get('email', '').strip()

            if not user.email:
                raise ValueError('El email es obligatorio')

            # Actualizar notificaciones
            profile.notify_new_appointment = request.POST.get('notify_new_appointment') == 'on'
            profile.notify_reminder = request.POST.get('notify_reminder') == 'on'

            # Actualizar etapas permitidas
            allowed_stages = request.POST.getlist('allowed_stages')
            profile.allowed_stages.set(allowed_stages)

            user.save()
            profile.save()

            messages.success(request, 'Perfil actualizado correctamente')
            return redirect('staff_profile')

        except ValueError as e:
            messages.error(request, str(e))
            return redirect('staff_profile')
        except Exception as e:
            logger.error(f"Error actualizando perfil: {str(e)}", exc_info=True)
            messages.error(request, 'Error al actualizar el perfil')
            return redirect('staff_profile')

class StaffPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'visits/staff_password_change.html'
    success_url = reverse_lazy('staff_profile')

    def form_valid(self, form):
        messages.success(self.request, 'Contraseña actualizada correctamente')
        return super().form_valid(form)

def staff_by_stage(request, stage_id):
    logger.debug(f"Obteniendo profesores para la etapa con id {stage_id}")
    staff = StaffProfile.objects.filter(allowed_stages=stage_id)
    data = [{'id': s.id, 'name': s.user.get_full_name()} for s in staff]
    return JsonResponse(data, safe=False)

# ====================================
# Part 3: Availability Functions
# ====================================

def get_stage_availability(request, stage_id):
    try:
        date_param = request.GET.get('date')
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
                serializer = AvailabilitySlotSerializer(slots, many=True)
                return JsonResponse(serializer.data, safe=False)
            except ValueError as e:
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
            available_dates = [{'date': slot['date'].isoformat(), 'available': True} for slot in slots]
            return JsonResponse(available_dates, safe=False)
    except Exception as e:
        logger.error(f"Error en get_stage_availability: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

# ====================================
# Part 4: Booking Management
# ====================================

def book_appointment(request, stage_id, slot_id):
    stage = get_object_or_404(SchoolStage, id=stage_id)
    slot = get_object_or_404(AvailabilitySlot, id=slot_id, stage_id=stage_id, is_active=True)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():  # Inicio de transacción atómica
                phone = request.POST.get('visitor_phone', '').strip()
                if not phone.isdigit() or len(phone) != 9:
                    return JsonResponse({
                        'error': 'El número de teléfono debe contener exactamente 9 dígitos'
                    }, status=400)
                
                appointment_datetime = datetime.combine(slot.date, slot.start_time)
                appointment_datetime = make_aware(appointment_datetime, get_current_timezone())
                
                # Verificar disponibilidad con bloqueo
                if Appointment.objects.select_for_update().filter(
                    staff=slot.staff,
                    date__lt=appointment_datetime + timedelta(minutes=slot.duration),
                    date__gt=appointment_datetime - timedelta(minutes=slot.duration)
                ).exists():
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
                    date=appointment_datetime,
                    duration=slot.duration,
                    comments=request.POST.get('comments', '')
                )

                # Enviar email de confirmación
                try:
                    send_appointment_confirmation(appointment)
                except Exception as e:
                    logger.error(f"Error enviando email de confirmación: {str(e)}", exc_info=True)
                    # No revertimos la creación de la cita si falla el email
                
                # Eliminar slots solapados
                appointment_end = appointment_datetime + timedelta(minutes=slot.duration)
                AvailabilitySlot.objects.filter(
                    staff=slot.staff,
                    date=slot.date
                ).filter(
                    start_time__lt=appointment_end.time(),
                    end_time__gt=appointment_datetime.time()
                ).delete()
                
                return JsonResponse({
                    'status': 'success',
                    'appointment_id': appointment.id,
                    'redirect_url': reverse('appointment_confirmation', 
                                         kwargs={'appointment_id': appointment.id})
                })
                
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    context = {
        'stage': stage,
        'slot': slot,
        'staff_name': slot.staff.user.get_full_name()
    }
    return render(request, 'visits/book_appointment.html', context)
# ====================================
# Part 5: Staff Availability
# ====================================

class StaffAvailabilityView(LoginRequiredMixin, View):
    template_name = 'visits/staff_availability.html'
    
    def get(self, request):
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
        return render(request, self.template_name, context)
    
    def post(self, request):
        try:
            staff_profile = request.user.staffprofile
            start_time = datetime.strptime(request.POST.get('start_time'), '%H:%M').time()
            end_time = datetime.strptime(request.POST.get('end_time'), '%H:%M').time()
            
            if start_time < time(8, 0) or end_time > time(20, 0):
                return JsonResponse({'error': 'Los horarios deben estar entre 8:00 y 20:00'}, status=400)
            
            base_slot_data = {
                'staff': staff_profile,
                'start_time': start_time,
                'end_time': end_time,
                'duration': int(request.POST.get('duration')),
                'repeat_type': request.POST.get('repeat_type'),
                'is_active': True
            }

            # Verificación de solapamientos según el tipo de slot
            if base_slot_data['repeat_type'] == 'weekly':
                base_slot_data.update({
                    'month': int(request.POST.get('month')),
                    'weekday': int(request.POST.get('weekday'))
                })
                
                # Para slots recurrentes, verificar todos los días del mes que coincidan
                month = base_slot_data['month']
                weekday = base_slot_data['weekday']
                year = datetime.now().year
                
                # Obtener todas las fechas del mes que coinciden con el día de la semana
                month_dates = []
                c = calendar.monthcalendar(year, month)
                for week in c:
                    if week[weekday] != 0:
                        month_dates.append(datetime(year, month, week[weekday]).date())
                
                # Verificar solapamientos para todas las fechas
                for date_to_check in month_dates:
                    # Verificar solapamiento con otros slots
                    overlapping_slots = AvailabilitySlot.objects.filter(
                        staff=staff_profile,
                        date=date_to_check,
                        is_active=True
                    ).filter(
                        Q(start_time__lt=end_time) & Q(end_time__gt=start_time)
                    ).exists()

                    if overlapping_slots:
                        return JsonResponse({
                            'error': 'Ya existen slots de disponibilidad que se solapan con este horario'
                        }, status=400)

                    # Verificar solapamiento con citas
                    start_datetime = datetime.combine(date_to_check, start_time)
                    end_datetime = datetime.combine(date_to_check, end_time)
                    
                    overlapping_appointments = Appointment.objects.filter(
                        staff=staff_profile,
                        date__range=(
                            make_aware(start_datetime),
                            make_aware(end_datetime)
                        )
                    ).exists()

                    if overlapping_appointments:
                        return JsonResponse({
                            'error': 'Hay citas programadas que se solapan con este horario'
                        }, status=400)
                    
            else:
                # Manejo de slots únicos
                date_str = request.POST.get('date')
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                if date_obj < datetime.now().date():
                    return JsonResponse({'error': 'No se pueden crear slots para fechas pasadas'}, status=400)
                base_slot_data['date'] = date_obj

                # Verificaciones para slots únicos
                overlapping_slots = AvailabilitySlot.objects.filter(
                    staff=staff_profile,
                    date=date_obj,
                    is_active=True
                ).filter(
                    Q(start_time__lt=end_time) & Q(end_time__gt=start_time)
                ).exists()

                if overlapping_slots:
                    return JsonResponse({
                        'error': 'Ya existen slots de disponibilidad que se solapan con este horario'
                    }, status=400)

                start_datetime = datetime.combine(date_obj, start_time)
                end_datetime = datetime.combine(date_obj, end_time)
                
                overlapping_appointments = Appointment.objects.filter(
                    staff=staff_profile,
                    date__range=(
                        make_aware(start_datetime),
                        make_aware(end_datetime)
                    )
                ).exists()

                if overlapping_appointments:
                    return JsonResponse({
                        'error': 'Hay citas programadas que se solapan con este horario'
                    }, status=400)

            # Crear slots si no hay solapamientos
            created_slots = []
            for stage in staff_profile.allowed_stages.all():
                base_slot = AvailabilitySlot(**base_slot_data, stage=stage)
                slots_generated = base_slot.generate_slots()
                created = AvailabilitySlot.objects.bulk_create(slots_generated)
                created_slots.extend(created)
            
            # Agrupar slots para la respuesta
            grouped_slots = {}
            for slot in created_slots:
                key = (slot.date, slot.start_time, slot.end_time)
                if key not in grouped_slots:
                    grouped_slots[key] = {
                        'id': slot.id,
                        'date': slot.date.strftime('%d/%m/%Y') if slot.date else '',
                        'start_time': slot.start_time.strftime('%H:%M'),
                        'end_time': slot.end_time.strftime('%H:%M'),
                        'duration': slot.duration,
                        'stages': [slot.stage.name]
                    }
                else:
                    grouped_slots[key]['stages'].append(slot.stage.name)
                    
            return JsonResponse({'slots': list(grouped_slots.values())})
            
        except Exception as e:
            logger.error(f"Error creating availability slots: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)
    
    def delete(self, request, slot_id=None):
        try:
            if not slot_id:
                data = json.loads(request.body)
                slot_id = data.get('slot_id')
                
            if not slot_id:
                return JsonResponse({'error': 'No se proporcionó el ID del slot'}, status=400)
                
            base_slot = get_object_or_404(AvailabilitySlot, id=slot_id, staff=request.user.staffprofile)
            has_appointments = Appointment.objects.filter(
                staff=base_slot.staff,
                date__date=base_slot.date,
                date__time__range=(base_slot.start_time, base_slot.end_time)
            ).exists()
            
            if has_appointments:
                return JsonResponse({'error': 'No se puede eliminar un slot con citas programadas'}, status=400)
                
            # Eliminar todos los slots relacionados para esa fecha y horario
            slots_to_delete = AvailabilitySlot.objects.filter(
                staff=base_slot.staff,
                date=base_slot.date,
                start_time=base_slot.start_time,
                end_time=base_slot.end_time
            )
            count = slots_to_delete.delete()[0]
            return JsonResponse({'status': 'success', 'deleted_count': count})
            
        except Exception as e:
            logger.error(f"Error deleting slot {slot_id}: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)
        
# ====================================
# Part 6: Appointments CRUD & Basic Views
# ====================================

class AppointmentsCRUDView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'visits/appointments_crud.html'
    
    def test_func(self):
        return hasattr(self.request.user, 'staffprofile')
    
    def handle_no_permission(self):
        messages.error(self.request, 'No tienes permisos para acceder a esta página.')
        return redirect('public_booking')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            staff_profile = self.request.user.staffprofile
            allowed_stages = list(staff_profile.allowed_stages.values('id', 'name'))
            
            # Generar horas disponibles (8:00 - 20:00)
            available_hours = []
            for hour in range(8, 21):
                for minute in [0, 15, 30, 45]:
                    if hour < 20 or (hour == 20 and minute == 0):
                        time_str = f"{hour:02d}:{minute:02d}"
                        available_hours.append({
                            'value': time_str,
                            'label': time_str
                        })
            
            context.update({
                'staff_name': self.request.user.get_full_name(),
                'allowed_stages': allowed_stages,
                'today': datetime.now().date().isoformat(),
                'available_hours': available_hours
            })
        except Exception as e:
            logger.error(f"Error preparing context: {str(e)}")
            messages.warning(self.request, 'Tu perfil de staff no está configurado correctamente.')
            context.update({
                'staff_name': self.request.user.get_full_name(),
                'allowed_stages': [],
                'today': datetime.now().date().isoformat(),
                'available_hours': []
            })
        return context

class AppointmentAPIView(LoginRequiredMixin, View):
    def get(self, request, appointment_id=None):
        try:
            is_supervisor = request.user.groups.filter(name='Supervisor').exists()
            
            if appointment_id:
                # Construir query base
                appointment_query = Appointment.objects.select_related('stage')
                
                # Si es supervisor, permitir ver todas las citas
                if is_supervisor:
                    appointment = get_object_or_404(appointment_query, id=appointment_id)
                else:
                    appointment = get_object_or_404(
                        appointment_query, 
                        id=appointment_id,
                        staff=request.user.staffprofile
                    )
                
                serializer = AppointmentSerializer(appointment)
                response_data = serializer.data
                response_data['duration'] = appointment.duration
                return JsonResponse(response_data)

            # Para listados, usar el mismo enfoque de permisos
            queryset = Appointment.objects.select_related('stage', 'staff__user')
            if not is_supervisor:
                queryset = queryset.filter(staff=request.user.staffprofile)

            search = request.GET.get('search', '').strip()
            if search:
                queryset = queryset.filter(
                    Q(visitor_name__icontains=search) |
                    Q(visitor_email__icontains=search) |
                    Q(visitor_phone__icontains=search) |
                    Q(stage__name__icontains=search)
                )

            stage = request.GET.get('stage')
            date = request.GET.get('date')
            status = request.GET.get('status')
            staff_id = request.GET.get('staff_id')

            if stage:
                queryset = queryset.filter(stage_id=stage)
            if date:
                queryset = queryset.filter(date__date=date)
            if status:
                queryset = queryset.filter(status=status)
            if staff_id and is_supervisor and staff_id.isdigit():
                queryset = queryset.filter(staff_id=staff_id)

            total_records = queryset.count()
            
            order_column = request.GET.get('order[0][column]', '0')
            order_dir = request.GET.get('order[0][dir]', 'desc')
            order_columns = ['date', 'date', 'visitor_name', 'stage__name', 'status']
            
            if order_column and order_column.isdigit():
                order_col_num = int(order_column)
                if order_col_num < len(order_columns):
                    order = f"-{order_columns[order_col_num]}" if order_dir == 'desc' else order_columns[order_col_num]
                    queryset = queryset.order_by(order)

            start = int(request.GET.get('start', 0))
            length = int(request.GET.get('length', 10))
            
            paginated_queryset = queryset[start:start + length]

            appointments = []
            for appointment in paginated_queryset:
                appointments.append({
                    'id': appointment.id,
                    'date': appointment.date.isoformat() if appointment.date else None,
                    'visitor_name': appointment.visitor_name,
                    'visitor_email': appointment.visitor_email,
                    'visitor_phone': appointment.visitor_phone,
                    'stage': appointment.stage.id if appointment.stage else None,
                    'stage_name': appointment.stage.name if appointment.stage else '',
                    'status': appointment.status,
                    'duration': appointment.duration,
                    'staff_id': appointment.staff.id,
                    'staff_name': appointment.staff.user.get_full_name()
                })

            return JsonResponse({
                'draw': int(request.GET.get('draw', 1)),
                'recordsTotal': total_records,
                'recordsFiltered': total_records,
                'data': appointments
            })

        except Exception as e:
            logger.error(f"Error in appointments API: {str(e)}", exc_info=True)
            return JsonResponse({
                'draw': int(request.GET.get('draw', 1)),
                'recordsTotal': 0,
                'recordsFiltered': 0,
                'data': [],
                'error': str(e)
            }, status=500)

    def post(self, request):
        try:
            # 1. Preparar los datos
            data = json.loads(request.body)
            logger.debug(f"Received POST data: {data}")

            # 2. Asignar staff_id (antes de la validación)
            is_supervisor = request.user.groups.filter(name='Supervisor').exists()
            if not is_supervisor:
                data['staff'] = request.user.staffprofile.id
            else:
                if 'staff' not in data:
                    data['staff'] = request.user.staffprofile.id

            # 3. Validar y procesar fecha
            try:
                date_str = data.get('date', '')
                appointment_date = make_aware(datetime.fromisoformat(date_str))
                data['date'] = appointment_date
            except ValueError as e:
                logger.error(f"Error parsing date: {str(e)}")
                return JsonResponse({'error': 'Formato de fecha inválido'}, status=400)

            # 4. Verificar solapamientos
            staff_id = data['staff']  # Ahora podemos usar data['staff'] con seguridad
            overlap = Appointment.objects.filter(
                staff_id=staff_id,
                date__lt=appointment_date + timedelta(minutes=data.get('duration', 60)),
                date__gt=appointment_date - timedelta(minutes=data.get('duration', 60))
            ).exists()

            if overlap:
                return JsonResponse({
                    'error': 'Ya existe una cita en este horario'
                }, status=400)

            # 5. Crear la cita
            serializer = AppointmentSerializer(data=data)
            if serializer.is_valid():
                appointment = serializer.save()
                logger.info(f"Created appointment: {appointment.id}")
                
                # 6. Eliminar slots solapados
                appointment_end = appointment.date + timedelta(minutes=appointment.duration)
                AvailabilitySlot.objects.filter(
                    staff_id=staff_id,
                    date=appointment.date.date(),
                    start_time__lt=appointment_end.time(),
                    end_time__gt=appointment.date.time()
                ).delete()
                logger.info(f"Deleted overlapping slots for appointment: {appointment.id}")
                
                response_data = serializer.data
                response_data['duration'] = appointment.duration
                return JsonResponse(response_data)
            
            logger.warning(f"Invalid appointment data: {serializer.errors}")
            return JsonResponse(serializer.errors, status=400)
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            return JsonResponse({'error': 'Datos JSON inválidos'}, status=400)
        except Exception as e:
            logger.error(f"Error creating appointment: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)

    def put(self, request, appointment_id):
        try:
            is_supervisor = request.user.groups.filter(name='Supervisor').exists()
            
            # Permitir que los supervisores editen cualquier cita
            if is_supervisor:
                appointment = get_object_or_404(Appointment, id=appointment_id)
            else:
                appointment = get_object_or_404(
                    Appointment, 
                    id=appointment_id,
                    staff=request.user.staffprofile
                )

            data = json.loads(request.body)
            logger.debug(f"Received PUT data for appointment {appointment_id}: {data}")

            if not is_supervisor:
                data['staff'] = request.user.staffprofile.id

            # Procesar fecha si se proporciona
            if 'date' in data:
                try:
                    appointment_date = make_aware(datetime.fromisoformat(data['date']))
                    data['date'] = appointment_date
                except ValueError as e:
                    logger.error(f"Error parsing date: {str(e)}")
                    return JsonResponse({'error': 'Formato de fecha inválido'}, status=400)

            # Validar duración
            if 'duration' in data:
                duration = data['duration']
                if not isinstance(duration, int) or duration not in [15, 30, 45, 60]:
                    return JsonResponse({'error': 'Duración inválida'}, status=400)

            # Verificar solapamientos si la fecha cambia
            if 'date' in data:
                staff_id = data.get('staff', appointment.staff_id)
                overlap = Appointment.objects.filter(
                    staff_id=staff_id,
                    date__lt=data['date'] + timedelta(minutes=data.get('duration', appointment.duration)),
                    date__gt=data['date'] - timedelta(minutes=data.get('duration', appointment.duration))
                ).exclude(id=appointment_id).exists()

                if overlap:
                    return JsonResponse({
                        'error': 'Ya existe una cita en este horario'
                    }, status=400)

            serializer = AppointmentSerializer(appointment, data=data, partial=True)
            if serializer.is_valid():
                updated_appointment = serializer.save()
                logger.info(f"Updated appointment: {appointment_id}")
                
                # Eliminar slots solapados
                appointment_end = updated_appointment.date + timedelta(minutes=updated_appointment.duration)
                AvailabilitySlot.objects.filter(
                    staff_id=staff_id,
                    date=updated_appointment.date.date(),
                    start_time__lt=appointment_end.time(),
                    end_time__gt=updated_appointment.date.time()
                ).delete()
                logger.info(f"Deleted overlapping slots for updated appointment: {appointment_id}")
                
                response_data = serializer.data
                response_data['duration'] = updated_appointment.duration
                return JsonResponse(response_data)

            logger.warning(f"Invalid update data: {serializer.errors}")
            return JsonResponse(serializer.errors, status=400)

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            return JsonResponse({'error': 'Datos JSON inválidos'}, status=400)
        except Exception as e:
            logger.error(f"Error updating appointment: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)

    def delete(self, request, appointment_id):
        try:
            is_supervisor = request.user.groups.filter(name='Supervisor').exists()
            
            # Permitir que los supervisores eliminen cualquier cita
            if is_supervisor:
                appointment = get_object_or_404(Appointment, id=appointment_id)
            else:
                appointment = get_object_or_404(
                    Appointment, 
                    id=appointment_id,
                    staff=request.user.staffprofile
                )

            appointment.delete()
            logger.info(f"Deleted appointment: {appointment_id}")
            return JsonResponse({'status': 'success'})

        except Exception as e:
            logger.error(f"Error deleting appointment: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)

class PrivacyPolicyView(TemplateView):
    template_name = 'visits/privacy_policy.html'

class AppointmentConfirmationView(TemplateView):
    template_name = 'visits/appointment_confirmation.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        appointment_id = kwargs.get('appointment_id')
        appointment = get_object_or_404(
            Appointment.objects.select_related('stage', 'staff', 'staff__user'),
            id=appointment_id
        )
        context.update({
            'appointment': appointment,
            'staff_name': appointment.staff.user.get_full_name(),
            'stage_name': appointment.stage.name,
            'date': appointment.date.strftime('%d/%m/%Y'),
            'time': appointment.date.strftime('%H:%M'),
            'duration': appointment.duration
        })
        return context
    
# ====================================
# Part 7: Dashboard Views
# ====================================

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, View
from django.http import JsonResponse
from django.db.models import Count
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

from django.utils.timezone import is_naive, make_aware, localtime
from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from datetime import datetime, timedelta
import logging
from .models import Appointment


# ====================================
# Part 7: Dashboard Views
# ====================================

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'visits/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if hasattr(self.request.user, 'staffprofile'):
            staff_profile = self.request.user.staffprofile
            # Verificar si el usuario pertenece al grupo Supervisor
            is_supervisor = self.request.user.groups.filter(name='Supervisor').exists()
            
            # Solo incluir lista de staff para supervisores
            if is_supervisor:
                context['staff_list'] = StaffProfile.objects.exclude(
                    id=staff_profile.id
                ).select_related('user').all()
            
            # Citas del usuario actual
            context['appointments'] = Appointment.objects.filter(
                staff=staff_profile
            ).select_related('stage')

            # Generar horas disponibles (8:00 - 20:00)
            available_hours = []
            for hour in range(8, 21):
                for minute in ['00', '15', '30', '45']:
                    if hour == 20 and minute != '00':
                        continue
                    time_str = f"{hour:02d}:{minute}"
                    available_hours.append({
                        'value': time_str,
                        'label': time_str
                    })
            context['available_hours'] = available_hours
            
            # Añadir configuración JavaScript
            context.update({
                'is_supervisor': is_supervisor,
                'dashboard_config': {
                    'isSupervisor': is_supervisor,
                    'staffId': staff_profile.id,
                    'csrfToken': get_token(self.request),
                    'apiUrl': reverse('api_appointments'),
                    'calendarUrl': reverse('dashboard_calendar'),
                    'statsUrl': reverse('dashboard_stats')
                }
            })
        else:
            context.update({
                'appointments': Appointment.objects.none(),
                'is_supervisor': False,
                'available_hours': [],
                'dashboard_config': {}
            })

        return context

class DashboardCalendarView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            if not hasattr(request.user, 'staffprofile'):
                return JsonResponse({'error': 'Perfil no encontrado'}, status=404)
                
            staff_profile = request.user.staffprofile
            staff_id = request.GET.get('staff_id')
            start_str = request.GET.get('start')
            end_str = request.GET.get('end')
            is_supervisor = request.user.groups.filter(name='Supervisor').exists()

            # Validar y procesar fechas
            try:
                start = self._parse_date(start_str)
                end = self._parse_date(end_str)
            except ValueError as e:
                return JsonResponse({'error': str(e)}, status=400)

            # Construir query base
            appointments_query = Appointment.objects.select_related('stage', 'staff__user')
            
            # Aplicar filtros según permisos
            if is_supervisor:
                if staff_id == 'global':
                    pass  # No filtrar
                elif staff_id and staff_id.isdigit():
                    appointments_query = appointments_query.filter(staff_id=int(staff_id))
                else:
                    appointments_query = appointments_query.filter(staff=staff_profile)
            else:
                appointments_query = appointments_query.filter(staff=staff_profile)

            # Filtrar por rango de fechas
            appointments = appointments_query.filter(
                date__range=(start, end)
            ).order_by('date')

            # Formatear eventos
            events = []
            for apt in appointments:
                end_time = apt.date + timedelta(minutes=apt.duration)
                event = {
                    'id': apt.id,
                    'title': f'{apt.visitor_name}',
                    'start': apt.date.isoformat(),
                    'end': end_time.isoformat(),
                    'backgroundColor': self._get_status_color(apt.status),
                    'borderColor': self._get_status_color(apt.status),
                    'extendedProps': {
                        'staffId': apt.staff.id,
                        'status': apt.status,
                        'stage': apt.stage.name,
                        'visitor_name': apt.visitor_name,
                        'visitor_email': apt.visitor_email,
                        'visitor_phone': apt.visitor_phone,
                        'duration': apt.duration,
                        'staff_name': apt.staff.user.get_full_name()
                    }
                }
                events.append(event)

            return JsonResponse(events, safe=False)

        except Exception as e:
            logger.error(f"Error obteniendo eventos del calendario: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)

    def _parse_date(self, date_str):
        try:
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            if is_naive(date):
                date = make_aware(date)
            return localtime(date)
        except ValueError:
            raise ValueError('Formato de fecha inválido')

    def _get_status_color(self, status):
        return {
            'pending': '#ffc107',
            'completed': '#198754',
            'cancelled': '#dc3545',
        }.get(status, '#6c757d')

class DashboardStatsView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            if not hasattr(request.user, 'staffprofile'):
                return JsonResponse({'error': 'Perfil no encontrado'}, status=404)
                
            staff_profile = request.user.staffprofile
            staff_id = request.GET.get('staff_id')
            is_supervisor = request.user.groups.filter(name='Supervisor').exists()
            
            today = timezone.now()
            today_start = timezone.localtime(today).replace(hour=0, minute=0, second=0)
            today_end = today_start + timedelta(days=1)
            
            # Determinar el queryset base según los permisos
            base_queryset = Appointment.objects.select_related('stage', 'staff__user')
            
            if is_supervisor:
                if staff_id == 'global':
                    pass  # No filtrar
                elif staff_id and staff_id.isdigit():
                    base_queryset = base_queryset.filter(staff_id=int(staff_id))
                else:
                    base_queryset = base_queryset.filter(staff=staff_profile)
            else:
                base_queryset = base_queryset.filter(staff=staff_profile)

            # Estadísticas
            stats = {
                'today_count': base_queryset.filter(
                    date__range=(today_start, today_end)
                ).count(),
                
                'confirmed_count': base_queryset.filter(
                    status='completed'
                ).count(),
                
                'pending_count': base_queryset.filter(
                    status='pending',
                    date__gte=today_start
                ).count(),
                
                'stages_count': staff_profile.allowed_stages.count()
            }

            # Estadísticas por etapa 
            stats_by_stage = []
            stages_queryset = staff_profile.allowed_stages.all() if not is_supervisor else SchoolStage.objects.all()
            
            for stage in stages_queryset:
                appointments = base_queryset.filter(stage=stage)
                stats_by_stage.append({
                    'stage_name': stage.name,
                    'total': appointments.count(),
                    'pending': appointments.filter(status='pending').count(),
                    'completed': appointments.filter(status='completed').count(),
                    'cancelled': appointments.filter(status='cancelled').count()
                })

            # Horas más populares
            popular_hours = (
                base_queryset
                .filter(date__gte=today_start)
                .annotate(
                    hour=ExtractHour('date', tzinfo=timezone.get_current_timezone())
                )
                .values('hour')
                .annotate(count=Count('id'))
                .order_by('-count')[:5]
            )

            # Próximas citas
            upcoming = (
                base_queryset
                .filter(
                    date__gte=today,
                    status='pending'
                )
                .order_by('date')[:5]
            )

            response_data = {
                'stats_by_stage': stats_by_stage,
                'popular_hours': list(popular_hours),
                'upcoming_appointments': [
                    {
                        'id': apt.id,
                        'visitor_name': apt.visitor_name,
                        'stage': apt.stage.name,
                        'date': timezone.localtime(apt.date).isoformat(),
                        'time': timezone.localtime(apt.date).strftime('%H:%M'),
                        'status': apt.status,
                        'staff_name': apt.staff.user.get_full_name()
                    } for apt in upcoming
                ],
                **stats
            }

            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)
        
# ====================================
# Part 8: Export Functions
# ====================================

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io
import xlsxwriter
import logging

logger = logging.getLogger(__name__)

class AppointmentExportView(LoginRequiredMixin, View):
    def get_appointment_data(self, appointment_id=None):
        """Obtiene los datos formateados de las citas"""
        if appointment_id:
            appointments = Appointment.objects.filter(id=appointment_id)
        else:
            appointments = Appointment.objects.filter(staff=self.request.user.staffprofile)
        
        # Aplicar filtros si existen
        stage = self.request.GET.get('stage')
        date = self.request.GET.get('date')
        status = self.request.GET.get('status')
        
        if stage:
            appointments = appointments.filter(stage_id=stage)
        if date:
            appointments = appointments.filter(date__date=date)
        if status:
            appointments = appointments.filter(status=status)
            
        return appointments

    def generate_pdf(self, appointment_id=None):
        """Genera un PDF con los datos de la(s) cita(s)"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=letter,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        story = []
        styles = getSampleStyleSheet()
        
        # Estilo personalizado para el título
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1  # Centrado
        )
        
        # Añadir título
        title = "Informe de Cita" if appointment_id else "Informe de Citas"
        story.append(Paragraph(title, title_style))
        
        # Añadir fecha de generación
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.gray,
            alignment=1  # Centrado
        )
        story.append(Paragraph(f"Generado el {timezone.now().strftime('%d/%m/%Y %H:%M')}", date_style))
        story.append(Spacer(1, 20))

        appointments = self.get_appointment_data(appointment_id)
        
        if appointment_id:
            # Para una sola cita, mostrar todos los detalles
            appointment = appointments.first()
            data = [
                ["Información de la Cita", ""],
                ["Visitante:", appointment.visitor_name],
                ["Email:", appointment.visitor_email],
                ["Teléfono:", appointment.visitor_phone],
                ["Etapa:", appointment.stage.name],
                ["Fecha:", appointment.date.strftime("%d/%m/%Y")],
                ["Hora:", appointment.date.strftime("%H:%M")],
                ["Estado:", dict(Appointment.STATUS_CHOICES)[appointment.status]],
                ["Duración:", f"{appointment.duration} minutos"],
                ["Comentarios:", appointment.comments or ""],
                ["Notas:", appointment.notes or ""]
            ]
            
            # Estilo de tabla detallada
            table_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f2f2f2')),
                ('SPAN', (0, 0), (1, 0)),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ])
        else:
            # Para múltiples citas, formato de lista
            data = [["Fecha", "Hora", "Visitante", "Etapa", "Estado"]]
            for apt in appointments:
                data.append([
                    apt.date.strftime("%d/%m/%Y"),
                    apt.date.strftime("%H:%M"),
                    apt.visitor_name,
                    apt.stage.name,
                    dict(Appointment.STATUS_CHOICES)[apt.status]
                ])
            
            # Estilo de tabla lista
            table_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f2f2f2')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ])

        # Calcular anchos de columna según el tipo de tabla
        if appointment_id:
            col_widths = [2.5*inch, 4*inch]
        else:
            col_widths = [1.2*inch, 1*inch, 2*inch, 1.8*inch, 1.5*inch]
        
        table = Table(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(table_style)
        
        story.append(table)
        
        # Agregar pie de página
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.gray,
            alignment=1
        )
        story.append(Spacer(1, 20))
        story.append(Paragraph("Documento generado automáticamente por el sistema de gestión de citas", footer_style))
        
        doc.build(story)
        pdf = buffer.getvalue()
        buffer.close()
        return pdf

    def generate_excel(self):
        """Genera un archivo Excel con los datos filtrados"""
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet()

        # Estilos
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4B5563',
            'color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        cell_format = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'border': 1
        })
        
        # Encabezados
        headers = ['Fecha', 'Hora', 'Visitante', 'Email', 'Teléfono', 'Etapa', 'Estado', 'Duración', 'Comentarios']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
            worksheet.set_column(col, col, 15)  # Ancho de columna
        
        # Datos
        appointments = self.get_appointment_data()
        for row, apt in enumerate(appointments, start=1):
            data = [
                apt.date.strftime("%d/%m/%Y"),
                apt.date.strftime("%H:%M"),
                apt.visitor_name,
                apt.visitor_email,
                apt.visitor_phone,
                apt.stage.name,
                dict(Appointment.STATUS_CHOICES)[apt.status],
                f"{apt.duration} min",
                apt.comments or ""
            ]
            for col, value in enumerate(data):
                worksheet.write(row, col, value, cell_format)
        
        workbook.close()
        excel_data = output.getvalue()
        output.close()
        return excel_data

    def get(self, request, format=None, appointment_id=None):
        try:
            export_type = request.GET.get('type', 'pdf')
            
            if export_type == 'pdf':
                response = HttpResponse(content_type='application/pdf')
                filename = f"cita_{appointment_id}.pdf" if appointment_id else "citas.pdf"
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                response.write(self.generate_pdf(appointment_id))
            else:  # excel
                response = HttpResponse(
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                response['Content-Disposition'] = 'attachment; filename="citas.xlsx"'
                response.write(self.generate_excel())
            
            return response
        except Exception as e:
            logger.error(f"Error generando exportación: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)