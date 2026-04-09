from rest_framework import serializers
from .models import Appointment
from django.utils import timezone
from .utils import encrypt, decrypt
from users.models import User


class AppointmentSerializer(serializers.ModelSerializer):
    """ Serializes appointment data and controls visibility, validation, and encryption """

    patient_name = serializers.ReadOnlyField(source='patient.get_full_name')
    patient_email = serializers.ReadOnlyField(source='patient.email')
    patient_sex = serializers.ReadOnlyField(source='patient.sex')
    patient_phone = serializers.ReadOnlyField(source='patient.contact_number')
    patient_dob = serializers.ReadOnlyField(source='patient.date_of_birth')
    patient_address = serializers.ReadOnlyField(source='patient.address')
    patient_course = serializers.ReadOnlyField(source='patient.course')
    patient_year = serializers.ReadOnlyField(source='patient.year')
    patient_section = serializers.ReadOnlyField(source='patient.section')
    doctor_name = serializers.SerializerMethodField()
    
    class Meta:
        # Defines the model and fields to be serialized, with some fields set as read-only
        model = Appointment
        fields = '__all__'
        read_only_fields = ['patient', 'last_status', 'created_at']

    def get_patient_name(self, obj):
        # Returns full patient name
        return f"{obj.patient.first_name} {obj.patient.last_name}"

    def get_doctor_name(self, obj):
        # Returns full doctor name
        return f"{obj.doctor.first_name} {obj.doctor.last_name}"

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        user = self.context['request'].user

        if user != instance.patient and user.role != 'admin' and user != instance.doctor:
            return {
                "id": instance.id,
                "date_time": ret["date_time"],
                "status": "Busy",
                "service": "Hidden",
                "condition": "Hidden",
            }

        # Decrypt condition
        try:
            if instance.condition:
                ret['condition'] = decrypt(instance.condition)
        except:
            ret['condition'] = "Data Error"

        try:
            ret['patient_phone'] = decrypt(instance.patient.contact_number) if instance.patient.contact_number else ""
        except:
            ret['patient_phone'] = ""

        try:
            ret['patient_address'] = decrypt(instance.patient.address) if instance.patient.address else ""
        except:
            ret['patient_address'] = "[Error]"

        return ret

    def validate(self, data):
        instance = self.instance

        # Validates appointment scheduling rules
        dt = data.get('date_time')
        doc = data.get('doctor', self.instance.doctor if self.instance else None)   

        # Prevent past scheduling
        if dt:
            if dt.replace(second=0, microsecond=0) < timezone.now().replace(second=0, microsecond=0):
                raise serializers.ValidationError("You cannot schedule appointments in the past.")

        check_dt = dt if dt else (instance.date_time if instance else None)

        if not check_dt or not doc:
         raise serializers.ValidationError("Doctor and Date/Time are required.")
        
        # Prevent double booking for the same doctor at the same time
        overlap = Appointment.objects.filter(doctor=doc, date_time=dt, status__in=['Pending', 'Approved', 'Completed'])
        if self.instance:
            overlap = overlap.exclude(pk=self.instance.pk)
        
        if overlap.exists():
            raise serializers.ValidationError("This time slot is already taken.")

        return data

    def create(self, validated_data):
        # Encrypt condition before saving new appointment
        validated_data['condition'] = encrypt(validated_data.get('condition', ''))
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Encrypt condition before updating appointment
        if 'condition' in validated_data:
            validated_data['condition'] = encrypt(validated_data['condition'])
        return super().update(instance, validated_data)