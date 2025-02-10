# ====================================
# Part 1: Imports and Configuration
# ====================================

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils.timezone import make_aware
from datetime import datetime, timedelta, time
import calendar
import logging

logger = logging.getLogger(__name__)

# ====================================
# Part 2: Base Models
# ====================================

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
        logger.debug(f"El profesor {self} está comprobando solapamientos de slots en {date} para el intervalo {start_time} – {end_time}")
        overlapping = AvailabilitySlot.objects.filter(
            staff=self,
            date=date,
            is_active=True
        ).exclude(id=exclude_id)
        
        for slot in overlapping:
            logger.debug(f"Comparando con el slot {slot} ({slot.start_time} – {slot.end_time})")
            if start_time < slot.end_time and end_time > slot.start_time:
                logger.info(f"Se encontró un slot solapado: {slot}")
                return True
        return False

    def has_appointments_in_timeframe(self, date, start_time, end_time):
        logger.debug(f"El profesor {self} está comprobando citas en {date} para el intervalo {start_time} – {end_time}")
        start_datetime = make_aware(datetime.combine(date, start_time))
        end_datetime = make_aware(datetime.combine(date, end_time))
        
        exists = Appointment.objects.filter(
            staff=self,
            date__gte=start_datetime,
            date__lt=end_datetime
        ).exists()
        if exists:
            logger.info(f"Se encontró una cita que se solapa en el intervalo {start_time} – {end_time} en {date}")
        return exists

# ====================================
# Part 3: Appointment Management
# ====================================

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('completed', 'Realizada'),
        ('cancelled', 'Cancelada')
    ]
    
    stage = models.ForeignKey(SchoolStage, on_delete=models.CASCADE)
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE)
    visitor_name = models.CharField(max_length=200)
    visitor_email = models.EmailField()
    visitor_phone = models.CharField(max_length=20)
    date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    comments = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['staff', 'date']),
            models.Index(fields=['status']),
        ]
    
    def clean(self):
        logger.debug(f"Validando la cita para {self.visitor_name} programada para {self.date}")
        if not self.pk:
            if self.staff and self.stage and self.stage not in self.staff.allowed_stages.all():
                logger.warning(f"El profesor {self.staff} no está autorizado para atender la etapa {self.stage}")
                raise ValidationError({
                    'staff': _('Este miembro del staff no puede atender citas de esta etapa.')
                })
            
            appointment_date = self.date.date()
            appointment_time = self.date.time()
            end_time = (datetime.combine(appointment_date, appointment_time) + timedelta(minutes=60)).time()
            
            if self.staff.has_appointments_in_timeframe(appointment_date, appointment_time, end_time):
                logger.warning("Se encontró una cita que se solapa en ese horario")
                raise ValidationError(_('Ya existe una cita en este horario.'))
            
            if not self.visitor_phone.isdigit() or len(self.visitor_phone) != 9:
                logger.warning(f"Formato de teléfono inválido: {self.visitor_phone}")
                raise ValidationError({
                    'visitor_phone': _('El teléfono debe contener exactamente 9 dígitos.')
                })
            
            logger.info(f"La cita para {self.visitor_name} a las {self.date} se validó correctamente")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        logger.debug(f"Guardando la cita para {self.visitor_name} a las {self.date}")
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.visitor_name} - {self.date}"

# ====================================
# Part 4: Availability Management
# ====================================

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
        logger.debug(f"Validando el slot para el profesor {self.staff} con tipo de repetición '{self.repeat_type}'")
        min_time = time(8, 0)
        max_time = time(20, 0)
        if self.start_time < min_time or self.end_time > max_time:
            logger.warning("El horario del slot está fuera del rango permitido (8:00 - 20:00)")
            raise ValidationError(_('Los horarios deben estar entre 8:00 y 20:00'))
        
        if self.repeat_type == 'once':
            if not self.date:
                logger.warning("Se requiere la fecha para un slot no recurrente")
                raise ValidationError({'date': 'La fecha es requerida para slots no recurrentes'})
            if self.date < datetime.now().date():
                logger.warning("No se pueden crear slots para fechas pasadas")
                raise ValidationError({'date': 'No se pueden crear slots para fechas pasadas'})
            self.month = None
            self.weekday = None
        elif self.repeat_type == 'weekly':
            if self.month is None or self.weekday is None:
                logger.warning("Se requieren mes y día de la semana para un slot semanal")
                raise ValidationError({
                    'month': 'Mes requerido para slots semanales',
                    'weekday': 'Día de la semana requerido para slots semanales'
                })
            current_month = datetime.now().month
            if self.month < current_month:
                logger.warning("No se pueden crear slots para meses pasados")
                raise ValidationError({'month': 'No se pueden crear slots para meses pasados'})
            self.date = None
        
        if self.end_time <= self.start_time:
            logger.warning("La hora de fin debe ser posterior a la hora de inicio")
            raise ValidationError({'end_time': 'La hora de fin debe ser posterior a la hora de inicio'})
        if self.duration <= 0:
            logger.warning("La duración debe ser un valor positivo")
            raise ValidationError({'duration': 'La duración debe ser positiva'})
        if self.stage not in self.staff.allowed_stages.all():
            logger.warning("El profesor no está autorizado para atender esta etapa")
            raise ValidationError({'stage': 'Este miembro del staff no puede atender esta etapa'})
        
        # Verificar solapamientos para slots no recurrentes:
        if self.repeat_type == 'once' and self.date:
            if self.staff.has_overlapping_slots(self.date, self.start_time, self.end_time, self.pk):
                logger.warning("Se encontró un slot solapado")
                raise ValidationError(_('Ya existe un slot en este horario'))
            if self.staff.has_appointments_in_timeframe(self.date, self.start_time, self.end_time):
                logger.warning("Se encontró una cita programada en el mismo intervalo")
                raise ValidationError(_('Ya existe una cita programada en este horario'))
        
        logger.info(f"El slot para el profesor {self.staff} se validó correctamente para {self.date or 'slot recurrente'}")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        logger.debug(f"Guardando el slot para el profesor {self.staff} en {self.date or 'slot recurrente'}")
        super().save(*args, **kwargs)
    
    def get_datetime_start(self):
        dt_start = make_aware(datetime.combine(self.date, self.start_time))
        logger.debug(f"Datetime de inicio del slot: {dt_start}")
        return dt_start
    
    def get_datetime_end(self):
        dt_end = make_aware(datetime.combine(self.date, self.end_time))
        logger.debug(f"Datetime de fin del slot: {dt_end}")
        return dt_end
    
    def is_available(self):
        logger.debug(f"Comprobando disponibilidad del slot en {self.date} de {self.start_time} a {self.end_time}")
        if not self.is_active:
            logger.debug("El slot no está activo")
            return False
        
        available = not Appointment.objects.filter(
            stage=self.stage,
            staff=self.staff,
            date__date=self.date,
            date__time__range=(self.start_time, self.end_time)
        ).exists()
        
        if available:
            logger.debug("El slot está disponible")
        else:
            logger.debug("El slot no está disponible debido a una cita existente")
        return available

    def generate_slots(self):
        """
        Genera slots a partir de la disponibilidad base.
        Para slots no recurrentes, genera slots en intervalos de 15 minutos.
        Para slots recurrentes, genera slots para todas las ocurrencias del mes.
        """
        logger.info(f"Generando slots para el profesor {self.staff} con tipo de repetición '{self.repeat_type}'")
        if self.repeat_type == 'once':
            return self._generate_day_slots()
        return self._generate_monthly_slots()

    def _generate_day_slots(self):
        """
        Genera slots individuales para un día específico con intervalos de 15 minutos
        y asegurando que cada slot tenga espacio para la duración completa.
        """
        slots = []
        current_dt = datetime.combine(self.date, self.start_time)
        end_dt = datetime.combine(self.date, self.end_time)
        
        # Redondear al próximo intervalo de 15 minutos si es necesario
        minutes = current_dt.minute
        if minutes % 15 != 0:
            minutes = ((minutes // 15) + 1) * 15
            current_dt = current_dt.replace(minute=minutes)
        
        # Generar slots mientras haya espacio para la duración completa
        while current_dt + timedelta(minutes=self.duration) <= end_dt:
            slot_start = current_dt.time()
            slot_end = (current_dt + timedelta(minutes=self.duration)).time()
            
            # Verificar si existe una cita programada en este intervalo
            if not self.staff.has_appointments_in_timeframe(self.date, slot_start, slot_end):
                slot = AvailabilitySlot(
                    staff=self.staff,
                    stage=self.stage,
                    date=self.date,
                    start_time=slot_start,
                    end_time=slot_end,
                    duration=self.duration,
                    is_active=True,
                    repeat_type='once'
                )
                slots.append(slot)
                logger.debug(f"Slot generado: {slot_start} – {slot_end} para {self.date}")
            
            # Avanzar 15 minutos
            current_dt += timedelta(minutes=15)
        
        logger.info(f"Generados {len(slots)} slots diarios para {self.date}")
        return slots

    def _generate_monthly_slots(self):
        """
        Genera slots para todas las ocurrencias del día de la semana especificado en el mes.
        """
        slots = []
        year = datetime.now().year
        c = calendar.monthcalendar(year, self.month)
        
        for week in c:
            if week[self.weekday] != 0:
                date_obj = datetime(year, self.month, week[self.weekday]).date()
                if date_obj >= datetime.now().date():
                    current_dt = datetime.combine(date_obj, self.start_time)
                    end_dt = datetime.combine(date_obj, self.end_time)
                    
                    # Redondear al próximo intervalo de 15 minutos
                    minutes = current_dt.minute
                    if minutes % 15 != 0:
                        minutes = ((minutes // 15) + 1) * 15
                        current_dt = current_dt.replace(minute=minutes)
                    
                    while current_dt + timedelta(minutes=self.duration) <= end_dt:
                        slot_start = current_dt.time()
                        slot_end = (current_dt + timedelta(minutes=self.duration)).time()
                        
                        if not self.staff.has_appointments_in_timeframe(date_obj, slot_start, slot_end):
                            slot = AvailabilitySlot(
                                staff=self.staff,
                                stage=self.stage,
                                date=date_obj,
                                start_time=slot_start,
                                end_time=slot_end,
                                duration=self.duration,
                                is_active=True,
                                repeat_type='once'
                            )
                            slots.append(slot)
                        current_dt += timedelta(minutes=15)
        
        logger.info(f"Generados {len(slots)} slots mensuales para el mes {self.month} en el día de la semana {self.weekday}")
        return slots

    def __str__(self):
        if self.date:
            return f"{self.staff} - {self.date} {self.start_time}"
        return f"{self.staff} - {calendar.day_name[self.weekday]} {self.start_time}"

    @classmethod
    def cleanup_old_slots(cls):
        """
        Elimina los slots de fechas pasadas que no tienen citas asignadas.
        Se ejecuta automáticamente al iniciar la aplicación.
        """
        today = datetime.now().date()
        
        # Identificar slots antiguos sin citas
        old_slots = cls.objects.filter(
            date__lt=today,
            is_active=True
        ).exclude(
            date__in=Appointment.objects.filter(
                date__date__lt=today
            ).values('date__date')
        )
        
        # Registrar y eliminar
        count = old_slots.count()
        if count > 0:
            logger.info(f"Limpiando {count} slots antiguos sin citas asignadas")
            old_slots.delete()
        
        return count