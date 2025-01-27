from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView, View
from rest_framework import viewsets
from rest_framework.response import Response
from django.http import JsonResponse
from datetime import datetime, timedelta
from django.contrib.auth.mixins import LoginRequiredMixin
import json


from .models import (
    Appointment, 
    SchoolStage, 
    StaffProfile, 
    AvailabilitySlot
)
from .serializers import AppointmentSerializer

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
        for stage in SchoolStage.objects.all().order_by('id'):
            stage_data = {
                'id': stage.id,
                'name': stage.name,
                'description': stage.description,
            }
            
            if stage.id == 1:  # Primer ciclo de Educación Infantil
                stage_data.update({
                    'name': 'Escuela Infantil',
                    'description': 'Primer ciclo de educación infantil',
                    'subtitle': 'Primer Ciclo',
                    'features': ['Programa bilingüe', 'Nuevas tecnologías', 'Desarrollo personal'],
                    'icon': '👶'
                })
            elif stage.id == 2:  # Segundo ciclo de Educación Infantil
                stage_data.update({
                    'name': 'Infantil',
                    'description': 'Segundo ciclo de educación infantil',
                    'subtitle': 'Segundo Ciclo',
                    'features': ['Orientación académica', 'Preparación EvAU', 'Actividades extraescolares'],
                    'icon': '🎨'
                })
            elif stage.id == 3:  # Primaria
                stage_data.update({
                    'name': 'Primaria',
                    'description': 'Educación primaria',
                    'features': ['Ciencias', 'Humanidades', 'Orientación universitaria'],
                    'icon': '📚'
                })
            elif stage.id == 4:  # Secundaria
                stage_data.update({
                    'name': 'Secundaria',
                    'description': 'Educación Secundaria',
                    'features': ['Orientación académica', 'Innovación educativa', 'Formación integral'],
                    'icon': '🔬'
                })
            elif stage.id == 5:  # Bachillerato
                stage_data.update({
                    'name': 'Bachillerato',
                    'description': 'Bachillerato',
                    'features': ['Ciencias', 'Humanidades', 'Orientación universitaria'],
                    'icon': '🎓'
                })
                
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
    data = [{'id': s.id, 'name': str(s)} for s in staff]
    return JsonResponse(data, safe=False)

def get_stage_availability(request, stage_id):
    try:
        start_date = datetime.now().date()
        end_date = start_date + timedelta(days=30)
        
        # Filtrar slots activos para el rango de fechas
        slots = AvailabilitySlot.objects.filter(
            stage_id=stage_id,
            date__range=(start_date, end_date),
            is_active=True
        ).select_related('staff')
        
        # Obtener los slots ya reservados
        booked_slots = Appointment.objects.filter(
            stage_id=stage_id,
            date__range=(start_date, end_date)
        ).values_list('date', flat=True)
        
        # Excluir los slots reservados
        available_slots = slots.exclude(date__in=booked_slots)
        
        # Transformar los datos para FullCalendar
        data = [{
            'id': slot.id,
            'title': f"Disponible con {slot.staff.user.get_full_name()}",
            'start': make_aware(datetime.combine(slot.date, slot.start_time)).isoformat(),
            'end': make_aware(datetime.combine(slot.date, slot.end_time)).isoformat(),
            'duration': slot.duration,
            'staff_name': slot.staff.user.get_full_name(),
            'backgroundColor': '#28a745',  # Color verde para diferenciar disponibilidad
            'borderColor': '#1e7e34'
        } for slot in available_slots]
        
        return JsonResponse(data, safe=False)  # JSON para FullCalendar
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

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
        
def stage_booking_view(request, stage_id):
    stage = get_object_or_404(SchoolStage, id=stage_id)
    return render(request, 'visits/stage_booking.html', {'stage': stage})