from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from appointments.utils import encrypt, decrypt
from .models import User  


class CustomTokenSerializer(TokenObtainPairSerializer):
    """ Adds user role and details to the token """

    # Include role and user details in the token response
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        return token

    # Include user details in the token response
    def validate(self, attrs):
        data = super().validate(attrs)
        data['id'] = self.user.id
        data['role'] = self.user.role  
        data['first_name'] = self.user.first_name
        data['last_name'] = self.user.last_name
        return data
    

class UserSerializer(serializers.ModelSerializer):
    """ Handles user registration, validation, and role assignment """

    # Defines required user fields for input
    username = serializers.CharField(required=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        # Connects to the User model and specifies fields to include
        model = User
        fields = [
                'id', 'username', 'first_name', 'last_name', 'email', 
                'password', 'role', 'date_of_birth', 'sex', 'contact_number', 
                'address', 'course', 'year', 'section',
            ]

    def validate(self, data):
        is_create = self.instance is None
        role = data.get('role') or (self.instance.role if self.instance else 'student')
        errors = {}

        if role in ['student', 'patient']:
            patient_required_fields = [
                'course', 'year', 'section', 'date_of_birth', 
                'sex', 'contact_number', 'address'
            ]
            
            for field in patient_required_fields:
                if (is_create and not data.get(field)) or (field in data and not data.get(field)):
                    errors[field] = "This field is required for students."
        elif role == 'faculty':
            faculty_required_fields = [
                'date_of_birth', 'sex', 'contact_number', 'address'
            ]
            
            for field in faculty_required_fields:
                if (is_create and not data.get(field)) or (field in data and not data.get(field)):
                    errors[field] = "This field is required for faculty."
        
        if errors:
            raise serializers.ValidationError(errors)
                 
        return data

    def validate_username(self, value):
        # Checks if username already exists
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value
    
    def validate_email(self, value):
        # Checks if email already exists
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        requested_role = validated_data.get('role')

        is_admin = (request and 
                    request.user.is_authenticated and 
                    getattr(request.user, 'role', None) == 'admin')

        if requested_role == 'faculty':
            role = 'faculty'
        elif is_admin and requested_role in ['faculty', 'admin', 'dean']:
            role = requested_role
        else:
            role = 'student'

        # ENCRYPT FIELDS
        sensitive_fields = [
            'address', 'contact_number',
        ]

        for field in sensitive_fields:
            if validated_data.get(field):
                validated_data[field] = encrypt(validated_data[field])

        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            role=role,

            date_of_birth=validated_data.get('date_of_birth'),
            sex=validated_data.get('sex'),
            contact_number=validated_data.get('contact_number'),
            address=validated_data.get('address'),
            course=validated_data.get('course'),
            year=validated_data.get('year'),
            section=validated_data.get('section'),
        )

        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password is not None:
            instance.set_password(password)

        # ENCRYPT FIELDS
        sensitive_fields = [
            'address', 'contact_number',
        ]

        for field in sensitive_fields:
            if field in validated_data and validated_data[field]:
                validated_data[field] = encrypt(validated_data[field])

        return super().update(instance, validated_data)
    
    def to_representation(self, instance):
        ret = super().to_representation(instance)

        # DECRYPT FIELDS
        decrypt_fields = [
            'address', 'contact_number',
        ]

        for field in decrypt_fields:
            try:
                if ret.get(field):
                    ret[field] = decrypt(ret[field])
            except Exception:
                ret[field] = "[Decryption Error]"

        return ret


class FacultyListSerializer(serializers.ModelSerializer):
    """ List serializer for faculty with full name and role """
    full_name = serializers.SerializerMethodField()

    class Meta:
         model = User
         fields = ['id', 'full_name', 'role', 'specialization']

    def get_full_name(self, obj):
        spec = (obj.specialization or "").lower()
        role = (obj.role or "").lower()

        if "dentist" in spec:
            prefix = "Dentist"
        elif "nurse" in spec or role == "nurse":
            prefix = "Nurse"
        elif role == "dean":
            prefix = "Dean"
        elif role == "faculty":
            prefix = ""
        else:
            prefix = ""

        first = obj.first_name.title()
        last = obj.last_name.title()

        return f"{prefix} {first} {last}".strip()