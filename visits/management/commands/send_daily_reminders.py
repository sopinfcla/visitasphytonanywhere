from django.core.management.base import BaseCommand
from django.utils import timezone
from visits.emails import send_daily_reminders
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Envía recordatorios diarios: FAMILIAS (24h antes) + STAFF (si notify_reminder=True)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar qué se haría sin enviar emails realmente'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('🔔 SISTEMA DE RECORDATORIOS DIARIOS'))
        self.stdout.write(f'📅 Fecha: {timezone.now().strftime("%d/%m/%Y %H:%M")}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  MODO SIMULACIÓN - No se enviarán emails reales'))
        
        self.stdout.write('=' * 70)
        
        try:
            if dry_run:
                # MODO SIMULACIÓN
                from visits.models import Appointment
                from datetime import datetime, timedelta, time
                
                tomorrow = timezone.now().date() + timedelta(days=1)
                tomorrow_start = timezone.make_aware(datetime.combine(tomorrow, time.min))
                tomorrow_end = timezone.make_aware(datetime.combine(tomorrow, time.max))
                
                appointments_tomorrow = Appointment.objects.filter(
                    date__range=(tomorrow_start, tomorrow_end),
                    status='pending'
                ).select_related('stage', 'course', 'staff__user', 'staff')
                
                if not appointments_tomorrow.exists():
                    self.stdout.write(self.style.WARNING('📭 No hay citas para mañana'))
                    self.stdout.write('=' * 70)
                    return
                
                self.stdout.write('')
                self.stdout.write(self.style.SUCCESS(f'📋 CITAS PARA MAÑANA: {appointments_tomorrow.count()}'))
                self.stdout.write('')
                
                # ========== FAMILIAS ==========
                self.stdout.write(self.style.SUCCESS('👨‍👩‍👧 RECORDATORIOS A FAMILIAS:'))
                family_count = 0
                for apt in appointments_tomorrow:
                    if not apt.reminder_sent:
                        family_count += 1
                        self.stdout.write(f'   ✉️  {apt.visitor_name} ({apt.visitor_email}) - {apt.stage.name} - {apt.date.strftime("%H:%M")}')
                
                if family_count == 0:
                    self.stdout.write('   ℹ️  Todos los recordatorios ya fueron enviados')
                else:
                    self.stdout.write(f'\n   📧 Total: {family_count} emails a familias')
                
                # ========== STAFF ==========
                self.stdout.write('')
                self.stdout.write(self.style.SUCCESS('👥 RECORDATORIOS A STAFF:'))
                
                # Agrupar por staff
                appointments_by_staff = {}
                for appointment in appointments_tomorrow:
                    staff_id = appointment.staff.id
                    if staff_id not in appointments_by_staff:
                        appointments_by_staff[staff_id] = {
                            'staff_name': appointment.staff.user.get_full_name(),
                            'staff_email': appointment.staff.user.email,
                            'notify_reminder': appointment.staff.notify_reminder,
                            'appointments': []
                        }
                    appointments_by_staff[staff_id]['appointments'].append(appointment)
                
                staff_emails_count = 0
                for staff_id, data in appointments_by_staff.items():
                    status_icon = "✅" if data['notify_reminder'] else "❌"
                    status_text = "SE ENVIARÁ" if data['notify_reminder'] else "DESACTIVADO"
                    
                    self.stdout.write(f'   {status_icon} {data["staff_name"]} ({data["staff_email"]})')
                    self.stdout.write(f'      └─ {len(data["appointments"])} citas - {status_text}')
                    
                    if data['notify_reminder']:
                        staff_emails_count += 1
                        for apt in data["appointments"]:
                            self.stdout.write(f'         • {apt.visitor_name} - {apt.stage.name} - {apt.date.strftime("%H:%M")}')
                
                self.stdout.write(f'\n   📧 Total: {staff_emails_count} emails a staff')
                
                # RESUMEN
                self.stdout.write('')
                self.stdout.write('=' * 70)
                self.stdout.write(self.style.SUCCESS('📊 RESUMEN DE SIMULACIÓN:'))
                self.stdout.write(f'   📧 Familias: {family_count} emails')
                self.stdout.write(f'   👥 Staff: {staff_emails_count} emails')
                self.stdout.write(f'   📋 Total citas: {appointments_tomorrow.count()}')
                self.stdout.write('=' * 70)
                
            else:
                # ENVÍO REAL
                result = send_daily_reminders()
                
                self.stdout.write('')
                self.stdout.write(self.style.SUCCESS('✅ RECORDATORIOS ENVIADOS:'))
                self.stdout.write(f'   📧 Emails a familias: {result.get("family_emails", 0)}')
                if result.get("family_emails_failed", 0) > 0:
                    self.stdout.write(self.style.WARNING(f'   ⚠️  Emails fallidos (familias): {result["family_emails_failed"]}'))
                
                self.stdout.write(f'   👥 Emails a staff: {result.get("staff_emails", 0)}')
                if result.get("staff_emails_skipped", 0) > 0:
                    self.stdout.write(f'   ℹ️  Staff omitidos (desactivado): {result["staff_emails_skipped"]}')
                
                self.stdout.write(f'   📋 Total citas mañana: {result.get("total_appointments", 0)}')
                self.stdout.write('')
                
                if result.get('error'):
                    self.stdout.write(self.style.ERROR(f'❌ Error: {result["error"]}'))
                else:
                    self.stdout.write(self.style.SUCCESS('🎉 Proceso completado exitosamente'))
                
                self.stdout.write('=' * 70)
                    
        except Exception as e:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR(f'❌ ERROR CRÍTICO: {str(e)}'))
            self.stdout.write('=' * 70)
            logger.error(f'Error en comando send_daily_reminders: {str(e)}', exc_info=True)
            raise