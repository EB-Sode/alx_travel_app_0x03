from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from listings.models import Listing
import random


class Command(BaseCommand):
    help = "Seed the database with sample listings data"

    def handle(self, *args, **options):
        # Check if a default user exists, else create one
        host, created = User.objects.get_or_create(
            username="demo_host",
            defaults={"email": "host@example.com", "password": "demo1234"}
        )

        if created:
            self.stdout.write(self.style.SUCCESS("Created demo host user"))

        # Sample data
        sample_listings = [
            {"title": "Cozy Apartment in Lagos", "description": "A modern apartment with all amenities.", "price_per_night": 75.00, "location": "Lagos, Nigeria"},
            {"title": "Beach House in Accra", "description": "Perfect spot for a seaside holiday.", "price_per_night": 150.00, "location": "Accra, Ghana"},
            {"title": "Luxury Villa in Nairobi", "description": "Spacious villa with private pool and garden.", "price_per_night": 300.00, "location": "Nairobi, Kenya"},
            {"title": "City Center Flat in Cape Town", "description": "Close to restaurants, shops, and attractions.", "price_per_night": 100.00, "location": "Cape Town, South Africa"},
            {"title": "Countryside Cottage in Enugu", "description": "Peaceful retreat surrounded by nature.", "price_per_night": 50.00, "location": "Enugu, Nigeria"},
        ]

        # Seed listings
        for data in sample_listings:
            listing, created = Listing.objects.get_or_create(
                title=data["title"],
                defaults={
                    "description": data["description"],
                    "price_per_night": data["price_per_night"],
                    "location": data["location"],
                    "host": host
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Added listing: {listing.title}"))
            else:
                self.stdout.write(self.style.WARNING(f"Listing already exists: {listing.title}"))

        self.stdout.write(self.style.SUCCESS("Database seeding completed!"))
