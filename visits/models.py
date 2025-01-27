from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from datetime import datetime, timedelta
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

   class Meta:
       ordering = ['date', 'start_time']

   def generate_slots(self):
       print(f"Generating slots - type: {self.repeat_type}, date: {self.date}, time: {self.start_time}-{self.end_time}")
       if self.repeat_type == 'once':
           return self._generate_day_slots()
       return self._generate_monthly_slots()

   def _generate_day_slots(self):
       slots = []
       current_time = self.start_time
       try:
           while (datetime.combine(self.date, current_time) + timedelta(minutes=self.duration)) <= datetime.combine(self.date, self.end_time):
               end_time = (datetime.combine(self.date, current_time) + timedelta(minutes=self.duration)).time()
               print(f"Creating slot: {self.date} {current_time}-{end_time}")
               
               slot = AvailabilitySlot(
                   staff=self.staff,
                   stage=self.stage,
                   date=self.date,
                   start_time=current_time,
                   end_time=end_time,
                   duration=self.duration,
                   is_active=True,
                   repeat_type='once'
               )
               slots.append(slot)
               current_time = end_time
       except Exception as e:
           print(f"Error in _generate_day_slots: {str(e)}")
           raise e
           
       print(f"Generated {len(slots)} day slots")
       return slots

   def _generate_monthly_slots(self):
       slots = []
       year = datetime.now().year
       try:
           c = calendar.monthcalendar(year, self.month)
           for week in c:
               if week[self.weekday] != 0:
                   date = datetime(year, self.month, week[self.weekday]).date()
                   if date >= datetime.now().date():
                       current_time = self.start_time
                       while (datetime.combine(date, current_time) + timedelta(minutes=self.duration)) <= datetime.combine(date, self.end_time):
                           end_time = (datetime.combine(date, current_time) + timedelta(minutes=self.duration)).time()
                           print(f"Creating monthly slot: {date} {current_time}-{end_time}")
                           
                           slot = AvailabilitySlot(
                               staff=self.staff,
                               stage=self.stage,
                               date=date,
                               start_time=current_time,
                               end_time=end_time,
                               duration=self.duration,
                               is_active=True,
                               repeat_type='once'
                           )
                           slots.append(slot)
                           current_time = end_time
       except Exception as e:
           print(f"Error in _generate_monthly_slots: {str(e)}")
           raise e
           
       print(f"Generated {len(slots)} monthly slots")
       return slots

   def __str__(self):
       return f"{self.staff} - {self.date} {self.start_time}"