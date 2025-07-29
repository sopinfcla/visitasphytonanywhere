from rest_framework import serializers
from .models import Appointment, AvailabilitySlot, SchoolStage, Course
from django.utils.timezone import make_aware, localtime
from datetime import datetime, timedelta

class AppointmentSerializer(serializers.ModelSerializer):
    """Serializer for Appointment model with calendar and CRUD functionality"""
    title = serializers.SerializerMethodField(read_only=True)
    start = serializers.SerializerMethodField(read_only=True)
    end = serializers.SerializerMethodField(read_only=True)
    
    stage_name = serializers.CharField(source='stage.name', read_only=True)
    course_name = serializers.CharField(source='course.name', read_only=True)
    fecha_y_hora = serializers.SerializerMethodField(read_only=True)
    status = serializers.CharField(required=False, default='pending')

    class Meta:
        model = Appointment
        fields = [
            'id', 'visitor_name', 'visitor_email', 'visitor_phone',
            'stage', 'stage_name', 'course', 'course_name', 'status', 'comments', 'staff', 'date',
            'duration', 'title', 'start', 'end', 'fecha_y_hora',
            'notes', 'follow_up_date'
        ]
        extra_kwargs = {
            'staff': {'required': True},
            'visitor_name': {'required': True},
            'visitor_email': {'required': True},
            'visitor_phone': {'required': True},
            'stage': {'required': True},
            'date': {'required': True},
            'duration': {'required': True},
            'course': {'required': False}
        }

    def get_title(self, obj):
        course_info = f" - {obj.course.name}" if obj.course else ""
        return f"{obj.visitor_name} - {obj.stage.name}{course_info}"

    def get_start(self, obj):
        return obj.date

    def get_end(self, obj):
        return obj.date + timedelta(minutes=obj.duration)

    def get_fecha_y_hora(self, obj):
        return obj.date.strftime('%d/%m/%Y %H:%M')

    def validate(self, data):
        """Validación personalizada para los datos de la cita"""
        # Validar teléfono
        if 'visitor_phone' in data:
            phone = data['visitor_phone']
            if not phone.isdigit() or len(phone) != 9:
                raise serializers.ValidationError({
                    'visitor_phone': 'El teléfono debe contener exactamente 9 dígitos.'
                })

        # Validar duración
        if 'duration' in data and data['duration'] not in [15, 30, 45, 60]:
            raise serializers.ValidationError({
                'duration': 'La duración debe ser 15, 30, 45 o 60 minutos.'
            })

        # Validar que el curso sea obligatorio si la etapa tiene cursos
        if 'stage' in data:
            stage = data['stage']
            course = data.get('course')
            
            # Si la etapa tiene cursos, el curso es obligatorio
            if hasattr(stage, 'courses') and stage.courses.exists():
                if not course:
                    raise serializers.ValidationError({
                        'course': 'Debes seleccionar un curso para esta etapa educativa.'
                    })

        # Validar que el curso pertenece a la etapa (si se proporciona)
        if 'course' in data and data['course'] and 'stage' in data:
            course = data['course']
            stage = data['stage']
            if course.stage != stage:
                raise serializers.ValidationError({
                    'course': 'El curso seleccionado no pertenece a la etapa elegida.'
                })

        return data


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


class CourseSerializer(serializers.ModelSerializer):
    """Serializer for Course model"""
    stage_name = serializers.CharField(source='stage.name', read_only=True)
    
    class Meta:
        model = Course
        fields = ['id', 'name', 'stage', 'stage_name', 'order']