from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('book/', views.book_appointment, name='book_appointment'),
    path('success/', views.booking_success, name='booking_success'),
    path('referrals/create/', views.create_referral, name='create_referral'),
    path('patients/', views.patient_list, name='patient_list'),
    path(
        'patients/<int:patient_id>/',
        views.patient_profile,
        name='patient_profile'
    ),
    path(
        'appointments/<int:appointment_id>/edit/',
        views.edit_appointment,
        name='edit_appointment'
    ),
    path('calendar/', views.calendar_view, name='calendar'),
]