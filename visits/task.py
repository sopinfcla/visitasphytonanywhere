# visits/tasks.py
from celery import shared_task
from datetime import timedelta
from django.utils import timezone
from .models import Appointment
from .emails import send_appointment_reminder

@shared_task
def send_appointment_reminders():
    """
    Envía recordatorios para las citas programadas para mañana
    """
    tomorrow = timezone.now().date() + timedelta(days=1)
    appointments = Appointment.objects.filter(
        date__date=tomorrow,
        reminder_sent=False  # Añadir este campo al modelo
    )
    
    for appointment in appointments:
        send_appointment_reminder(appointment)
        appointment.reminder_sent = True
        appointment.save()

# Añadir al modelo Appointment
def send_appointment_reminder(appointment):
    """Envía recordatorio de cita"""
    subject = f'Recordatorio: Visita escolar mañana - {appointment.stage.name}'
    context = {
        'appointment': appointment,
        'visitor_name': appointment.visitor_name,
        'date': appointment.date,
        'staff': appointment.staff.user.get_full_name()
    }
    
    html_message = render_to_string('emails/appointment_reminder.html', context)
    
    send_mail(
        subject=subject,
        message='',
        html_message=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[appointment.visitor_email],
        fail_silently=False
    )