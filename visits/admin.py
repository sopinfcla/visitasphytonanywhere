from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import SchoolStage, StaffProfile, Appointment, AvailabilitySlot

@admin.register(SchoolStage)
class SchoolStageAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'staff_count']
    search_fields = ['name']
    
    def staff_count(self, obj):
        return obj.staffprofile_set.count()
    staff_count.short_description = 'Personal asignado'

@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_full_name', 'get_stages', 'active_slots_count']
    list_filter = ['allowed_stages']
    search_fields = ['user__first_name', 'user__last_name', 'user__email']
    filter_horizontal = ['allowed_stages']
    
    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Nombre completo'
    
    def get_stages(self, obj):
        return ", ".join([stage.name for stage in obj.allowed_stages.all()])
    get_stages.short_description = 'Etapas asignadas'
    
    def active_slots_count(self, obj):
        return obj.availabilityslot_set.filter(is_active=True).count()
    active_slots_count.short_description = 'Slots activos'

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['visitor_name', 'stage', 'staff', 'formatted_date', 'visitor_email', 'visitor_phone']
    list_filter = ['stage', 'staff', 'date']
    search_fields = ['visitor_name', 'visitor_email', 'visitor_phone']
    date_hierarchy = 'date'
    readonly_fields = ['created_at']
    
    def formatted_date(self, obj):
        # Convertir la hora de la cita a la zona horaria local configurada (por ejemplo, Europe/Madrid)
        local_dt = timezone.localtime(obj.date)
        return local_dt.strftime("%d/%m/%Y %H:%M")
    formatted_date.short_description = 'Fecha y hora'

@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(admin.ModelAdmin):
    list_display = ['staff', 'stage', 'formatted_date', 'formatted_time', 'duration', 'is_active', 'repeat_type']
    list_filter = ['staff', 'stage', 'is_active', 'repeat_type', 'date']
    search_fields = ['staff__user__first_name', 'staff__user__last_name']
    date_hierarchy = 'date'
    list_editable = ['is_active']
    
    def formatted_date(self, obj):
        if obj.date:
            return obj.date.strftime("%d/%m/%Y")
        return '-'
    formatted_date.short_description = 'Fecha'
    
    def formatted_time(self, obj):
        return f"{obj.start_time.strftime('%H:%M')} - {obj.end_time.strftime('%H:%M')}"
    formatted_time.short_description = 'Horario'
    
    fieldsets = (
        ('Información básica', {
            'fields': ('staff', 'stage', 'duration', 'is_active')
        }),
        ('Programación', {
            'fields': ('repeat_type', 'date', 'start_time', 'end_time'),
            'classes': ('wide',)
        }),
        ('Repetición semanal', {
            'fields': ('month', 'weekday'),
            'classes': ('collapse',),
            'description': 'Solo para slots semanales'
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is None:  # Para nuevos slots
            if request.user.is_superuser:
                return form
            try:
                staff_profile = StaffProfile.objects.get(user=request.user)
                form.base_fields['staff'].initial = staff_profile
                form.base_fields['staff'].disabled = True
                form.base_fields['stage'].queryset = staff_profile.allowed_stages.all()
            except StaffProfile.DoesNotExist:
                pass
        return form
    
    def has_change_permission(self, request, obj=None):
        if not obj or request.user.is_superuser:
            return True
        return obj.staff.user == request.user
    
    def has_delete_permission(self, request, obj=None):
        if not obj or request.user.is_superuser:
            return True
        return obj.staff.user == request.user
