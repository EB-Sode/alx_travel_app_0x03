from django.shortcuts import render
from .serializers import ListingSerializer, BookingSerializer
from rest_framework import viewsets
from .models import Listing, Booking, Payment
import uuid
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.contrib.auth import get_user_model
from .tasks import send_payment_confirmation_email, send_booking_confirmation_email

User = get_user_model()

# Use CHAPA_BASE_URL from settings
CHAPA_INIT_URL = f"{settings.CHAPA_BASE_URL}transaction/initialize"

# Create your views here.
class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.all()
    serializer_class = ListingSerializer
    lookup_field = 'slug'

def index(request):
    return render(request, 'index.html')

def about(request):
    return render(request, 'about.html')

def contact(request):
    return render(request, 'contact.html')

def services(request):
    return render(request, 'services.html')


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = serializer.save(user=request.user)

        # Initiate payment for the booking
        amount = serializer.validated_data.get("total_price")  # Assuming you have total_price field
        email = request.user.email
        first_name = request.user.first_name
        last_name = request.user.last_name
        description = f"Payment for booking #{booking.id}"

        # Generate unique transaction reference
        tx_ref = str(uuid.uuid4())

        payload = {
            "amount": amount,
            "currency": "ETB",
            "tx_ref": tx_ref,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "callback_url": f"{settings.SITE_URL}/api/payment/callback/",
            "metadata": {
                "description": description,
                "booking_id": booking.id
            }
        }

        headers = {
            "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(CHAPA_INIT_URL, json=payload, headers=headers)
            response_data = response.json()

            if response.status_code != 200 or response_data.get("status") != "success":
                return Response({"error": "Failed to initialize payment", "details": response_data}, status=status.HTTP_400_BAD_REQUEST)

            # Store payment in DB
            payment = Payment.objects.create(
                user=request.user,
                tx_ref=tx_ref,
                chapa_tx_id=response_data["data"]["id"],
                amount=amount,
                currency="ETB",
                status="pending",
                description=description
            )

            # ✅ Trigger background email notification via Celery
            send_booking_confirmation_email.delay(email, booking.id, first_name, amount)

            return Response({
                "booking": BookingSerializer(booking).data,
                "payment_url": response_data["data"]["checkout_url"],
                "payment_status": payment.payment_status,
                "tx_ref": tx_ref
            }, status=status.HTTP_201_CREATED)

        except requests.exceptions.RequestException as e:
            return Response({"error": "Payment service unavailable", "details": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class InitiatePaymentView(APIView):
    """
    API endpoint to initiate a Chapa payment for a booking.
    """

    def post(self, request):
        user = request.user
        data = request.data
        amount = data.get("amount")
        currency = data.get("currency", "ETB")
        email = data.get("email")
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")
        description = data.get("description", "")

        if not all([amount, email]):
            return Response(
                {"error": "Amount and email are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate unique transaction reference
        tx_ref = str(uuid.uuid4())

        # Prepare data for Chapa API
        payload = {
            "amount": amount,
            "currency": currency,
            "tx_ref": tx_ref,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "callback_url": f"{settings.SITE_URL}/api/payment/callback/",
            "metadata": {
                "description": description,
                "user_id": user.id
            }
        }

        headers = {
            "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(CHAPA_INIT_URL, json=payload, headers=headers)
            response_data = response.json()

            if response.status_code != 200 or response_data.get("status") != "success":
                return Response(
                    {"error": "Failed to initialize payment.", "details": response_data},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Store payment in database
            payment = Payment.objects.create(
                user=user,
                tx_ref=tx_ref,
                chapa_tx_id=response_data["data"]["id"],
                amount=amount,
                currency=currency,
                status="pending",
                description=description
            )



            return Response({
                "payment_url": response_data["data"]["checkout_url"],
                "tx_ref": tx_ref,
                "status": payment.payment_status
            })

        except requests.exceptions.RequestException as e:
            return Response(
                {"error": "Payment service unavailable.", "details": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )


class PaymentCallbackView(APIView):
    def get(self, request):
        tx_ref = request.GET.get("tx_ref")
        if not tx_ref:
            return Response({"error": "tx_ref is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Verify with Chapa
            verify_url = f"{settings.CHAPA_BASE_URL}transaction/verify/{tx_ref}"
            headers = {"Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"}
            response = requests.get(verify_url, headers=headers)
            data = response.json()

            payment = Payment.objects.get(tx_ref=tx_ref)

            if response.status_code == 200 and data.get("status") == "success":
                payment.payment_status = "success"
                payment.chapa_tx_id = data["data"]["id"]
                payment.save()

                # Trigger confirmation email via Celery
                send_payment_confirmation_email.delay(payment.id)

                return Response({"message": "Payment successful", "payment_status": payment.payment_status})
            else:
                payment.payment_status = "failed"
                payment.save()
                return Response({"message": "Payment failed", "payment_status": payment.payment_status})

        except Payment.DoesNotExist:
            return Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)
        except requests.exceptions.RequestException as e:
            return Response({"error": "Payment verification failed", "details": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
