from rest_framework import serializers
from .models import Appointment, AvailabilitySlot, SchoolStage
from django.utils.timezone import make_aware, localtime
from datetime import datetime, timedelta

class AppointmentSerializer(serializers.ModelSerializer):
    """Serializer for Appointment model with calendar and CRUD functionality"""
    # Calendar-specific fields
    title = serializers.SerializerMethodField()
    start = serializers.SerializerMethodField()
    end = serializers.SerializerMethodField()
    
    # CRUD-specific fields
    stage_name = serializers.CharField(source='stage.name', read_only=True)
    fecha_y_hora = serializers.SerializerMethodField()
    status = serializers.CharField(required=False, default='pending')
    
    class Meta:
        model = Appointment
        fields = [
            # Base fields
            'id', 'visitor_name', 'visitor_email', 'visitor_phone',
            'stage', 'stage_name', 'status', 'comments', 'staff', 'date',
            # Calendar fields
            'title', 'start', 'end', 'fecha_y_hora'
        ]
        
    def get_title(self, obj):
        return f"{obj.visitor_name} - {obj.stage.name}"
        
    def get_start(self, obj):
        return obj.date
        
    def get_end(self, obj):
        return obj.date + timedelta(minutes=30)

    def get_fecha_y_hora(self, obj):
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
        return obj.start_time.strftime('%H:%M')
    
    def get_date(self, obj):
        return obj.date.isoformat()
        
    def get_available(self, obj):
        return True
        
    def get_staff_name(self, obj):
        return obj.staff.user.get_full_name()

    def get_fecha_y_hora(self, obj):
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
        return obj.start_time.strftime('%H:%M')
        
    def get_date(self, obj):
        return obj.date.isoformat()

    def get_fecha_y_hora(self, obj):
        fecha = obj.date.strftime('%d/%m/%Y')
        hora = obj.start_time.strftime('%H:%M')
        return f"{fecha} {hora}"