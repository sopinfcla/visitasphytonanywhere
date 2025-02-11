# visits/emails.py
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone

def send_appointment_confirmation(appointment):
    """Envía emails de confirmación al visitante y al staff"""
    
    # Email al visitante
    subject = f'Confirmación de visita - {appointment.stage.name}'
    context = {
        'appointment': appointment,
        'visitor_name': appointment.visitor_name,
        'date': appointment.date,
        'staff': appointment.staff.user.get_full_name(),
        'year': timezone.now().year
    }
    
    html_message = render_to_string('emails/appointment_confirmation.html', context)
    
    send_mail(
        subject=subject,
        message='',
        html_message=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[appointment.visitor_email],
        fail_silently=False
    )

    # Email al staff
    staff_subject = f'Nueva visita programada - {appointment.stage.name}'
    staff_context = {
        'appointment': appointment,
        'visitor_name': appointment.visitor_name,
        'visitor_email': appointment.visitor_email,
        'visitor_phone': appointment.visitor_phone,
        'date': appointment.date,
        'staff': appointment.staff,
        'year': timezone.now().year
    }
    
    staff_html_message = render_to_string('emails/staff_notification.html', staff_context)
    
    send_mail(
        subject=staff_subject,
        message='',
        html_message=staff_html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[appointment.staff.user.email],
        fail_silently=False
    )

def send_appointment_reminder(appointment):
    """Envía recordatorio 24h antes de la cita"""
    context = {
        'appointment': appointment,
        'visitor_name': appointment.visitor_name,
        'date': appointment.date,
        'staff': appointment.staff.user.get_full_name(),
        'year': timezone.now().year
    }
    
    html_message = render_to_string('emails/appointment_reminder.html', context)
    
    send_mail(
        subject=f'Recordatorio: Visita escolar mañana - {appointment.stage.name}',
        message='',
        html_message=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[appointment.visitor_email],
        fail_silently=False
    )