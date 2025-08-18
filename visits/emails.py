# visits/emails.py
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from datetime import datetime, timedelta, time
import logging

logger = logging.getLogger(__name__)

def send_appointment_confirmation(appointment):
    """Envía emails de confirmación al visitante y al staff"""
    
    try:
        # Generar URL de cancelación
        cancel_url = f"{settings.SCHOOL_CONFIG['base_url']}{reverse('cancel_appointment', kwargs={'token': appointment.cancellation_token})}"
        
        # Contexto común
        base_context = {
            'appointment': appointment,
            'visitor_name': appointment.visitor_name,
            'date': appointment.date,
            'staff_name': appointment.staff.user.get_full_name(),
            'year': timezone.now().year,
            'school_name': settings.SCHOOL_CONFIG['name'],
            'school_address': settings.SCHOOL_CONFIG['address'],
            'school_phone': settings.SCHOOL_CONFIG['phone'],
            'cancel_url': cancel_url
        }
        
        # Email al visitante
        visitor_subject = f'Confirmación de visita - {appointment.stage.name}'
        visitor_html = render_to_string('emails/appointment_confirmation.html', base_context)
        
        send_mail(
            subject=visitor_subject,
            message='',
            html_message=visitor_html,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[appointment.visitor_email],
            fail_silently=False
        )
        
        logger.info(f"Email de confirmación enviado a {appointment.visitor_email}")

        # Email al staff (solo si tiene notificaciones activas)
        if appointment.staff.notify_new_appointment:
            staff_subject = f'Nueva visita programada - {appointment.stage.name}'
            staff_context = {
                **base_context,
                'visitor_email': appointment.visitor_email,
                'visitor_phone': appointment.visitor_phone,
            }
            
            staff_html = render_to_string('emails/staff_notification.html', staff_context)
            
            send_mail(
                subject=staff_subject,
                message='',
                html_message=staff_html,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[appointment.staff.user.email],
                fail_silently=False
            )
            
            logger.info(f"Email de notificación enviado al staff {appointment.staff.user.email}")

    except Exception as e:
        logger.error(f"Error enviando emails de confirmación para cita {appointment.id}: {str(e)}", exc_info=True)
        raise

def send_appointment_reminder(appointment):
    """Envía recordatorio 24h antes de la cita - DEPRECADO: Usar send_daily_reminders()"""
    
    try:
        # Generar URL de cancelación
        cancel_url = f"{settings.SCHOOL_CONFIG['base_url']}{reverse('cancel_appointment', kwargs={'token': appointment.cancellation_token})}"
        
        context = {
            'appointment': appointment,
            'visitor_name': appointment.visitor_name,
            'date': appointment.date,
            'staff_name': appointment.staff.user.get_full_name(),
            'year': timezone.now().year,
            'school_name': settings.SCHOOL_CONFIG['name'],
            'school_address': settings.SCHOOL_CONFIG['address'],
            'school_phone': settings.SCHOOL_CONFIG['phone'],
            'cancel_url': cancel_url
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
        
        logger.info(f"Recordatorio enviado a {appointment.visitor_email} para cita {appointment.id}")
        
    except Exception as e:
        logger.error(f"Error enviando recordatorio para cita {appointment.id}: {str(e)}", exc_info=True)
        raise

def send_appointment_cancellation(appointment, cancelled_by='family'):
    """Envía notificación de cancelación a ambas partes"""
    
    try:
        base_context = {
            'appointment': appointment,
            'visitor_name': appointment.visitor_name,
            'date': appointment.date,
            'staff_name': appointment.staff.user.get_full_name(),
            'year': timezone.now().year,
            'school_name': settings.SCHOOL_CONFIG['name'],
            'school_address': settings.SCHOOL_CONFIG['address'],
            'school_phone': settings.SCHOOL_CONFIG['phone'],
            'cancelled_by': cancelled_by
        }
        
        # Email a la familia
        family_subject = f'Cita cancelada - {appointment.stage.name}'
        family_html = render_to_string('emails/appointment_cancelled_family.html', base_context)
        
        send_mail(
            subject=family_subject,
            message='',
            html_message=family_html,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[appointment.visitor_email],
            fail_silently=False
        )
        
        logger.info(f"Email de cancelación enviado a familia {appointment.visitor_email}")

        # Email al staff
        staff_subject = f'Cita cancelada - {appointment.stage.name}'
        staff_context = {
            **base_context,
            'visitor_email': appointment.visitor_email,
            'visitor_phone': appointment.visitor_phone,
        }
        
        staff_html = render_to_string('emails/appointment_cancelled_staff.html', staff_context)
        
        send_mail(
            subject=staff_subject,
            message='',
            html_message=staff_html,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[appointment.staff.user.email],
            fail_silently=False
        )
        
        logger.info(f"Email de cancelación enviado al staff {appointment.staff.user.email}")

    except Exception as e:
        logger.error(f"Error enviando emails de cancelación para cita {appointment.id}: {str(e)}", exc_info=True)
        raise

def send_appointment_modification(appointment, old_date=None):
    """Envía notificación de modificación solo a la familia"""
    
    try:
        # Generar nueva URL de cancelación
        cancel_url = f"{settings.SCHOOL_CONFIG['base_url']}{reverse('cancel_appointment', kwargs={'token': appointment.cancellation_token})}"
        
        context = {
            'appointment': appointment,
            'visitor_name': appointment.visitor_name,
            'date': appointment.date,
            'old_date': old_date,
            'staff_name': appointment.staff.user.get_full_name(),
            'year': timezone.now().year,
            'school_name': settings.SCHOOL_CONFIG['name'],
            'school_address': settings.SCHOOL_CONFIG['address'],
            'school_phone': settings.SCHOOL_CONFIG['phone'],
            'cancel_url': cancel_url
        }
        
        subject = f'Cita modificada - {appointment.stage.name}'
        html_message = render_to_string('emails/appointment_modified.html', context)
        
        send_mail(
            subject=subject,
            message='',
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[appointment.visitor_email],
            fail_silently=False
        )
        
        logger.info(f"Email de modificación enviado a {appointment.visitor_email}")

    except Exception as e:
        logger.error(f"Error enviando email de modificación para cita {appointment.id}: {str(e)}", exc_info=True)
        raise

# ====================================
# SISTEMA DE RECORDATORIOS DIARIOS PARA STAFF - CORREGIDO
# ====================================

def send_staff_daily_reminder(staff_profile, appointments_tomorrow):
    """Envía recordatorio diario al STAFF con todas las familias que debe atender mañana"""
    
    try:
        if not appointments_tomorrow or not staff_profile.notify_reminder:
            return
        
        context = {
            'staff_name': staff_profile.user.get_full_name(),
            'staff_email': staff_profile.user.email,
            'appointments': appointments_tomorrow,
            'total_appointments': len(appointments_tomorrow),
            'date': appointments_tomorrow[0].date.date(),
            'year': timezone.now().year,
            'school_name': settings.SCHOOL_CONFIG['name'],
            'school_address': settings.SCHOOL_CONFIG['address'],
            'school_phone': settings.SCHOOL_CONFIG['phone'],
        }
        
        # Asunto dependiendo del número de citas
        if len(appointments_tomorrow) == 1:
            subject = f'Recordatorio: 1 visita mañana - {appointments_tomorrow[0].stage.name}'
        else:
            subject = f'Recordatorio: {len(appointments_tomorrow)} visitas mañana'
        
        html_message = render_to_string('emails/staff_daily_reminder.html', context)
        
        send_mail(
            subject=subject,
            message='',
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[staff_profile.user.email],
            fail_silently=False
        )
        
        # Marcar citas como recordatorio enviado
        for appointment in appointments_tomorrow:
            appointment.reminder_sent = True
            appointment.save()
        
        logger.info(f"Recordatorio diario enviado al staff {staff_profile.user.email} para {len(appointments_tomorrow)} citas")
        
    except Exception as e:
        logger.error(f"Error enviando recordatorio diario al staff {staff_profile.user.email}: {str(e)}", exc_info=True)
        raise

def send_daily_reminders():
    """Función para enviar todos los recordatorios diarios AL STAFF - llamar desde comando o tarea"""
    
    try:
        # Calcular mañana
        tomorrow = timezone.now().date() + timedelta(days=1)
        tomorrow_start = timezone.make_aware(datetime.combine(tomorrow, time.min))
        tomorrow_end = timezone.make_aware(datetime.combine(tomorrow, time.max))
        
        # Solo importar aquí para evitar import circular
        from .models import Appointment
        
        # Obtener todas las citas de mañana que no han enviado recordatorio
        appointments_tomorrow = Appointment.objects.filter(
            date__range=(tomorrow_start, tomorrow_end),
            status='pending',
            reminder_sent=False
        ).select_related('stage', 'course', 'staff__user', 'staff')
        
        if not appointments_tomorrow.exists():
            logger.info("No hay citas para enviar recordatorios mañana")
            return 0
        
        # Agrupar por STAFF (no por email del visitante)
        appointments_by_staff = {}
        for appointment in appointments_tomorrow:
            staff_id = appointment.staff.id
            if staff_id not in appointments_by_staff:
                appointments_by_staff[staff_id] = {
                    'staff_profile': appointment.staff,
                    'appointments': []
                }
            appointments_by_staff[staff_id]['appointments'].append(appointment)
        
        # Enviar un email por staff con todas sus citas
        sent_count = 0
        for staff_id, data in appointments_by_staff.items():
            staff_profile = data['staff_profile']
            appointments = data['appointments']
            
            # Solo enviar si el staff tiene recordatorios activados
            if staff_profile.notify_reminder:
                try:
                    send_staff_daily_reminder(staff_profile, appointments)
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Error enviando recordatorio al staff {staff_profile.user.email}: {str(e)}")
                    continue
            else:
                # Marcar como enviado aunque no se envíe por configuración
                for appointment in appointments:
                    appointment.reminder_sent = True
                    appointment.save()
                logger.info(f"Staff {staff_profile.user.email} tiene recordatorios desactivados - marcando como enviado")
        
        total_appointments = appointments_tomorrow.count()
        logger.info(f"Recordatorios procesados: {sent_count} emails enviados para {total_appointments} citas")
        return sent_count
        
    except Exception as e:
        logger.error(f"Error en send_daily_reminders: {str(e)}", exc_info=True)
        return 0