"""
Load products from a JSON file (name + price) into the Product model.
Usage: python manage.py load_products [path/to/products.json]
Default path: products.json in project root (same folder as manage.py).
"""
import json
import os
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand

from product.models import Product


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
            Product.objects.create(
                title=title,
                price=price,
                status="ACTIVE",
                position=i + 1,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Inserted {created} products from {path}."))
