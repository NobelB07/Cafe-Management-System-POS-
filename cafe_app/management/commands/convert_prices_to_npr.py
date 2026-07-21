from decimal import Decimal

from django.core.management.base import BaseCommand

from cafe_app.models import MenuItem, Order, OrderItem, USD_TO_NPR_RATE


class Command(BaseCommand):
    help = "Convert old small dollar-style demo prices to Nepali rupees once."

    def handle(self, *args, **options):
        converted_menu = 0
        converted_items = 0

        for item in MenuItem.objects.all():
            if item.price < Decimal('100.00'):
                item.price = (item.price * USD_TO_NPR_RATE).quantize(Decimal('0.01'))
                item.save(update_fields=['price'])
                converted_menu += 1

        for order_item in OrderItem.objects.select_related('menu_item'):
            if order_item.price_at_order < Decimal('100.00'):
                order_item.price_at_order = (order_item.price_at_order * USD_TO_NPR_RATE).quantize(Decimal('0.01'))
                order_item.save(update_fields=['price_at_order'])
                converted_items += 1

        for order in Order.objects.all():
            order.calculate_totals()

        self.stdout.write(
            self.style.SUCCESS(
                f"Converted {converted_menu} menu prices and {converted_items} order item prices to NPR."
            )
        )
