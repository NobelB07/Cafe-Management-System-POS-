from .models import Order, Review
from .notifications import menu_notification_version, order_notification_version
from .views import get_user_role


def app_notifications(request):
    if not request.user.is_authenticated:
        return {
            'app_role': 'guest',
            'customer_basket_count': 0,
            'pending_order_count': 0,
            'unpaid_order_count': 0,
            'admin_notice_count': 0,
            'has_unseen_dashboard_notifications': False,
            'has_unseen_menu_notifications': False,
            'has_unseen_order_notifications': False,
        }

    role = get_user_role(request.user)
    show_operations = role in ('staff', 'admin')
    pending_order_count = Order.objects.filter(status='pending').count() if show_operations else 0
    unpaid_order_count = Order.objects.filter(payment_status__in=['unpaid', 'pending']).count() if show_operations else 0
    review_count = Review.objects.filter(is_visible=True).count() if role == 'admin' else 0
    menu_version = menu_notification_version()
    order_version = order_notification_version()
    has_unseen_menu_notifications = show_operations and request.session.get('seen_menu_version') != menu_version
    has_unseen_order_notifications = show_operations and request.session.get('seen_order_version') != order_version
    has_unseen_dashboard_notifications = has_unseen_menu_notifications or has_unseen_order_notifications
    basket = request.session.get('customer_basket') or {}
    basket_items = basket.get('items') or {}
    customer_basket_count = sum(int(quantity) for quantity in basket_items.values() if str(quantity).isdigit()) if role == 'customer' else 0

    return {
        'app_role': role,
        'customer_basket_count': customer_basket_count,
        'pending_order_count': pending_order_count,
        'unpaid_order_count': unpaid_order_count,
        'review_notification_count': review_count,
        'has_unseen_notifications': has_unseen_dashboard_notifications,
        'has_unseen_dashboard_notifications': has_unseen_dashboard_notifications,
        'has_unseen_menu_notifications': has_unseen_menu_notifications,
        'has_unseen_order_notifications': has_unseen_order_notifications,
        'admin_notice_count': (pending_order_count + unpaid_order_count + review_count) if role == 'admin' else 0,
    }
