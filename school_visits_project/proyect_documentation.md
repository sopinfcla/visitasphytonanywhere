Sistema de Gestión de Visitas Escolares
Descripción General
Aplicación web estilo Bookings/Calendly para gestionar visitas escolares, permitiendo a las familias reservar citas para conocer diferentes etapas educativas del colegio.
Estructura del Proyecto
Copyschool_visits/
├── school_visits_project/
│   ├── settings.py
│   └── urls.py
├── visits/
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── serializers.py
│   ├── admin.py
│   ├── emails.py        # Pendiente
│   └── tasks.py         # Pendiente
└── templates/
    └── visits/
        ├── dashboard.html
        ├── public_booking.html
        ├── stage_booking.html
        ├── book_appointment.html
        ├── appointment_confirmation.html
        ├── staff_availability.html
        ├── privacy_policy.html
Especificaciones Técnicas
Stack Tecnológico

Backend: Django 5.1.5 + Django REST Framework
Frontend: Bootstrap + FullCalendar
Base de datos: SQLite (desarrollo)
UI: Diseño responsive inspirado en Calendly

Etapas Educativas y Personal
Etapas

Escuela Infantil (guardería)
Infantil (segundo ciclo)
Primaria
Secundaria
Bachillerato

Personal y Permisos

Chus: Solo Escuela Infantil
Regina: Solo Primaria
Elisa: Solo Secundaria
Sonia: Escuela Infantil + Infantil
Juanjo: Todas las etapas (Director global)

Funcionalidades Implementadas ✅

Sistema Base

Modelos y relaciones
Admin Django configurado
Usuarios y perfiles creados
Estructura base de templates


Sistema de Reservas

Landing page con grid de etapas
Calendario estilo Calendly
Selección de slots en dos pasos
Formulario de reserva con política de privacidad
Confirmación de reserva
Slots paralelos para diferentes profesores


Gestión de Disponibilidad

CRUD slots individuales y recurrentes
Validaciones automáticas staff-etapa
Generación de slots para todas las etapas asignadas
UI con FullCalendar


Panel de Staff

Vista básica de citas
Gestión de disponibilidad
Permisos por etapa



Funcionalidades Pendientes ⏳

Sistema de Emails

Configuración SMTP
Templates HTML responsive
Notificaciones automatizadas:

Confirmación de reserva
Recordatorios 24h antes
Cancelaciones
Resumen semanal para staff




Gestión Avanzada de Citas

Sistema de notas y comentarios
Adjuntar archivos
Estados de seguimiento
Histórico de cambios


Panel de Staff Mejorado

Edición de perfil
Gestión de etapas asignadas
Dashboard con estadísticas
Filtros avanzados de citas


Mantenimiento

Limpieza automática de slots pasados
Backup de datos
Logs del sistema



Modelos Actuales
SchoolStage
pythonCopyclass SchoolStage(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
StaffProfile
pythonCopyclass StaffProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    allowed_stages = models.ManyToManyField(SchoolStage)
AvailabilitySlot
pythonCopyclass AvailabilitySlot(models.Model):
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE)
    stage = models.ForeignKey(SchoolStage, on_delete=models.CASCADE)
    date = models.DateField(null=True, blank=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    duration = models.IntegerField()
    is_active = models.BooleanField(default=True)
    repeat_type = models.CharField(max_length=10, choices=['once', 'weekly'])
Appointment
pythonCopyclass Appointment(models.Model):
    stage = models.ForeignKey(SchoolStage, on_delete=models.CASCADE)
    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE)
    visitor_name = models.CharField(max_length=200)
    visitor_email = models.EmailField()
    visitor_phone = models.CharField(max_length=20)
    date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
Modelos Pendientes
MeetingNote
pythonCopyclass MeetingNote(models.Model):
    appointment = models.ForeignKey(Appointment)
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
MeetingAttachment
pythonCopyclass MeetingAttachment(models.Model):
    appointment = models.ForeignKey(Appointment)
    file = models.FileField(upload_to='meeting_attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
MeetingFollowUp
pythonCopyclass MeetingFollowUp(models.Model):
    STATUS_CHOICES = [
        ('interested', 'Interesados'),
        ('pending', 'Pendiente decisión'),
        ('confirmed', 'Confirman matriculación'),
        ('rejected', 'No interesados'),
    ]
    appointment = models.ForeignKey(Appointment)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    comments = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
Próximos Sprints
Sprint 1: Sistema de Emails (Alta Prioridad)

Configuración Base

Setup servidor SMTP
Templates base HTML
Sistema de cola de emails


Implementación de Notificaciones

Email de confirmación de cita
Recordatorios automáticos
Notificaciones al staff



Sprint 2: Gestión Avanzada de Citas

Sistema de Notas

CRUD de notas
Rich text editor
Historial de cambios


Gestión de Archivos

Upload de archivos
Previsualización
Control de tamaño/tipo


Sistema de Seguimiento

Estados configurables
Comentarios de seguimiento
Filtros y búsquedas



Sprint 3: Panel de Staff Mejorado

Perfil de Usuario

Edición de datos personales
Cambio de contraseña
Gestión de etapas


Dashboard Mejorado

Vista de calendario
Filtros avanzados
Estadísticas básicas



Restricciones y Consideraciones

Emails HTML responsive
Archivos: max 10MB, tipos permitidos: PDF, DOC, DOCX, JPG, PNG
Backup diario de BD
Logging de acciones importantes
RGPD: Aceptación explícita y gestión de datos

Deuda Técnica

Tests unitarios y de integración
Documentación API
Optimización de queries
Sistema de caché
Monitorización y logs






Sistema de Gestión de Citas para Padres Nuevos en el Colegio

Requisitos Generales

Reserva de Citas: Cuando se realice una reserva, se enviará automáticamente un correo electrónico tanto al padre/madre como al director correspondiente para confirmar la reunión.

Gestión de Citas:

Cada cita será gestionada como un objeto individual, permitiendo:

Modificar los detalles de la reunión.

Borrar la cita si es necesario.

Tomar notas asociadas a la reunión.

Subir y gestionar archivos relacionados con la cita.

Eliminación Automática de Slots Pasados: Los slots de disponibilidad cuya fecha ya haya pasado serán eliminados automáticamente para mantener la base de datos limpia y actualizada.

Funcionalidades para Directores

Gestión de Perfil:

Actualización de datos personales.

Cambio de contraseña.

Gestión de las etapas educativas en las que participan.

Gestión de Disponibilidad:

Creación y actualización de slots de disponibilidad.

Eliminación de slots de disponibilidad obsoletos.

Gestión de Reuniones:

Visualización de reuniones pendientes y finalizadas.

Acceso a la ficha de cada reunión, donde podrán:

Añadir anotaciones.

Adjuntar archivos relevantes.

Hacer un seguimiento de la familia interesada en la institución.

Consideraciones Técnicas

La plataforma debe permitir la automatización de notificaciones y confirmaciones vía correo electrónico.

El sistema debe ser intuitivo, responsive y fácil de usar tanto para los padres como para los directores.

Se debe asegurar la seguridad de los datos, especialmente en la gestión de información confidencial de las familias y directores.

Próximos Pasos

Evaluar la mejor tecnología para la implementación (Power Apps, Django, SharePoint u otra alternativa).

Establecer flujos de trabajo y permisos de usuario.

Diseñar una interfaz accesible y funcional para todos los usuarios.

Implementar la lógica de gestión de disponibilidad y reservas.

Configurar el sistema de notificaciones y automatización de emails.