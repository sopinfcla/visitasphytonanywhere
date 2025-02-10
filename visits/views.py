# ====================================
# Part 1: Imports and Base Functions
# ====================================

# Importaciones de Django
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, View
from django.http import JsonResponse
from django.urls import reverse
from django.contrib import messages
from django.utils.timezone import make_aware, get_current_timezone

# Importaciones de Python
from datetime import datetime, timedelta, time
import calendar
import json
import logging

logger = logging.getLogger(__name__)

# Importaciones locales
from .models import Appointment, SchoolStage, StaffProfile, AvailabilitySlot
from .serializers import AppointmentSerializer, AvailabilitySlotSerializer, CalendarDaySerializer

def is_slot_available(staff, datetime_start, duration):
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
# Part 2: Basic Views
# ====================================

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
            'stage_json': json.dumps({'id': stage.id, 'name': stage.name, 'description': stage.description})
        })
        return context

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
            phone = request.POST.get('visitor_phone', '').strip()
            if not phone.isdigit() or len(phone) != 9:
                return JsonResponse({'error': 'El número de teléfono debe contener exactamente 9 dígitos'}, status=400)
            
            appointment_datetime = datetime.combine(slot.date, slot.start_time)
            appointment_datetime = make_aware(appointment_datetime, get_current_timezone())
            
            if not is_slot_available(slot.staff, appointment_datetime, slot.duration):
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
            
            appointment_end = appointment_datetime + timedelta(minutes=slot.duration)
            slots_updated = AvailabilitySlot.objects.filter(
                staff=slot.staff,
                date=slot.date,
                is_active=True
            ).filter(
                start_time__lt=appointment_end.time(),
                end_time__gt=appointment_datetime.time()
            ).update(is_active=False)
            
            return JsonResponse({
                'status': 'success',
                'appointment_id': appointment.id,
                'redirect_url': reverse('appointment_confirmation', kwargs={'appointment_id': appointment.id})
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
            
            if base_slot_data['repeat_type'] == 'weekly':
                base_slot_data.update({
                    'month': int(request.POST.get('month')),
                    'weekday': int(request.POST.get('weekday'))
                })
            else:
                date_str = request.POST.get('date')
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                if date_obj < datetime.now().date():
                    return JsonResponse({'error': 'No se pueden crear slots para fechas pasadas'}, status=400)
                base_slot_data['date'] = date_obj
            
            created_slots = []
            for stage in staff_profile.allowed_stages.all():
                base_slot = AvailabilitySlot(**base_slot_data, stage=stage)
                slots_generated = base_slot.generate_slots()
                created = AvailabilitySlot.objects.bulk_create(slots_generated)
                created_slots.extend(created)
            
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
                return JsonResponse({'error': 'No se puede eliminar un slot con citas programadas'}, status=400)
                
            slots_to_delete = AvailabilitySlot.objects.filter(
                staff=base_slot.staff,
                date=base_slot.date,
                start_time=base_slot.start_time,
                end_time=base_slot.end_time
            )
            count = slots_to_delete.delete()[0]
            return JsonResponse({'status': 'success', 'deleted_count': count})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

# ====================================
# Part 6: Appointments CRUD
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
            context.update({
                'staff_name': self.request.user.get_full_name(),
                'allowed_stages': allowed_stages,
                'today': datetime.now().date().isoformat()
            })
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
        try:
            if appointment_id:
                appointment = get_object_or_404(
                    Appointment.objects.select_related('stage'), 
                    id=appointment_id,
                    staff=request.user.staffprofile
                )
                return JsonResponse(AppointmentSerializer(appointment).data)
            
            # Base query
            queryset = Appointment.objects.select_related('stage', 'staff__user').filter(
                staff=request.user.staffprofile
            )
            
            # Filtros
            stage = request.GET.get('stage')
            date = request.GET.get('date')
            status = request.GET.get('status')
            
            if stage:
                queryset = queryset.filter(stage_id=stage)
            if date:
                queryset = queryset.filter(date__date=date)
            if status:
                queryset = queryset.filter(status=status)
            
            # Paginación
            start = int(request.GET.get('start', 0))
            length = int(request.GET.get('length', 10))
            draw = int(request.GET.get('draw', 1))
            
            # Total records antes de filtrar
            total_records = queryset.count()
            
            # Ordenación
            order_column = int(request.GET.get('order[0][column]', 0))
            order_dir = request.GET.get('order[0][dir]', 'desc')
            order_columns = ['date', 'date', 'visitor_name', 'stage__name', 'status']
            
            if order_column < len(order_columns):
                order = f"-{order_columns[order_column]}" if order_dir == 'desc' else order_columns[order_column]
                queryset = queryset.order_by(order)
            
            paginated_queryset = queryset[start:start + length]
            
            # Serializar datos
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
                    'status': appointment.status
                })
            
            response_data = {
                'draw': draw,
                'recordsTotal': total_records,
                'recordsFiltered': total_records,
                'data': appointments
            }
            
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"Error in appointments API: {str(e)}", exc_info=True)
            return JsonResponse({
                'draw': draw if 'draw' in locals() else 1,
                'recordsTotal': 0,
                'recordsFiltered': 0,
                'data': [],
                'error': str(e)
            }, status=500)

    def post(self, request):
        try:
            data = json.loads(request.body)
            data['staff'] = request.user.staffprofile.id
            
            # Convertir la fecha string a datetime
            if 'date' in data:
                data['date'] = make_aware(datetime.fromisoformat(data['date']))
            
            serializer = AppointmentSerializer(data=data)
            if serializer.is_valid():
                appointment = serializer.save()
                logger.info(f"Created appointment: {appointment.id}")
                return JsonResponse(serializer.data)
            
            logger.warning(f"Invalid appointment data: {serializer.errors}")
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
            
            # Asegurar que no se cambie el staff
            data['staff'] = request.user.staffprofile.id
            
            # Convertir la fecha string a datetime
            if 'date' in data:
                data['date'] = make_aware(datetime.fromisoformat(data['date']))
            
            serializer = AppointmentSerializer(appointment, data=data, partial=True)
            if serializer.is_valid():
                updated_appointment = serializer.save()
                logger.info(f"Updated appointment: {appointment_id}")
                return JsonResponse(serializer.data)
            
            logger.warning(f"Invalid update data for appointment {appointment_id}: {serializer.errors}")
            return JsonResponse(serializer.errors, status=400)
            
        except Exception as e:
            logger.error(f"Error updating appointment {appointment_id}: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)

    def delete(self, request, appointment_id):
        try:
            appointment = get_object_or_404(
                Appointment, 
                id=appointment_id,
                staff=request.user.staffprofile
            )
            appointment.delete()
            logger.info(f"Deleted appointment: {appointment_id}")
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            logger.error(f"Error deleting appointment {appointment_id}: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)

# ====================================
# Part 7: Basic Views
# ====================================

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
            'time': appointment.date.strftime('%H:%M')
        })
        return context

# ====================================
# Part 8: Appointments CRUD Views 
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
            context.update({
                'staff_name': self.request.user.get_full_name(),
                'allowed_stages': allowed_stages,
                'today': datetime.now().date().isoformat()
            })
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
        try:
            if appointment_id:
                appointment = get_object_or_404(
                    Appointment.objects.select_related('stage'), 
                    id=appointment_id,
                    staff=request.user.staffprofile
                )
                return JsonResponse(AppointmentSerializer(appointment).data)

            # Base query
            queryset = Appointment.objects.select_related('stage', 'staff__user').filter(
                staff=request.user.staffprofile
            )

            # Búsqueda global
            search = request.GET.get('search')
            if search:
                from django.db.models import Q
                queryset = queryset.filter(
                    Q(visitor_name__icontains=search) |
                    Q(visitor_email__icontains=search) |
                    Q(visitor_phone__icontains=search) |
                    Q(stage__name__icontains=search)
                )

            # Filtros específicos
            stage = request.GET.get('stage')
            date = request.GET.get('date')
            status = request.GET.get('status')

            if stage:
                queryset = queryset.filter(stage_id=stage)
            if date:
                queryset = queryset.filter(date__date=date)
            if status:
                queryset = queryset.filter(status=status)

            # Paginación
            start = int(request.GET.get('start', 0))
            length = int(request.GET.get('length', 10))
            draw = int(request.GET.get('draw', 1))

            # Total records antes de filtrar
            total_records = queryset.count()
            filtered_records = queryset.count()

            # Ordenación
            order_column = int(request.GET.get('order[0][column]', 0))
            order_dir = request.GET.get('order[0][dir]', 'desc')
            order_columns = ['date', 'visitor_name', 'stage__name', 'status']

            if order_column < len(order_columns):
                order = f"-{order_columns[order_column]}" if order_dir == 'desc' else order_columns[order_column]
                queryset = queryset.order_by(order)

            paginated_queryset = queryset[start:start + length]

            # Serializar datos
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
                    'status': appointment.status
                })

            response_data = {
                'draw': draw,
                'recordsTotal': total_records,
                'recordsFiltered': filtered_records,
                'data': appointments
            }

            return JsonResponse(response_data)

        except Exception as e:
            logger.error(f"Error in appointments API: {str(e)}", exc_info=True)
            return JsonResponse({
                'draw': draw if 'draw' in locals() else 1,
                'recordsTotal': 0,
                'recordsFiltered': 0,
                'data': [],
                'error': str(e)
            }, status=500)

    def post(self, request):
        try:
            data = json.loads(request.body)
            data['staff'] = request.user.staffprofile.id

            if 'date' in data:
                data['date'] = make_aware(datetime.fromisoformat(data['date']))

            # Verificar solapamientos
            overlap = Appointment.objects.filter(
                staff=request.user.staffprofile,
                date__lt=data['date'] + timedelta(minutes=30),
                date__gt=data['date'] - timedelta(minutes=30)
            ).exists()

            if overlap:
                return JsonResponse({
                    'error': 'Ya existe una cita en este horario'
                }, status=400)

            serializer = AppointmentSerializer(data=data)
            if serializer.is_valid():
                appointment = serializer.save()
                
                # Desactivar slots solapados
                AvailabilitySlot.objects.filter(
                    staff=request.user.staffprofile,
                    date=data['date'].date(),
                    start_time__lt=(data['date'] + timedelta(minutes=30)).time(),
                    end_time__gt=(data['date'] - timedelta(minutes=30)).time()
                ).update(is_active=False)
                
                logger.info(f"Created appointment: {appointment.id}")
                return JsonResponse(serializer.data)

            logger.warning(f"Invalid appointment data: {serializer.errors}")
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
            data['staff'] = request.user.staffprofile.id

            if 'date' in data:
                data['date'] = make_aware(datetime.fromisoformat(data['date']))
                
                # Verificar solapamientos excluyendo la cita actual
                overlap = Appointment.objects.filter(
                    staff=request.user.staffprofile,
                    date__lt=data['date'] + timedelta(minutes=30),
                    date__gt=data['date'] - timedelta(minutes=30)
                ).exclude(id=appointment_id).exists()

                if overlap:
                    return JsonResponse({
                        'error': 'Ya existe una cita en este horario'
                    }, status=400)

            serializer = AppointmentSerializer(appointment, data=data, partial=True)
            if serializer.is_valid():
                updated_appointment = serializer.save()
                
                if 'date' in data:
                    # Desactivar slots solapados
                    AvailabilitySlot.objects.filter(
                        staff=request.user.staffprofile,
                        date=data['date'].date(),
                        start_time__lt=(data['date'] + timedelta(minutes=30)).time(),
                        end_time__gt=(data['date'] - timedelta(minutes=30)).time()
                    ).update(is_active=False)
                
                logger.info(f"Updated appointment: {appointment_id}")
                return JsonResponse(serializer.data)

            logger.warning(f"Invalid update data for appointment {appointment_id}: {serializer.errors}")
            return JsonResponse(serializer.errors, status=400)

        except Exception as e:
            logger.error(f"Error updating appointment {appointment_id}: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)

    def delete(self, request, appointment_id):
        try:
            appointment = get_object_or_404(
                Appointment, 
                id=appointment_id,
                staff=request.user.staffprofile
            )
            
            # Reactivar slots relacionados
            AvailabilitySlot.objects.filter(
                staff=request.user.staffprofile,
                date=appointment.date.date(),
                start_time__lt=(appointment.date + timedelta(minutes=30)).time(),
                end_time__gt=(appointment.date - timedelta(minutes=30)).time()
            ).update(is_active=True)
            
            appointment.delete()
            logger.info(f"Deleted appointment: {appointment_id}")
            return JsonResponse({'status': 'success'})

        except Exception as e:
            logger.error(f"Error deleting appointment {appointment_id}: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)

    def check_overlap(self, request):
        try:
            data = json.loads(request.body)
            date = make_aware(datetime.fromisoformat(data['date']))
            
            # Buscar citas solapadas
            overlap = Appointment.objects.filter(
                staff=request.user.staffprofile,
                date__lt=date + timedelta(minutes=30),
                date__gt=date - timedelta(minutes=30)
            ).exists()
            
            if overlap:
                # Desactivar slots solapados
                AvailabilitySlot.objects.filter(
                    staff=request.user.staffprofile,
                    date=date.date(),
                    start_time__lt=(date + timedelta(minutes=30)).time(),
                    end_time__gt=(date - timedelta(minutes=30)).time()
                ).update(is_active=False)
                
            return JsonResponse({'overlap': overlap})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)