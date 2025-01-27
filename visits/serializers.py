# visits/serializers.py

from rest_framework import serializers
from .models import Appointment

class AppointmentSerializer(serializers.ModelSerializer):
   title = serializers.SerializerMethodField()
   start = serializers.SerializerMethodField()
   
   class Meta:
       model = Appointment
       fields = ['id', 'title', 'start', 'visitor_name', 'visitor_email', 'visitor_phone']
       
   def get_title(self, obj):
       return f"{obj.visitor_name} - {obj.stage.name}"
       
   def get_start(self, obj):
       return obj.date