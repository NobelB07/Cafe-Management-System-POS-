from django.db.models import Max

from .models import MenuItem, Order


def _version_for(queryset):
    latest = queryset.aggregate(latest=Max('updated_at'))['latest']
    latest_value = latest.isoformat() if latest else 'none'
    return f"{queryset.count()}:{latest_value}"


def menu_notification_version():
    return _version_for(MenuItem.objects.all())


def order_notification_version():
    return _version_for(Order.objects.all())


def mark_menu_seen(request):
    request.session['seen_menu_version'] = menu_notification_version()


def mark_orders_seen(request):
    request.session['seen_order_version'] = order_notification_version()


def mark_operations_seen(request):
    mark_menu_seen(request)
    mark_orders_seen(request)
