from rest_framework import serializers
from .models import Listing, Booking


class ListingSerializer(serializers.ModelSerializer):
    host = serializers.ReadOnlyField(source="host.username")

    class Meta:
        model = Listing
        fields = ["id",
                  "title",
                  "description",
                  "price_per_night",
                  "location",
                  "created_at",
                  "host"]


class BookingSerializer(serializers.ModelSerializer):
    guest = serializers.ReadOnlyField(source="guest.username")
    listing = serializers.ReadOnlyField(source="listing.title")

    class Meta:
        model = Booking
        fields = ["id",
                  "listing",
                  "guest",
                  "check_in",
                  "check_out",
                  "created_at",
                  "total_price"]
