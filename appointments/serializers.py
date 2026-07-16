from rest_framework import serializers
from .models import Appointment
from django.utils import timezone
from .utils import encrypt, decrypt
from users.models import User


class ParticipantSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name', 'email', 'role']
        
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"


class AppointmentSerializer(serializers.ModelSerializer):
    """ Serializes appointment data and controls visibility, validation, and field access """

    student_name = serializers.SerializerMethodField()
    student_email = serializers.SerializerMethodField()
    student_sex = serializers.SerializerMethodField()
    student_phone = serializers.SerializerMethodField()
    student_dob = serializers.SerializerMethodField()
    student_address = serializers.SerializerMethodField()
    student_course = serializers.SerializerMethodField()
    student_year = serializers.SerializerMethodField()
    student_section = serializers.SerializerMethodField()
    faculty_name = serializers.SerializerMethodField()
    participants_detail = ParticipantSerializer(many=True, read_only=True, source='participants')
    
    class Meta:
        # Defines the model and fields to be serialized, with some fields set as read-only
        model = Appointment
        fields = '__all__'
        read_only_fields = ['student', 'last_status', 'created_at']

    def get_student_name(self, obj):
        if not obj.student:
            return "N/A"
        return f"{obj.student.first_name} {obj.student.last_name}"

    def get_student_email(self, obj):
        if not obj.student:
            return "N/A"
        return obj.student.email

    def get_student_sex(self, obj):
        if not obj.student:
            return "N/A"
        return obj.student.sex

    def get_student_phone(self, obj):
        if not obj.student:
            return ""
        try:
            return decrypt(obj.student.contact_number) if obj.student.contact_number else ""
        except:
            return ""

    def get_student_dob(self, obj):
        if not obj.student:
            return None
        return obj.student.date_of_birth

    def get_student_address(self, obj):
        if not obj.student:
            return ""
        try:
            return decrypt(obj.student.address) if obj.student.address else ""
        except:
            return ""

    def get_student_course(self, obj):
        if not obj.student:
            return "N/A"
        return obj.student.course

    def get_student_year(self, obj):
        if not obj.student:
            return "N/A"
        return obj.student.year

    def get_student_section(self, obj):
        if not obj.student:
            return "N/A"
        return obj.student.section

    def get_faculty_name(self, obj):
        # Returns full faculty name
        return f"{obj.faculty.first_name} {obj.faculty.last_name}"

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        user = self.context['request'].user

        is_participant = instance.participants.filter(pk=user.pk).exists() if instance.pk else False
        if user != instance.student and user.role != 'admin' and user != instance.faculty and not is_participant:
            return {
                "id": instance.id,
                "date_time": ret["date_time"],
                "status": "Busy",
                "service": "Hidden",
                "condition": "Hidden",
            }

        # Return condition as plain text (no decryption)
        if instance.condition:
            ret['condition'] = instance.condition

        if instance.student:
            try:
                ret['student_phone'] = decrypt(instance.student.contact_number) if instance.student.contact_number else ""
            except:
                ret['student_phone'] = ""

            try:
                ret['student_address'] = decrypt(instance.student.address) if instance.student.address else ""
            except:
                ret['student_address'] = "[Error]"
        else:
            ret['student_phone'] = ""
            ret['student_address'] = ""
            
            # Fetch attendance details
            attendance_records = instance.attendance_records.all()
            ret['attendance'] = {str(rec.user_id): rec.attended for rec in attendance_records}
            ret['participants_attendance'] = [
                {
                    "id": p.id,
                    "full_name": f"{p.first_name} {p.last_name}",
                    "role": p.role,
                    "attended": next((rec.attended for rec in attendance_records if rec.user_id == p.id), False)
                }
                for p in instance.participants.all()
            ]

        return ret

    def validate(self, data):
        instance = self.instance
        user = self.context['request'].user

        # If booking is created by faculty/dean, automatically set faculty = user
        if user.role in ['faculty', 'dean'] and not instance:
            data['faculty'] = user

        # Validates appointment scheduling rules
        dt = data.get('date_time')
        fac = data.get('faculty', self.instance.faculty if self.instance else None)   

        # Prevent past scheduling
        if dt:
            if dt.replace(second=0, microsecond=0) < timezone.now().replace(second=0, microsecond=0):
                raise serializers.ValidationError("You cannot schedule appointments in the past.")

        check_dt = dt if dt else (instance.date_time if instance else None)

        if not check_dt or not fac:
         raise serializers.ValidationError("Faculty and Date/Time are required.")
        
        # Prevent double booking for the same faculty at the same time
        overlap = Appointment.objects.filter(faculty=fac, date_time=dt, status__in=['Pending', 'Approved', 'Completed'])
        if self.instance:
            overlap = overlap.exclude(pk=self.instance.pk)
        
        if overlap.exists():
            raise serializers.ValidationError("This time slot is already taken.")

        return data

    def create(self, validated_data):
        # Save condition as plain text
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Save condition as plain text
        return super().update(instance, validated_data)