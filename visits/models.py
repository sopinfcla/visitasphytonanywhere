from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils.timezone import make_aware
from datetime import datetime, timedelta, time
import calendar
import logging

logger = logging.getLogger(__name__)

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

    def has_overlapping_slots(self, date, start_time, end_time, exclude_id=None):
        """Verifica si hay slots solapados para este staff"""
        overlapping = AvailabilitySlot.objects.filter(
            staff=self,
            date=date,
            is_active=True
        ).exclude(id=exclude_id)

        for slot in overlapping:
            if (start_time < slot.end_time and end_time > slot.start_time):
                return True
        return False

    def has_appointments_in_timeframe(self, date, start_time, end_time):
        """Verifica si hay citas en el rango de tiempo especificado"""
        start_datetime = make_aware(datetime.combine(date, start_time))
        end_datetime = make_aware(datetime.combine(date, end_time))
        
        return Appointment.objects.filter(
            staff=self,
            date__gte=start_datetime,
            date__lt=end_datetime
        ).exists()

class Appointment(models.Model):
    stage = models.ForeignKey(SchoolStage, on_delete=models.CASCADE)
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE)
    visitor_name = models.CharField(max_length=200)
    visitor_email = models.EmailField()
    visitor_phone = models.CharField(max_length=20)
    date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    comments = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['staff', 'date']),
        ]

    def clean(self):
        if not self.pk:  # Solo para nuevas citas
            # Validar etapa asignada al staff
            if self.staff and self.stage and self.stage not in self.staff.allowed_stages.all():
                raise ValidationError({
                    'staff': _('Este miembro del staff no puede atender citas de esta etapa.')
                })

            # Validar solapamiento con otras citas
            appointment_date = self.date.date()
            appointment_time = self.date.time()
            end_time = (datetime.combine(appointment_date, appointment_time) + 
                       timedelta(minutes=30)).time()

            if self.staff.has_appointments_in_timeframe(
                appointment_date, appointment_time, end_time):
                raise ValidationError(_('Ya existe una cita en este horario.'))

            # Validar formato de teléfono
            if not self.visitor_phone.isdigit() or len(self.visitor_phone) != 9:
                raise ValidationError({
                    'visitor_phone': _('El teléfono debe contener exactamente 9 dígitos.')
                })

            logger.info(f"Nueva cita validada para {self.visitor_name} el {self.date}")

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
        # Validar horario permitido (8:00 - 20:00)
        min_time = time(8, 0)
        max_time = time(20, 0)
        
        if self.start_time < min_time or self.end_time > max_time:
            raise ValidationError(_('Los horarios deben estar entre 8:00 y 20:00'))

        # Validación para slots no recurrentes
        if self.repeat_type == 'once':
            if not self.date:
                raise ValidationError({'date': 'La fecha es requerida para slots no recurrentes'})
            # Validar que la fecha no sea pasada
            if self.date < datetime.now().date():
                raise ValidationError({'date': 'No se pueden crear slots para fechas pasadas'})
            self.month = None
            self.weekday = None
        
        # Validación para slots semanales
        elif self.repeat_type == 'weekly':
            if self.month is None or self.weekday is None:
                raise ValidationError({
                    'month': 'Mes requerido para slots semanales',
                    'weekday': 'Día de la semana requerido para slots semanales'
                })
            # Validar mes actual o futuro
            current_month = datetime.now().month
            if self.month < current_month:
                raise ValidationError({'month': 'No se pueden crear slots para meses pasados'})
            self.date = None
        
        # Validaciones comunes
        if self.end_time <= self.start_time:
            raise ValidationError({'end_time': 'La hora de fin debe ser posterior a la hora de inicio'})
        
        if self.duration <= 0:
            raise ValidationError({'duration': 'La duración debe ser positiva'})
        
        if self.stage not in self.staff.allowed_stages.all():
            raise ValidationError({'stage': 'Este miembro del staff no puede atender esta etapa'})

        # Validar solapamientos
        if self.repeat_type == 'once' and self.date:
            if self.staff.has_overlapping_slots(self.date, self.start_time, self.end_time, self.pk):
                raise ValidationError(_('Ya existe un slot en este horario'))

            if self.staff.has_appointments_in_timeframe(self.date, self.start_time, self.end_time):
                raise ValidationError(_('Ya existe una cita programada en este horario'))

        logger.info(f"Slot validado para {self.staff} el {self.date or 'recurrente'}")

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
        logger.info(f"Generando slots - tipo: {self.repeat_type}, fecha: {self.date}, hora: {self.start_time}-{self.end_time}")
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
        
        logger.info(f"Generados {len(slots)} slots diarios")
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
        
        logger.info(f"Generados {len(slots)} slots mensuales")
        return slots

    def __str__(self):
        if self.date:
            return f"{self.staff} - {self.date} {self.start_time}"
        return f"{self.staff} - {calendar.day_name[self.weekday]} {self.start_time}"