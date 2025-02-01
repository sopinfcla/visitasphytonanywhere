from rest_framework import serializers
from .models import Appointment, AvailabilitySlot, SchoolStage
from django.utils.timezone import make_aware, localtime
from datetime import datetime, timedelta

class AppointmentSerializer(serializers.ModelSerializer):
    fecha_y_hora = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    start = serializers.SerializerMethodField()
    end = serializers.SerializerMethodField()
    
    class Meta:
        model = Appointment
        fields = ['id', 'title', 'start', 'end', 'fecha_y_hora', 'visitor_name', 'visitor_email', 'visitor_phone']
        
    def get_title(self, obj):
        return f"{obj.visitor_name} - {obj.stage.name}"
        
    def get_start(self, obj):
        # Usar la fecha/hora sin conversión de zona horaria
        return obj.date
        
    def get_end(self, obj):
        # Usar la fecha/hora sin conversión de zona horaria
        return obj.date + timedelta(minutes=30)

    def get_fecha_y_hora(self, obj):
        # Usamos la hora del slot original
        return obj.date.strftime('%d/%m/%Y %H:%M')

class AvailabilitySlotSerializer(serializers.ModelSerializer):
    time = serializers.SerializerMethodField()
    available = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    staff_name = serializers.SerializerMethodField()
    fecha_y_hora = serializers.SerializerMethodField()
    
    class Meta:
        model = AvailabilitySlot
        fields = ['id', 'time', 'date', 'available', 'staff_name', 'fecha_y_hora']
    
    def get_time(self, obj):
        # Mantener la hora original del slot sin conversiones
        return obj.start_time.strftime('%H:%M')
    
    def get_date(self, obj):
        # Mantener la fecha original del slot sin conversiones
        return obj.date.isoformat()
        
    def get_available(self, obj):
        return True
        
    def get_staff_name(self, obj):
        return obj.staff.user.get_full_name()

    def get_fecha_y_hora(self, obj):
        # Para mostrar en el listado
        fecha = obj.date.strftime('%d/%m/%Y')
        hora = obj.start_time.strftime('%H:%M')
        return f"{fecha} {hora}"

class CalendarDaySerializer(serializers.Serializer):
    date = serializers.DateField()
    available = serializers.BooleanField(default=True)
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if isinstance(instance['date'], datetime.date):
            data['date'] = instance['date'].isoformat()
        return data

class SlotDetailSerializer(serializers.ModelSerializer):
    staff_name = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    fecha_y_hora = serializers.SerializerMethodField()
    
    class Meta:
        model = AvailabilitySlot
        fields = ['id', 'time', 'date', 'staff_name', 'fecha_y_hora']
    
    def get_staff_name(self, obj):
        return obj.staff.user.get_full_name()
    
    def get_time(self, obj):
        # Mantener hora original del slot
        return obj.start_time.strftime('%H:%M')
        
    def get_date(self, obj):
        # Mantener fecha original del slot
        return obj.date.isoformat()

    def get_fecha_y_hora(self, obj):
        # Formato consistente para mostrar
        fecha = obj.date.strftime('%d/%m/%Y')
        hora = obj.start_time.strftime('%H:%M')
        return f"{fecha} {hora}"