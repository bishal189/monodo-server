"""
Load products from a JSON file (name + price) into the Product model.
Usage: python manage.py load_products [path/to/products.json]
Default path: products.json in project root (same folder as manage.py).
When no image_url is in JSON, uses 100 real travel/hotel/destination images (rotated by product index).
"""
import json
import os
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand

from product.models import Product

# 100 real travel/hotel/destination images (Unsplash). Same set reused; product index picks image by (i % 100).
TRAVEL_IMAGE_URLS = [
    "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1611892440504-42a792e24d32?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1590490360182-c33d57733427?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1564501049412-61c2a3083791?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1571003123894-1f0594d2b5d9?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1445019980597-93fa8acb246c?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1522771739844-6a9f6d5f14af?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1566665797739-1674de7a421a?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1512918728675-ed5a9ecdebfd?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1506929562872-bb421503ef21?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1519046904884-53103b34b206?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1501785888041-af3ef285b470?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1485738422979-f5c462d49f74?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1519681393784-d120267933ba?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1504280390367-361c6d9f38f4?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1530789253388-582c481c54b0?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1478131143081-80f7f84ca84d?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1493246507139-91e8fad9978e?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1473580044384-7ba9967e16a0?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1506197603052-3cc9c3a201bd?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1518391846015-55a9cc003b25?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1516483638261-f4dbaf036963?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1523531294919-4bcd7c65e216?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1470252649378-9c29740c9fa8?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1472214103451-9374bd1c798e?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1513836279014-a89f7a76ae86?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1506929562872-bb421503ef21?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1519046904884-53103b34b206?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1501785888041-af3ef285b470?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1470252649378-9c29740c9fa8?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1493246507139-91e8fad9978e?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1519681393784-d120267933ba?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1504280390367-361c6d9f38f4?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1530789253388-582c481c54b0?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1478131143081-80f7f84ca84d?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1516483638261-f4dbaf036963?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1523531294919-4bcd7c65e216?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1472214103451-9374bd1c798e?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1513836279014-a89f7a76ae86?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1517840901100-8179e982acb7?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1611892440504-42a792e24d32?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1590490360182-c33d57733427?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1564501049412-61c2a3083791?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1571003123894-1f0594d2b5d9?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1445019980597-93fa8acb246c?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1522771739844-6a9f6d5f14af?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1566665797739-1674de7a421a?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1512918728675-ed5a9ecdebfd?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1506929562872-bb421503ef21?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1519046904884-53103b34b206?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1501785888041-af3ef285b470?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1485738422979-f5c462d49f74?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1519681393784-d120267933ba?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1504280390367-361c6d9f38f4?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1530789253388-582c481c54b0?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1478131143081-80f7f84ca84d?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1493246507139-91e8fad9978e?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1473580044384-7ba9967e16a0?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1506197603052-3cc9c3a201bd?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1518391846015-55a9cc003b25?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1516483638261-f4dbaf036963?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1523531294919-4bcd7c65e216?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1470252649378-9c29740c9fa8?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1472214103451-9374bd1c798e?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1513836279014-a89f7a76ae86?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=400&h=300&fit=crop",
    "https://images.unsplash.com/photo-1517840901100-8179e982acb7?w=400&h=300&fit=crop",
]

# Authentic-sounding hotel and travel descriptions (used when description not in JSON). Longer paragraphs.
HOTEL_DESCRIPTIONS = [
    "A cozy retreat with modern amenities and attentive service. Our rooms are designed for comfort and relaxation, with quality bedding and blackout curtains. The team is on hand around the clock to help with anything from local tips to travel arrangements. Perfect for a relaxing stay, whether you're here for business or leisure.",
    "Enjoy stunning views and comfortable rooms in a setting that feels both welcoming and refined. Our staff is dedicated to making your visit memorable, from a warm check-in to recommendations for the best nearby restaurants and sights. Many guests return year after year for the same personal touch and peaceful atmosphere.",
    "Located in a prime area with easy access to local attractions, this property puts you right where you want to be. A full breakfast is included each morning, and our common areas are ideal for meeting other travelers or catching up on work. Public transport links are just a short walk away.",
    "Boutique accommodation with real character. Each room is thoughtfully designed for your comfort, with unique decor and all the essentials you need. The building has a rich history that we're proud to share, and the neighborhood is full of cafes, shops, and cultural spots worth exploring.",
    "Peaceful setting with garden views and a calm atmosphere. Ideal for both business and leisure travelers: work from your room or from our quiet lounge, then unwind in the garden. We offer free Wi-Fi, daily housekeeping, and a simple but satisfying breakfast to start your day.",
    "Charming property with a warm welcome from the moment you arrive. Free Wi-Fi and daily housekeeping keep things simple, while the friendly team is always ready to help with directions, bookings, or local advice. The area is safe, walkable, and well connected to the rest of the city.",
    "Spacious rooms and a friendly atmosphere make this a popular choice for families and groups. We're close to restaurants and public transport, so you can easily explore without a car. The rooms are clean, well maintained, and designed to give you plenty of space to spread out.",
    "A hidden gem with personalized service and a quiet neighborhood feel. You're still only minutes from the action—shops, nightlife, and main attractions are all within easy reach. Our team takes pride in offering a stay that feels like a home away from home.",
    "Modern facilities in a classic setting: the best of both worlds. The building has character, while the rooms and common areas are updated with everything you need for a comfortable stay. It's the perfect base for exploring the area, with helpful staff and a central location.",
    "Comfortable rooms with all the essentials and a focus on value. Great location means you spend less time commuting and more time enjoying your trip. We offer a simple breakfast, free Wi-Fi, and a 24-hour front desk so you can come and go with ease.",
    "Relax in style with premium bedding, thoughtful touches, and a calm environment. Our helpful front desk is available 24/7 for any questions or requests. Whether you're here for a night or a week, we aim to make your stay as smooth and enjoyable as possible.",
    "Family-friendly with flexible room options and a welcoming vibe. On-site parking is available for those traveling by car, and we're happy to help with extra beds or cots. The area is safe and has plenty of parks and activities suitable for all ages.",
    "Escape to comfort with our well-appointed rooms and attentive service. Ideal for a short break or a longer stay: many guests extend their visit once they see how easy and relaxing it is here. Breakfast, Wi-Fi, and a friendly team are all part of the experience.",
    "Clean, comfortable, and centrally located. Guests love our breakfast and the helpful tips we share about the best local spots. We keep the property in great shape and focus on the details that make a stay feel smooth and stress-free.",
    "A welcoming stay with a homely feel. The neighborhood is quiet at night so you can rest well, but by day it's a lively area with cafes, markets, and cultural sites. Our team is happy to point you to their favorite places and help with any plans.",
    "Bright rooms and a relaxed vibe throughout the property. We're within walking distance of main sights and dining, so you can explore on foot and come back whenever you like. The rooms are simple, clean, and designed for a good night's sleep.",
    "Traditional hospitality meets modern comfort. Air-conditioned rooms and free Wi-Fi are standard, and our staff bring a warm, personal approach to everything they do. It's a place where you can feel at ease and well looked after.",
    "Small-scale hotel with big-hearted service. Perfect for couples and solo travelers who appreciate attention to detail and a peaceful atmosphere. We don't have hundreds of rooms—just a handful—so every guest gets the care and attention they deserve.",
    "Well-maintained rooms and a calm environment. Easy connections to the rest of the city mean you can explore further afield without hassle. We keep the property spotless and the common areas inviting, so you always have a comfortable place to return to.",
    "Friendly staff and a convenient location make this a favorite among repeat guests. Many visitors come back year after year for the same reliable comfort and personal touch. We're here to help with anything you need, from check-in to check-out and beyond.",
    "Simple, stylish accommodation in the heart of the area. Great for first-time visitors who want a central base and a team that can guide them. The rooms are designed to be functional and pleasant, with everything you need for a comfortable stay.",
    "Comfortable beds and a good night's sleep guaranteed. We invest in quality mattresses and bedding so you wake up refreshed. A continental breakfast is included each morning, and our staff are always on hand to help you plan your day.",
    "A peaceful stay with all you need under one roof. Ideal for a weekend getaway or a business trip: the space is quiet and well equipped, and the location makes it easy to reach meetings or attractions. We aim to make your stay as smooth as possible.",
    "Charming building with updated interiors and a lot of character. Walking distance to shops and cafes means you can step out and explore without relying on transport. Our team is proud of the property and the area and loves sharing recommendations.",
    "Reliable choice with clean rooms and a helpful team. Parking and Wi-Fi are included, and we're happy to assist with luggage, directions, or bookings. It's the kind of place where you know what to expect—comfort, cleanliness, and a warm welcome.",
    "Cozy rooms and a personal touch from the moment you arrive. Our team is happy to recommend local spots, from the best coffee to hidden gems. The property is small enough to feel intimate but well run enough to meet all your needs.",
    "Quiet location with easy access to transport, so you can explore the region without a car. The area is safe and residential, and our rooms offer a calm retreat after a day of sightseeing. We're here to help with timetables, tickets, or day-trip ideas.",
    "Warm welcome and comfortable rooms in a spot that puts many attractions within a short walk. Whether you're here for culture, food, or relaxation, you'll find something nearby. Our staff can point you in the right direction and help with any arrangements.",
    "No-fuss comfort in a great location. Ideal for travelers who want value and convenience without sacrificing cleanliness or service. We keep things straightforward: good beds, good Wi-Fi, and a team that's ready to help whenever you need it.",
    "A comfortable base for your trip with friendly service and a relaxed atmosphere. Whether you're passing through or staying a while, we aim to make you feel at home. The rooms are practical and pleasant, and the common areas are there for you to use.",
    "Well-located with a mix of comfort and practicality. Popular with repeat guests who know they can count on a clean room, a good sleep, and a helpful team. We're not the flashiest option—just a reliable one that does the job well.",
    "Clean, quiet rooms and a convenient spot for exploring. Breakfast is available daily, and our staff can suggest the best ways to get around and what to see. It's a no-nonsense stay that focuses on the things that matter most.",
    "Small and welcoming with a focus on guest comfort. Great for a short stay or a longer one if you decide to extend. We keep the property tidy and the atmosphere friendly, so you can relax and make the most of your time here.",
    "Modern rooms in a character building with a central location and 24-hour reception. You get the charm of an older property with the convenience of updated facilities. Our team is always available to help, day or night.",
    "Relaxed atmosphere and attentive service. We're close to parks and local restaurants, so you can easily mix activity with relaxation. The rooms are comfortable and well maintained, and we're happy to help with any special requests.",
    "Practical and pleasant with everything you need for a smooth stay. Free Wi-Fi throughout, comfortable beds, and a team that speaks multiple languages. It's a solid choice for travelers who want reliability and a good location.",
    "Comfortable accommodation with a homely feel. Ideal for families and groups: we have space, flexibility, and a welcoming approach. The area is safe and has something for everyone, and we're here to help you make the most of it.",
    "Quiet retreat with easy links to the city. Our garden and common areas give you space to unwind, and the transport connections make it simple to explore. Many guests appreciate the balance of peace and accessibility.",
    "Bright, airy rooms and a friendly team. We're within walking distance of key attractions, so you can leave the car behind and explore on foot. The property is kept in great condition, and we're proud of the feedback we get from guests.",
    "No surprises—just reliable comfort and good value. Recommended by many guests who appreciate the consistency and the personal touch. We focus on the basics done well: a clean room, a good sleep, and a team that cares.",
]


def get_default_description(index: int) -> str:
    """Return an authentic hotel/travel description for the given product index."""
    return HOTEL_DESCRIPTIONS[index % len(HOTEL_DESCRIPTIONS)]


class Command(BaseCommand):
    help = "Load product name and price from JSON into the products table."

    def add_arguments(self, parser):
        parser.add_argument(
            "file",
            nargs="?",
            default=os.path.join(settings.BASE_DIR, "products.json"),
            help="Path to JSON file (default: products.json in project root)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing products before loading.",
        )

    def handle(self, *args, **options):
        path = options["file"]
        clear = options["clear"]

        if not os.path.isfile(path):
            self.stderr.write(self.style.ERROR(f"File not found: {path}"))
            return

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            self.stderr.write(self.style.ERROR("JSON must be a list of objects with 'name' and 'price'."))
            return

        if clear:
            deleted, _ = Product.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing products."))

        created = 0
        for i, item in enumerate(data):
            name = item.get("name") or item.get("title")
            price_raw = item.get("price")
            image_url = item.get("image_url") or item.get("image")
            if not name:
                self.stdout.write(self.style.WARNING(f"Skip row {i + 1}: missing 'name' or 'title'."))
                continue
            if price_raw is None:
                self.stdout.write(self.style.WARNING(f"Skip row {i + 1}: missing 'price'."))
                continue
            try:
                price = Decimal(str(price_raw))
            except Exception:
                self.stdout.write(self.style.WARNING(f"Skip row {i + 1}: invalid price {price_raw!r}."))
                continue
            title = name[:200] if len(name) > 200 else name
            if isinstance(image_url, str) and image_url.strip():
                pass
            else:
                image_url = TRAVEL_IMAGE_URLS[i % len(TRAVEL_IMAGE_URLS)]
            description = item.get("description")
            if not isinstance(description, str) or not description.strip():
                description = get_default_description(i)
            else:
                description = description.strip()
            Product.objects.create(
                title=title,
                price=price,
                status="ACTIVE",
                position=i + 1,
                image_url=image_url,
                description=description,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Inserted {created} products from {path}."))
