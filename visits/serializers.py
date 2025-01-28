from rest_framework import serializers
from .models import Appointment, AvailabilitySlot, SchoolStage
from django.utils.timezone import make_aware
from datetime import datetime

class AppointmentSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    start = serializers.SerializerMethodField()
    end = serializers.SerializerMethodField()
    
    class Meta:
        model = Appointment
        fields = ['id', 'title', 'start', 'end', 'visitor_name', 'visitor_email', 'visitor_phone']
        
    def get_title(self, obj):
        return f"{obj.visitor_name} - {obj.stage.name}"
        
    def get_start(self, obj):
        return obj.date
        
    def get_end(self, obj):
        return obj.date + timedelta(minutes=30)  # Asumiendo citas de 30 minutos

class AvailabilitySlotSerializer(serializers.ModelSerializer):
    staff_name = serializers.SerializerMethodField()
    start = serializers.SerializerMethodField()
    end = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    extendedProps = serializers.SerializerMethodField()
    
    class Meta:
        model = AvailabilitySlot
        fields = ['id', 'start', 'end', 'duration', 'staff_name', 'title', 'extendedProps']
    
    def get_staff_name(self, obj):
        return obj.staff.user.get_full_name()
    
    def get_start(self, obj):
        return obj.get_datetime_start()
    
    def get_end(self, obj):
        return obj.get_datetime_end()
        
    def get_title(self, obj):
        return f"Disponible con {self.get_staff_name(obj)}"
        
    def get_extendedProps(self, obj):
        """Propiedades adicionales para el evento de FullCalendar"""
        return {
            'staff_name': self.get_staff_name(obj),
            'duration': obj.duration,
            'stage_name': obj.stage.name
        }

class CalendarDaySerializer(serializers.Serializer):
    date = serializers.DateField()
    has_slots = serializers.BooleanField()
    slots_count = serializers.IntegerField()
    
    def to_representation(self, instance):
        """
        Asegura formato ISO para las fechas y añade datos adicionales
        necesarios para el calendario
        """
        data = super().to_representation(instance)
        data['date'] = instance['date'].isoformat() if isinstance(instance['date'], datetime.date) else instance['date']
        
        # Agregar propiedades necesarias para FullCalendar
        data['selectable'] = data['has_slots']
        return data