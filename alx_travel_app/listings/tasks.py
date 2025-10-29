# listings/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from .models import Payment
from django.conf import settings

@shared_task
def send_payment_confirmation_email(payment_id):
    try:
        payment = Payment.objects.get(id=payment_id)
        subject = "Booking Payment Confirmation"
        message = f"Hello {payment.user.first_name},\n\nYour payment of {payment.amount} {payment.currency} for booking has been successfully processed.\n\nThank you!"
        recipient = [payment.user.email]
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient)
        return f"Payment confirmation email sent to {payment.user.email}"
    except Payment.DoesNotExist:
        return f"Payment with ID {payment_id} not found."


@shared_task
def send_booking_confirmation_email(to_email, booking_id, listing_name):
    """
    Sends a booking confirmation email after a successful booking creation.
    """
    subject = f'Booking Confirmation - {listing_name}'
    
    message = f'Your booking (ID: {booking_id}) for {listing_name} has been confirmed!'
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [to_email],
        fail_silently=False,
    )
    return f"Booking confirmation email sent to {to_email}"
