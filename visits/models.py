# ====================================
# Part 1: Imports and Configuration - CORREGIDO
# ====================================

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils.timezone import make_aware, localtime, get_current_timezone
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

class Course(models.Model):
    """Modelo para los cursos específicos dentro de cada etapa"""
    stage = models.ForeignKey(SchoolStage, on_delete=models.CASCADE, related_name='courses')
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=1, help_text="Orden de visualización dentro de la etapa")
    
    class Meta:
        ordering = ['stage', 'order']
        unique_together = ['stage', 'name']
    
    def __str__(self):
        return f"{self.stage.name} - {self.name}"

class StaffProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    allowed_stages = models.ManyToManyField(SchoolStage)
    notify_new_appointment = models.BooleanField(default=True)
    notify_reminder = models.BooleanField(default=True)
    
    def __str__(self):
        return self.user.get_full_name()

    def has_overlapping_slots(self, date, start_time, end_time, exclude_id=None):
        """
        CORRECCIÓN COMPLETA: Verificar solapamientos de slots con manejo correcto de límites exactos
        """
        logger.debug(f"Verificando solapamientos de slots para {self} en {date} de {start_time} a {end_time}")
        
        overlapping = AvailabilitySlot.objects.filter(
            staff=self,
            date=date,
            is_active=True
        )
        
        if exclude_id:
            overlapping = overlapping.exclude(id=exclude_id)
        
        for slot in overlapping:
            logger.debug(f"Comparando con slot existente: {slot.start_time} - {slot.end_time}")
            
            # CORRECCIÓN: Verificar solapamiento real (sin límites exactos)
            # Hay solapamiento si: start1 < end2 AND end1 > start2
            # PERO permitir límites exactos: end1 == start2 OR start1 == end2
            if start_time < slot.end_time and end_time > slot.start_time:
                # Permitir límites exactos
                if end_time == slot.start_time or start_time == slot.end_time:
                    logger.debug(f"Límite exacto permitido con slot {slot.id}")
                    continue
                
                logger.warning(f"Slot solapado encontrado: {slot.id}")
                return True
        
        logger.debug("No se encontraron solapamientos de slots")
        return False

    def has_appointments_in_timeframe(self, date, start_time, end_time):
        """
        CORRECCIÓN COMPLETA: Verificar citas que se solapen con manejo correcto de zonas horarias
        """
        logger.debug(f"Verificando citas para {self} en {date} de {start_time} a {end_time}")
        
        # Buscar citas del mismo día
        appointments_same_day = Appointment.objects.filter(
            staff=self,
            date__date=date
        )
        
        logger.debug(f"Encontradas {appointments_same_day.count()} citas en {date}")
        
        for appointment in appointments_same_day:
            # CORRECCIÓN: Convertir la cita a hora local para comparación
            apt_local = localtime(appointment.date)
            apt_start_time = apt_local.time()
            apt_end_time = (apt_local + timedelta(minutes=appointment.duration)).time()
            
            logger.debug(f"Comparando con cita {appointment.id}: {apt_start_time} - {apt_end_time}")
            
            # CORRECCIÓN: Verificar solapamiento con times (no datetimes)
            # Hay solapamiento si: start1 < end2 AND end1 > start2
            if start_time < apt_end_time and end_time > apt_start_time:
                # Permitir límites exactos
                if end_time == apt_start_time or start_time == apt_end_time:
                    logger.debug(f"Límite exacto permitido con cita {appointment.id}")
                    continue
                
                logger.warning(f"Cita solapada encontrada: {appointment.id} ({apt_start_time} - {apt_end_time})")
                return True
        
        logger.debug("No se encontraron solapamientos con citas")
        return False

# ====================================
# Part 3: Appointment Management - CORREGIDO
# ====================================

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('completed', 'Realizada'),
        ('cancelled', 'Cancelada')
    ]
    
    stage = models.ForeignKey(SchoolStage, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True, 
                              help_text="Curso específico dentro de la etapa")
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE)
    visitor_name = models.CharField(max_length=200)
    visitor_email = models.EmailField()
    visitor_phone = models.CharField(max_length=20)
    date = models.DateTimeField()
    duration = models.PositiveIntegerField(default=60)  # Duración en minutos
    created_at = models.DateTimeField(auto_now_add=True)
    comments = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES,
        default='pending'
    )
    notes = models.TextField(blank=True, help_text="Notas internas del profesor")
    follow_up_date = models.DateField(null=True, blank=True, help_text="Fecha de seguimiento")
    reminder_sent = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['staff', 'date']),
            models.Index(fields=['status']),
        ]
    
    def clean(self):
        """
        CORRECCIÓN COMPLETA: Validar solapamientos con zona horaria correcta EN MENSAJES
        """
        super().clean()
        
        logger.debug(f"Validando cita para {self.visitor_name} programada para {self.date}")
        
        # Validar que el curso corresponde a la etapa
        if self.course and self.stage and self.course.stage != self.stage:
            logger.warning(f"El curso {self.course} no pertenece a la etapa {self.stage}")
            raise ValidationError({
                'course': _('El curso seleccionado no pertenece a la etapa elegida.')
            })
        
        # Validar que el staff puede atender la etapa
        if self.staff and self.stage and self.stage not in self.staff.allowed_stages.all():
            logger.warning(f"El profesor {self.staff} no está autorizado para atender la etapa {self.stage}")
            raise ValidationError({
                'staff': _('Este miembro del staff no puede atender citas de esta etapa.')
            })
        
        # Validar formato del teléfono
        if self.visitor_phone and (not self.visitor_phone.isdigit() or len(self.visitor_phone) != 9):
            logger.warning(f"Formato de teléfono inválido: {self.visitor_phone}")
            raise ValidationError({
                'visitor_phone': _('El teléfono debe contener exactamente 9 dígitos.')
            })
        
        # CORRECCIÓN PRINCIPAL: Validar solapamientos con zona horaria correcta
        if self.date and self.staff and self.duration:
            # Convertir a hora local para comparaciones Y mensajes
            appointment_local = localtime(self.date)
            appointment_date = appointment_local.date()
            appointment_start_time = appointment_local.time()
            appointment_end_time = (appointment_local + timedelta(minutes=self.duration)).time()
            
            logger.debug(f"Validando cita: {appointment_date} {appointment_start_time} - {appointment_end_time}")
            
            # Buscar citas existentes del mismo staff en el mismo día
            existing_appointments = Appointment.objects.filter(
                staff=self.staff,
                date__date=appointment_date
            )
            
            # Excluir la cita actual si estamos editando
            if self.pk:
                existing_appointments = existing_appointments.exclude(pk=self.pk)
                logger.debug(f"Excluyendo cita actual (ID: {self.pk}) de la validación")
            
            logger.debug(f"Encontradas {existing_appointments.count()} citas existentes para validar")
            
            # Verificar solapamientos cita por cita
            for existing_apt in existing_appointments:
                # CORRECCIÓN: Convertir cita existente a hora local PARA COMPARACIÓN Y MENSAJE
                existing_local = localtime(existing_apt.date)
                existing_start_time = existing_local.time()
                existing_end_time = (existing_local + timedelta(minutes=existing_apt.duration)).time()
                
                logger.debug(f"Comparando con cita {existing_apt.id}:")
                logger.debug(f"  Existente: {existing_start_time} - {existing_end_time}")
                logger.debug(f"  Nueva:     {appointment_start_time} - {appointment_end_time}")
                
                # CORRECCIÓN: Verificar solapamiento con times locales y permitir límites exactos
                if appointment_start_time < existing_end_time and appointment_end_time > existing_start_time:
                    # Permitir límites exactos
                    if appointment_end_time == existing_start_time or appointment_start_time == existing_end_time:
                        logger.debug(f"Límite exacto permitido con cita {existing_apt.id}")
                        continue
                    
                    logger.warning("Cita solapada encontrada")
                    
                    # CORRECCIÓN: Mensaje con horas locales
                    raise ValidationError(
                        f'Ya existe una cita de {existing_apt.visitor_name} '
                        f'programada de {existing_start_time.strftime("%H:%M")} a {existing_end_time.strftime("%H:%M")} '  
                        f'el {existing_local.strftime("%d/%m/%Y")}'
                    )
                else:
                    logger.debug(f"No hay solapamiento con cita {existing_apt.id}")
        
        logger.info(f"Cita para {self.visitor_name} validada correctamente")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        logger.debug(f"Guardando cita para {self.visitor_name} a las {self.date}")
        super().save(*args, **kwargs)
    
    def __str__(self):
        course_info = f" - {self.course.name}" if self.course else ""
        return f"{self.visitor_name} - {self.stage.name}{course_info} - {self.date}"

# ====================================
# Part 4: Availability Management - CORREGIDO
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
        """
        CORRECCIÓN COMPLETA: Validación de slots con manejo correcto
        """
        logger.debug(f"Validando slot para {self.staff} con tipo '{self.repeat_type}'")
        
        # Validar horarios
        min_time = time(8, 0)
        max_time = time(20, 0)
        if self.start_time < min_time or self.end_time > max_time:
            logger.warning("Horario fuera del rango permitido (8:00 - 20:00)")
            raise ValidationError(_('Los horarios deben estar entre 8:00 y 20:00'))
        
        if self.end_time <= self.start_time:
            logger.warning("La hora de fin debe ser posterior a la hora de inicio")
            raise ValidationError({'end_time': 'La hora de fin debe ser posterior a la hora de inicio'})
        
        if self.duration <= 0:
            logger.warning("La duración debe ser un valor positivo")
            raise ValidationError({'duration': 'La duración debe ser positiva'})
        
        if self.stage not in self.staff.allowed_stages.all():
            logger.warning("El profesor no está autorizado para atender esta etapa")
            raise ValidationError({'stage': 'Este miembro del staff no puede atender esta etapa'})
        
        # Validar según tipo de repetición
        if self.repeat_type == 'once':
            if not self.date:
                logger.warning("Se requiere la fecha para un slot no recurrente")
                raise ValidationError({'date': 'La fecha es requerida para slots no recurrentes'})
            if self.date < datetime.now().date():
                logger.warning("No se pueden crear slots para fechas pasadas")
                raise ValidationError({'date': 'No se pueden crear slots para fechas pasadas'})
            self.month = None
            self.weekday = None
            
            # CORRECCIÓN: Verificar solapamientos para slots no recurrentes
            if self.staff.has_overlapping_slots(self.date, self.start_time, self.end_time, self.pk):
                logger.warning("Slot solapado encontrado")
                raise ValidationError(_('Ya existe un slot en este horario'))
            if self.staff.has_appointments_in_timeframe(self.date, self.start_time, self.end_time):
                logger.warning("Cita programada en el mismo intervalo")
                raise ValidationError(_('Ya existe una cita programada en este horario'))
                
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
        
        logger.info(f"Slot para {self.staff} validado correctamente")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        logger.debug(f"Guardando slot para {self.staff} en {self.date or 'slot recurrente'}")
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
        """
        CORRECCIÓN COMPLETA: Verificar disponibilidad con manejo correcto
        """
        logger.debug(f"Comprobando disponibilidad del slot en {self.date} de {self.start_time} a {self.end_time}")
        if not self.is_active:
            logger.debug("El slot no está activo")
            return False
        
        # Verificar si hay citas que se solapen con este slot
        appointments = Appointment.objects.filter(
            stage=self.stage,
            staff=self.staff,
            date__date=self.date
        )
        
        for apt in appointments:
            apt_local = localtime(apt.date)
            apt_start_time = apt_local.time()
            apt_end_time = (apt_local + timedelta(minutes=apt.duration)).time()
            
            # Verificar solapamiento con límites exactos permitidos
            if self.start_time < apt_end_time and self.end_time > apt_start_time:
                # Permitir límites exactos
                if self.end_time == apt_start_time or self.start_time == apt_end_time:
                    continue
                
                logger.debug("El slot no está disponible debido a una cita existente")
                return False
        
        logger.debug("El slot está disponible")
        return True

    def generate_slots(self):
        """
        CORRECCIÓN COMPLETA: Genera slots con manejo correcto
        """
        logger.info(f"Generando slots para {self.staff} con tipo '{self.repeat_type}'")
        if self.repeat_type == 'once':
            return self._generate_day_slots()
        return self._generate_monthly_slots()

    def _generate_day_slots(self):
        """
        CORRECCIÓN COMPLETA: Genera slots individuales para un día específico
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
            
            # CORRECCIÓN: Verificar si existe una cita programada en este intervalo
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
                logger.debug(f"Slot generado: {slot_start} - {slot_end} para {self.date}")
            
            # Avanzar 15 minutos
            current_dt += timedelta(minutes=15)
        
        logger.info(f"Generados {len(slots)} slots diarios para {self.date}")
        return slots

    def _generate_monthly_slots(self):
        """
        CORRECCIÓN COMPLETA: Genera slots para todas las ocurrencias del día de la semana
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
                        
                        # CORRECCIÓN: Verificación correcta de solapamientos
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
        
        logger.info(f"Generados {len(slots)} slots mensuales para el mes {self.month}")
        return slots

    def __str__(self):
        if self.date:
            return f"{self.staff} - {self.date} {self.start_time}"
        return f"{self.staff} - {calendar.day_name[self.weekday]} {self.start_time}"

    @classmethod
    def cleanup_old_slots(cls):
        """
        Elimina los slots de fechas pasadas que no tienen citas asignadas.
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