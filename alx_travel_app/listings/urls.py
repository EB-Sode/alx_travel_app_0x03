from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ListingViewSet,
    BookingViewSet,
    InitiatePaymentView,
    PaymentCallbackView,
    index, about, contact, services
)

router = DefaultRouter()
router.register(r'listings', ListingViewSet, basename='listing')
router.register(r'bookings', BookingViewSet, basename='booking')

urlpatterns = [
    # HTML pages
    path('', index, name='index'),
    path('about/', about, name='about'),
    path('contact/', contact, name='contact'),
    path('services/', services, name='services'),

    # API routes
    path('api/', include(router.urls)),
    path('api/payment/initiate/', InitiatePaymentView.as_view(), name='initiate-payment'),
    path('api/payment/callback/', PaymentCallbackView.as_view(), name='payment-callback'),
]
