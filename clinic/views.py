from datetime import datetime, time, timedelta

from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import (
    Appointment,
    AppointmentType,
    Clinician,
    Department,
    Patient,
    Referral,
)


def dashboard(request):
    today = timezone.localdate()

    today_appointments = Appointment.objects.filter(
        start_time__date=today,
        status='booked'
    ).order_by('start_time')

    upcoming_appointments = Appointment.objects.filter(
        start_time__date__gt=today,
        status='booked'
    ).order_by('start_time')[:5]

    recent_referrals = Referral.objects.select_related(
        'patient',
        'referred_from',
        'referred_to_department'
    ).order_by('-created_at')[:5]

    urgent_referrals = Referral.objects.select_related(
        'patient',
        'referred_from',
        'referred_to_department'
    ).filter(status='pending').order_by('-created_at')[:3]

    context = {
        'total_patients': Patient.objects.count(),
        'total_clinicians': Clinician.objects.count(),
        'total_appointments': Appointment.objects.count(),
        'pending_referrals': Referral.objects.filter(status='pending').count(),
        'today_appointments': today_appointments,
        'upcoming_appointments': upcoming_appointments,
        'recent_referrals': recent_referrals,
        'urgent_referrals': urgent_referrals,
    }

    return render(request, 'clinic/dashboard.html', context)


def book_appointment(request):
    if request.method == 'POST':
        start_time = parse_datetime(request.POST.get('start_time'))

        if timezone.is_naive(start_time):
            start_time = timezone.make_aware(start_time)

        appointment = Appointment.objects.create(
            patient_id=request.POST.get('patient'),
            clinician_id=request.POST.get('clinician'),
            appointment_type_id=request.POST.get('appointment_type'),
            start_time=start_time,
            notes=request.POST.get('notes'),
        )

        print(f"""
SMS SENT:
Patient: {appointment.patient.full_name}
File Number: {appointment.patient.file_number}
Appointment: {appointment.start_time}
Clinician: {appointment.clinician.name}
""")

        return redirect('booking_success')

    selected_date = request.GET.get('date')
    selected_time = request.GET.get('time')
    initial_datetime = None

    if selected_date and selected_time:
        initial_datetime = datetime.strptime(
            f'{selected_date} {selected_time}',
            '%Y-%m-%d %H:%M'
        )

    context = {
        'patients': Patient.objects.all(),
        'clinicians': Clinician.objects.all(),
        'appointment_types': AppointmentType.objects.all(),
        'initial_datetime': initial_datetime,
    }

    return render(request, 'clinic/book_appointment.html', context)


def booking_success(request):
    return render(request, 'clinic/success.html')


def create_referral(request):
    if request.method == 'POST':
        Referral.objects.create(
            patient_id=request.POST.get('patient'),
            referred_from_id=request.POST.get('referred_from'),
            referred_to_department_id=request.POST.get(
                'referred_to_department'
            ),
            reason=request.POST.get('reason'),
        )

        return redirect('dashboard')

    context = {
        'patients': Patient.objects.all(),
        'clinicians': Clinician.objects.all(),
        'departments': Department.objects.all(),
    }

    return render(request, 'clinic/create_referral.html', context)


def patient_list(request):
    patients = Patient.objects.all().order_by('full_name')
    return render(request, 'clinic/patient_list.html', {'patients': patients})


def patient_profile(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)

    appointments = Appointment.objects.filter(
        patient=patient
    ).order_by('-start_time')

    referrals = Referral.objects.filter(
        patient=patient
    ).order_by('-created_at')

    context = {
        'patient': patient,
        'appointments': appointments,
        'referrals': referrals,
    }

    return render(request, 'clinic/patient_profile.html', context)


def edit_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if request.method == 'POST':
        appointment.status = request.POST.get('status')
        appointment.notes = request.POST.get('notes')
        appointment.save()

        return redirect('patient_profile', patient_id=appointment.patient.id)

    context = {
        'appointment': appointment,
    }

    return render(request, 'clinic/edit_appointment.html', context)


def calendar_view(request):
    selected_date = request.GET.get('date')

    if selected_date:
        calendar_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    else:
        calendar_date = timezone.localdate()

    appointments = Appointment.objects.filter(
        start_time__date=calendar_date
    ).order_by('start_time')

    time_slots = []
    current_time = datetime.combine(calendar_date, time(8, 0))
    end_day = datetime.combine(calendar_date, time(16, 0))

    while current_time < end_day:
        slot_appointments = appointments.filter(
            start_time__time=current_time.time()
        )

        time_slots.append({
            'time': current_time.strftime('%H:%M'),
            'appointments': slot_appointments,
        })

        current_time += timedelta(minutes=30)

    context = {
        'calendar_date': calendar_date,
        'time_slots': time_slots,
    }

    return render(request, 'clinic/calendar.html', context)