# visits/management/commands/send_reminders.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from visits.models import Appointment
from visits.emails import send_appointment_reminder
import logging

logger = logging.getLogger('visits')

class Command(BaseCommand):
    help = 'Envía recordatorios para las citas de mañana'

    def handle(self, *args, **options):
        tomorrow = timezone.now().date() + timedelta(days=1)
        logger.info(f'Buscando citas para el día {tomorrow}')
        
        appointments = Appointment.objects.filter(
            date__date=tomorrow,
            reminder_sent=False
        )
        
        count = 0
        for appointment in appointments:
            try:
                send_appointment_reminder(appointment)
                appointment.reminder_sent = True
                appointment.save()
                count += 1
                logger.info(f'Recordatorio enviado para cita {appointment.id}')
            except Exception as e:
                logger.error(f'Error enviando recordatorio para cita {appointment.id}: {str(e)}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Enviados {count} recordatorios de {appointments.count()} citas')
        )