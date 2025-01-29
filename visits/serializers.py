from rest_framework import serializers
from .models import Appointment, AvailabilitySlot, SchoolStage
from django.utils.timezone import make_aware
from datetime import datetime, timedelta

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
        return obj.date + timedelta(minutes=30)

class AvailabilitySlotSerializer(serializers.ModelSerializer):
    time = serializers.SerializerMethodField()
    available = serializers.SerializerMethodField()
    
    class Meta:
        model = AvailabilitySlot
        fields = ['id', 'time', 'available']
    
    def get_time(self, obj):
        return obj.start_time.strftime('%H:%M')
        
    def get_available(self, obj):
        return True

class CalendarDaySerializer(serializers.Serializer):
    date = serializers.DateField()
    available = serializers.BooleanField(default=True)
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if isinstance(instance['date'], datetime.date):
            data['date'] = instance['date'].isoformat()
        return data

class SlotDetailSerializer(serializers.ModelSerializer):
    """Serializer para los detalles del slot cuando se selecciona uno"""
    staff_name = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    
    class Meta:
        model = AvailabilitySlot
        fields = ['id', 'time', 'date', 'staff_name']
    
    def get_staff_name(self, obj):
        return obj.staff.user.get_full_name()
    
    def get_time(self, obj):
        return obj.start_time.strftime('%H:%M')
        
    def get_date(self, obj):
        return obj.date.isoformat()