from django.contrib import admin
from .models import SchoolStage, StaffProfile, Appointment

admin.site.register(SchoolStage)
admin.site.register(StaffProfile)

class AppointmentAdmin(admin.ModelAdmin):
   list_display = ['visitor_name', 'stage', 'staff', 'date']
   
   def formfield_for_foreignkey(self, db_field, request, **kwargs):
       if db_field.name == "staff":
           stage_id = request.GET.get('stage')
           if stage_id:
               kwargs["queryset"] = StaffProfile.objects.filter(allowed_stages=stage_id)
           elif request.resolver_match.kwargs.get('object_id'):
               obj = self.get_object(request, request.resolver_match.kwargs['object_id'])
               if obj and obj.stage:
                   kwargs["queryset"] = StaffProfile.objects.filter(allowed_stages=obj.stage)
       return super().formfield_for_foreignkey(db_field, request, **kwargs)

   class Media:
       js = ('admin/js/staff_filter.js',)

admin.site.register(Appointment, AppointmentAdmin)