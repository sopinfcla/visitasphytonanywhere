# visits/management/commands/send_daily_reminders.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from visits.emails import send_daily_reminders
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Envía recordatorios diarios AL STAFF con sus citas de mañana'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar qué se haría sin enviar emails realmente'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('MODO SIMULACIÓN - No se enviarán emails reales')
            )
        
        self.stdout.write(f'Iniciando envío de recordatorios diarios AL STAFF - {timezone.now()}')
        
        try:
            if dry_run:
                # Simular lo que se haría
                from visits.models import Appointment
                from datetime import datetime, timedelta, time
                
                tomorrow = timezone.now().date() + timedelta(days=1)
                tomorrow_start = timezone.make_aware(datetime.combine(tomorrow, time.min))
                tomorrow_end = timezone.make_aware(datetime.combine(tomorrow, time.max))
                
                appointments_tomorrow = Appointment.objects.filter(
                    date__range=(tomorrow_start, tomorrow_end),
                    status='pending',
                    reminder_sent=False
                ).select_related('stage', 'course', 'staff__user', 'staff')
                
                if not appointments_tomorrow.exists():
                    self.stdout.write('No hay citas para recordatorios mañana')
                    return
                
                # Agrupar por STAFF
                appointments_by_staff = {}
                for appointment in appointments_tomorrow:
                    staff_id = appointment.staff.id
                    staff_name = appointment.staff.user.get_full_name()
                    staff_email = appointment.staff.user.email
                    staff_notify = appointment.staff.notify_reminder
                    
                    if staff_id not in appointments_by_staff:
                        appointments_by_staff[staff_id] = {
                            'staff_name': staff_name,
                            'staff_email': staff_email,
                            'notify_reminder': staff_notify,
                            'appointments': []
                        }
                    appointments_by_staff[staff_id]['appointments'].append(appointment)
                
                self.stdout.write(f'Se procesarían recordatorios para {len(appointments_by_staff)} miembros del staff:')
                emails_to_send = 0
                
                for staff_id, data in appointments_by_staff.items():
                    status = "✅ SE ENVIARÍA" if data['notify_reminder'] else "❌ RECORDATORIOS DESACTIVADOS"
                    if data['notify_reminder']:
                        emails_to_send += 1
                        
                    self.stdout.write(f'  - {data["staff_name"]} ({data["staff_email"]}): {len(data["appointments"])} citas - {status}')
                    for apt in data["appointments"]:
                        self.stdout.write(f'    * {apt.visitor_name} - {apt.stage.name} - {apt.date.strftime("%H:%M")}')
                
                self.stdout.write(f'\n📧 Total emails que se enviarían: {emails_to_send}')
            else:
                # Envío real
                sent_count = send_daily_reminders()
                
                if sent_count > 0:
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Recordatorios enviados exitosamente al staff: {sent_count} emails')
                    )
                else:
                    self.stdout.write('No se enviaron recordatorios (no hay citas pendientes o staff con recordatorios activos)')
                    
        except Exception as e:
            logger.error(f"Error en comando send_daily_reminders: {str(e)}", exc_info=True)
            self.stdout.write(
                self.style.ERROR(f'❌ Error enviando recordatorios: {str(e)}')
            )
            raise