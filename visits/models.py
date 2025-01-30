from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils.timezone import make_aware
from datetime import datetime, timedelta, time
import calendar

class SchoolStage(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    
    def __str__(self):
        return self.name

class StaffProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    allowed_stages = models.ManyToManyField(SchoolStage)
    
    def __str__(self):
        return self.user.get_full_name()

class Appointment(models.Model):
    stage = models.ForeignKey(SchoolStage, on_delete=models.CASCADE)
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE)
    visitor_name = models.CharField(max_length=200)
    visitor_email = models.EmailField()
    visitor_phone = models.CharField(max_length=20)
    date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    comments = models.TextField(blank=True, null=True)  # Nuevo campo añadido

    class Meta:
        ordering = ['-date']

    def clean(self):
        if self.staff and self.stage and self.stage not in self.staff.allowed_stages.all():
            raise ValidationError({
                'staff': _('Este miembro del staff no puede atender citas de esta etapa.')
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.visitor_name} - {self.date}"

class AvailabilitySlot(models.Model):
    REPEAT_CHOICES = [
        ('once', 'Única vez'),
        ('weekly', 'Semanal'),
    ]
    
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE)
    stage = models.ForeignKey(SchoolStage, on_delete=models.CASCADE)
    date = models.DateField(null=True, blank=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    duration = models.IntegerField(help_text='Duración en minutos')
    is_active = models.BooleanField(default=True)
    repeat_type = models.CharField(max_length=10, choices=REPEAT_CHOICES, default='once')
    month = models.IntegerField(null=True, blank=True)
    weekday = models.IntegerField(null=True, blank=True)
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ['date', 'start_time']
        indexes = [
            models.Index(fields=['date', 'start_time']),
            models.Index(fields=['staff', 'is_active']),
        ]

    def clean(self):
        # Validación para slots no recurrentes
        if self.repeat_type == 'once':
            if not self.date:
                raise ValidationError({'date': 'La fecha es requerida para slots no recurrentes'})
            # Establecer month y weekday a None para evitar confusiones
            self.month = None
            self.weekday = None
        
        # Validación para slots semanales
        elif self.repeat_type == 'weekly':
            if self.month is None or self.weekday is None:
                raise ValidationError({
                    'month': 'Mes requerido para slots semanales',
                    'weekday': 'Día de la semana requerido para slots semanales'
                })
            # Establecer date a None para slots semanales
            self.date = None
        
        # Validaciones comunes
        if self.end_time <= self.start_time:
            raise ValidationError({'end_time': 'La hora de fin debe ser posterior a la hora de inicio'})
        
        if self.duration <= 0:
            raise ValidationError({'duration': 'La duración debe ser positiva'})
        
        if self.stage not in self.staff.allowed_stages.all():
            raise ValidationError({'stage': 'Este miembro del staff no puede atender esta etapa'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_datetime_start(self):
        """Retorna datetime con zona horaria para el inicio del slot"""
        return make_aware(datetime.combine(self.date, self.start_time))

    def get_datetime_end(self):
        """Retorna datetime con zona horaria para el fin del slot"""
        return make_aware(datetime.combine(self.date, self.end_time))

    def is_available(self):
        """Verifica si el slot está disponible"""
        if not self.is_active:
            return False
        
        # Verificar si ya hay una cita para este slot
        return not Appointment.objects.filter(
            stage=self.stage,
            staff=self.staff,
            date__date=self.date,
            date__time__range=(self.start_time, self.end_time)
        ).exists()

    def generate_slots(self):
        """Genera slots individuales basados en este template"""
        print(f"Generating slots - type: {self.repeat_type}, date: {self.date}, time: {self.start_time}-{self.end_time}")
        if self.repeat_type == 'once':
            return self._generate_day_slots()
        return self._generate_monthly_slots()

    def _generate_day_slots(self):
        slots = []
        current_time = self.start_time
        
        while True:
            next_time = datetime.combine(self.date, current_time) + timedelta(minutes=self.duration)
            if next_time.time() > self.end_time:
                break
                
            slot = AvailabilitySlot(
                staff=self.staff,
                stage=self.stage,
                date=self.date,
                start_time=current_time,
                end_time=next_time.time(),
                duration=self.duration,
                is_active=True,
                repeat_type='once'
            )
            slots.append(slot)
            current_time = next_time.time()
        
        print(f"Generated {len(slots)} day slots")
        return slots

    def _generate_monthly_slots(self):
        slots = []
        year = datetime.now().year
        
        c = calendar.monthcalendar(year, self.month)
        for week in c:
            if week[self.weekday] != 0:
                date = datetime(year, self.month, week[self.weekday]).date()
                if date >= datetime.now().date():
                    current_time = self.start_time
                    
                    while True:
                        next_time = datetime.combine(date, current_time) + timedelta(minutes=self.duration)
                        if next_time.time() > self.end_time:
                            break
                            
                        slot = AvailabilitySlot(
                            staff=self.staff,
                            stage=self.stage,
                            date=date,
                            start_time=current_time,
                            end_time=next_time.time(),
                            duration=self.duration,
                            is_active=True,
                            repeat_type='once'
                        )
                        slots.append(slot)
                        current_time = next_time.time()
        
        print(f"Generated {len(slots)} monthly slots")
        return slots

    def __str__(self):
        if self.date:
            return f"{self.staff} - {self.date} {self.start_time}"
        return f"{self.staff} - {calendar.day_name[self.weekday]} {self.start_time}"