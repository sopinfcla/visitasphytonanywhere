from django.db import migrations
import uuid

def populate_cancellation_tokens(apps, schema_editor):
    Appointment = apps.get_model('visits', 'Appointment')
    for appointment in Appointment.objects.all():
        appointment.cancellation_token = uuid.uuid4()
        appointment.save()

def reverse_populate_cancellation_tokens(apps, schema_editor):
    # No need to reverse, tokens can stay
    pass

class Migration(migrations.Migration):
    dependencies = [
       ('visits', '0003_appointment_cancellation_token_and_more'),
    ]

    operations = [
        migrations.RunPython(
            populate_cancellation_tokens,
            reverse_populate_cancellation_tokens,
        ),
    ]