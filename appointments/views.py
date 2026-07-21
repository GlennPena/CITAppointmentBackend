from django.utils import timezone
from rest_framework import viewsets
from .models import Appointment
from .serializers import AppointmentSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.decorators import action
from datetime import timedelta
from django.db.models import Q
from django.shortcuts import render, get_object_or_404


class AppointmentViewSet(viewsets.ModelViewSet):
    """ Handles CRUD operations for appointments with role-based access control and validation """
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Returns appointments based on user role and filters
        user = self.request.user
        faculty_id = self.request.query_params.get('faculty')
        date_str = self.request.query_params.get('date')

        # Auto-update statuses for past appointments
        now_local = timezone.localtime(timezone.now())
        grace_cutoff = now_local - timedelta(hours=1)

        # AUTO-COMPLETE (Only if older than 1 hour)
        Appointment.objects.filter(
            status="Approved", 
            date_time__lt=grace_cutoff
        ).update(status="Completed")

        # AUTO-EXPIRE (Only if Pending and time has passed)
        Appointment.objects.filter(
            status="Pending", 
            date_time__lt=now_local
        ).update(status="Expired")

        search_query = self.request.query_params.get('search')

        # Returns faculty availability view
        if faculty_id and date_str:
            return Appointment.objects.filter(
                faculty_id=faculty_id, 
                date_time__date=date_str
            ).order_by('-date_time')

        # Returns user-specific dashboard data 
        if user.role == 'admin':
            queryset = Appointment.objects.all()
        elif user.role in ['faculty', 'dean']:
            queryset = Appointment.objects.filter(
                Q(faculty=user) | Q(participants=user)
            ).distinct()
        else:
            queryset = Appointment.objects.filter(student=user)

        # 
        if date_str:
            queryset = queryset.filter(date_time__date=date_str)

        if search_query:
            terms = search_query.strip().split()

            query = Q()
            for term in terms:
                query &= (
                    Q(student__first_name__icontains=term) |
                    Q(student__last_name__icontains=term)
                )

            queryset = queryset.filter(query)

        return queryset.order_by('-date_time')
    

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == 'student':
            serializer.save(student=user)
        else:
            # Faculty / Dean booking: set student=None, host/faculty=user, status='Approved'
            serializer.save(student=None, faculty=user, status='Approved')

    def update(self, request, *args, **kwargs):
        # Handles role-based update restrictions and status transitions
        instance = self.get_object()
        user = request.user
        new_status = request.data.get('status')

        # Student update rules
        if user.role == "student":
            if instance.student != user:
                raise PermissionDenied("Unauthorized.")
            
            # Student can only CANCEL if Pending.
            if new_status == "Cancelled":
                if instance.status != "Pending":
                    raise PermissionDenied("You can only cancel pending appointments.")
            elif new_status:
                raise PermissionDenied("You cannot change the status to " + new_status)
            
            # Prevent editing condition/date if not Pending
            if instance.status != "Pending":
                raise PermissionDenied("Approved/Completed appointments cannot be edited.")

        # Faculty / Dean update rules
        if user.role in ["faculty", "dean"]:
            is_host_or_participant = (instance.faculty == user) or instance.participants.filter(pk=user.pk).exists()
            if not is_host_or_participant:
                raise PermissionDenied("Unauthorized.")

            # Faculty can only APPROVE or REJECT if Pending.
            if new_status in ["Approved", "Rejected"]:
                if instance.status != "Pending":
                    raise PermissionDenied("Decision already made on this appointment.")
            
            # Faculty can only mark Completed if previously Approved
            elif new_status == "Completed":
                if instance.status != "Approved":
                    raise PermissionDenied("Only approved appointments can be marked as completed.")
                
                # Ensure they can't "Complete" an appointment that hasn't happened yet
                if instance.date_time > timezone.now():
                    raise PermissionDenied("You cannot complete an appointment before its scheduled time.")
            
            # Faculty can only CANCEL if previously Approved
            elif new_status == "Cancelled":
                if instance.status != "Approved":
                    raise PermissionDenied("Only previously approved appointments can be cancelled by the faculty member.")
            
            # Faculty cannot reset an appointment to pending once a decision is made
            elif new_status == "Pending" and instance.status != "Pending":
                raise PermissionDenied("Cannot reset an appointment to pending once a decision is made.")

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # Handles deletion rules based on status and role
        instance = self.get_object()
        user = request.user

        # Admin can delete anything
        if user.role == "admin":
            return super().destroy(request, *args, **kwargs)

        is_owner_or_participant = (
            (instance.student == user) or 
            (instance.faculty == user) or 
            instance.participants.filter(pk=user.pk).exists()
        )
        if not is_owner_or_participant:
            raise PermissionDenied("Unauthorized.")

        # Students and Faculty can only delete if Rejected, Cancelled, Completed, or Expired
        if instance.status not in ["Rejected", "Cancelled", "Completed", "Expired"]:
            raise PermissionDenied("Active or Pending appointments cannot be deleted.")

        return super().destroy(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'], url_path='busy-slots/(?P<faculty_id>[^/.]+)')
    def busy_slots(self, request, faculty_id=None):
        date_str = request.query_params.get('date')

        faculty_ids = [fid.strip() for fid in faculty_id.split(',') if fid.strip()]

        queryset = Appointment.objects.filter(
            Q(faculty_id__in=faculty_ids) | Q(participants__id__in=faculty_ids),
            status__in=['Pending', 'Approved'],
        ).distinct()

        if date_str:
            queryset = queryset.filter(date_time__date=date_str)

        busy_times = queryset.values_list('date_time', flat=True)

        return Response(busy_times)
    
    @action(detail=True, methods=['post'])
    def complete_appointment(self, request, pk=None):
        appointment = self.get_object()
        
        # Get data from the faculty's modal
        outcome = request.data.get('outcome', 'No outcome provided.')
        notes = request.data.get('consultation_notes', 'No specific notes provided.')
        
        appointment.status = 'Completed'
        appointment.outcome = outcome
        appointment.consultation_notes = notes
        appointment.save()

        # Handle attendance if provided
        attendance_data = request.data.get('attendance', {})
        if attendance_data:
            from .models import MeetingAttendance
            for user_id, attended in attendance_data.items():
                MeetingAttendance.objects.update_or_create(
                    appointment=appointment,
                    user_id=int(user_id),
                    defaults={'attended': bool(attended)}
                )
        
        return Response({'status': 'appointment completed'})
    
    @action(detail=True, methods=['post'])
    def rate_consultation(self, request, pk=None):
        appointment = self.get_object()
        user = request.user
        
        if appointment.student != user:
            raise PermissionDenied("Only the student who attended this consultation can rate it.")
        
        if appointment.status != 'Completed':
            raise PermissionDenied("You can only rate completed consultations.")
        
        try:
            rating_val = int(request.data.get('rating'))
            if rating_val < 1 or rating_val > 5:
                return Response({'error': 'Rating must be between 1 and 5.'}, status=400)
        except (TypeError, ValueError):
            return Response({'error': 'Invalid rating value.'}, status=400)
        
        feedback = request.data.get('rating_feedback', '').strip()
        
        appointment.rating = rating_val
        appointment.rating_feedback = feedback
        appointment.save()
        
        serializer = self.get_serializer(appointment)
        return Response(serializer.data)
    
def verify_slip_view(request, appointment_id):
    try:
        appointment = Appointment.objects.get(id=appointment_id)
    except Appointment.DoesNotExist:
        return render(request, 'appointments/verify_slip.html', {'not_found': True, 'appointment_id': appointment_id}, status=404)

    local_dt = timezone.localtime(appointment.date_time)
    
    # Build student name safely (student can be null for internal meetings)
    if appointment.student:
        full_name = f"{appointment.student.first_name} {appointment.student.last_name}"
    else:
        full_name = "N/A (Internal Meeting)"
    
    RATING_LABELS = {
        1: "1 / 5 ★☆☆☆☆ — Very Dissatisfied (Poor)",
        2: "2 / 5 ★★☆☆☆ — Dissatisfied (Below Average)",
        3: "3 / 5 ★★★☆☆ — Neutral",
        4: "4 / 5 ★★★★☆ — Satisfied (Good)",
        5: "5 / 5 ★★★★★ — Very Satisfied (Excellent)",
    }
    rating_display = RATING_LABELS.get(appointment.rating, "") if appointment.rating else None

    context = {
        'appointment': appointment,
        'full_name': full_name,
        'date': local_dt.strftime('%B %d, %Y'),
        'time': local_dt.strftime('%I:%M %p'),
        'service': appointment.service or 'General Consultation',
        'appointment_notes': appointment.condition or 'No appointment notes provided.',
        'consultation_notes': appointment.consultation_notes or 'No consultation notes recorded.',
        'rating': appointment.rating,
        'rating_display': rating_display,
        'rating_feedback': appointment.rating_feedback,
    }
    return render(request, 'appointments/verify_slip.html', context)


def verify_meeting_report_view(request, appointment_id):
    """Renders a verification page for faculty meeting reports that matches the in-app preview."""
    from .models import MeetingAttendance

    try:
        appointment = Appointment.objects.get(id=appointment_id)
    except Appointment.DoesNotExist:
        return render(request, 'appointments/verify_meeting_report.html', {'not_found': True, 'appointment_id': appointment_id}, status=404)

    local_dt = timezone.localtime(appointment.date_time)

    faculty_name = ""
    if appointment.faculty:
        faculty_name = f"{appointment.faculty.first_name} {appointment.faculty.last_name}"

    # Build participant attendance list
    participants = []
    for participant in appointment.participants.all():
        try:
            record = MeetingAttendance.objects.get(appointment=appointment, user=participant)
            attended = record.attended
        except MeetingAttendance.DoesNotExist:
            attended = False

        role = getattr(participant, 'role', 'faculty')
        participants.append({
            'full_name': f"{participant.first_name} {participant.last_name}",
            'role': 'Dean' if role == 'dean' else 'Faculty',
            'attended': attended,
        })

    context = {
        'appointment': appointment,
        'faculty_name': faculty_name,
        'date': local_dt.strftime('%B %d, %Y'),
        'time': local_dt.strftime('%I:%M %p'),
        'service': appointment.service or 'Faculty Meeting',
        'agenda': appointment.condition or 'No agenda details provided.',
        'participants': participants,
    }
    return render(request, 'appointments/verify_meeting_report.html', context)

