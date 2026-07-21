from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group, User
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from decimal import Decimal
from functools import wraps
from uuid import uuid4

from .models import Coupon, CustomerProfile, MenuItem, Order, OrderItem, Review
from .forms import AdminUserCreateForm, CouponCodeForm, CustomerOrderForm, MenuItemForm, OrderForm, OrderItemForm, PaymentMethodForm, ReviewForm
from .notifications import mark_menu_seen, mark_operations_seen, mark_orders_seen


ROLE_GROUPS = ['Customer', 'Staff']


def ensure_role_groups():
    for name in ROLE_GROUPS:
        Group.objects.get_or_create(name=name)


def get_user_role(user):
    if not user.is_authenticated:
        return 'guest'
    if user.is_superuser or user.is_staff:
        return 'admin'
    if user.groups.filter(name='Staff').exists():
        return 'staff'
    return 'customer'


def get_customer_profile(user):
    profile, _created = CustomerProfile.objects.get_or_create(user=user)
    return profile


def is_admin(user):
    return get_user_role(user) == 'admin'


def is_staff_or_admin(user):
    return get_user_role(user) in ('staff', 'admin')


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            role = get_user_role(request.user)
            if role not in roles:
                messages.error(request, 'You do not have permission to open that section.')
                return redirect('customer_portal' if role == 'customer' else 'dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


@login_required
def dashboard(request):
    if not is_staff_or_admin(request.user):
        return redirect('customer_portal')
    mark_operations_seen(request)

    today = timezone.now().date()

    # Today's stats
    today_orders = Order.objects.filter(created_at__date=today)
    today_revenue = today_orders.filter(status='completed').aggregate(
        total=Sum('total')
    )['total'] or Decimal('0.00')
    
    # Order counts
    pending_orders = Order.objects.filter(status='pending').count()
    completed_orders = Order.objects.filter(status='completed').count()
    
    # Most ordered items
    most_ordered = OrderItem.objects.values('menu_item__name').annotate(
        total_quantity=Sum('quantity')
    ).order_by('-total_quantity')[:5]

    status_counts = {
        status: Order.objects.filter(status=status).count()
        for status, _label in Order.STATUS_CHOICES
    }
    max_status_count = max([*status_counts.values(), 1])
    status_chart = [
        {
            'key': status,
            'label': label,
            'count': status_counts[status],
            'percent': round((status_counts[status] / max_status_count) * 100),
        }
        for status, label in Order.STATUS_CHOICES
    ]

    category_counts = {
        item['menu_item__category']: item['total_quantity']
        for item in OrderItem.objects.values('menu_item__category').annotate(
            total_quantity=Sum('quantity')
        )
    }
    max_category_count = max([*category_counts.values(), 1])
    category_chart = [
        {
            'key': category,
            'label': label,
            'count': category_counts.get(category, 0),
            'percent': round((category_counts.get(category, 0) / max_category_count) * 100),
        }
        for category, label in MenuItem.CATEGORY_CHOICES
    ]

    total_orders = Order.objects.count()
    total_revenue = Order.objects.filter(status='completed').aggregate(
        total=Sum('total')
    )['total'] or Decimal('0.00')
    avg_order_value = (total_revenue / completed_orders) if completed_orders else Decimal('0.00')

    context = {
        'today_orders_count': today_orders.count(),
        'today_revenue': today_revenue,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'total_orders': total_orders,
        'avg_order_value': avg_order_value,
        'most_ordered': most_ordered,
        'status_chart': status_chart,
        'category_chart': category_chart,
        'is_admin': request.user.is_staff,
    }
    return render(request, 'cafe_app/dashboard.html', context)


@login_required
def customer_portal(request):
    menu_items = MenuItem.objects.filter(is_available=True)[:6]
    profile = get_customer_profile(request.user)
    reviews = Review.objects.filter(is_visible=True)[:5]
    customer_orders = Order.objects.filter(created_by=request.user).prefetch_related('items__menu_item')[:6]

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.save()
            messages.success(request, 'Thank you for your review.')
            return redirect('customer_portal')
    else:
        form = ReviewForm()

    return render(request, 'cafe_app/customer_portal.html', {
        'menu_items': menu_items,
        'profile': profile,
        'review_form': form,
        'reviews': reviews,
        'customer_orders': customer_orders,
    })


def get_customer_basket(request):
    basket = request.session.get('customer_basket')
    if not basket:
        basket = {'items': {}, 'notes': ''}
    basket.setdefault('items', {})
    basket.setdefault('notes', '')
    return basket


def save_customer_basket(request, basket):
    request.session['customer_basket'] = basket
    request.session.modified = True


def get_safe_next_url(request, fallback='customer_order_create'):
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return next_url
    return fallback


def get_customer_basket_summary(basket):
    item_ids = [int(item_id) for item_id in basket['items'].keys() if str(item_id).isdigit()]
    menu_items = MenuItem.objects.filter(pk__in=item_ids, is_available=True)
    menu_item_map = {item.pk: item for item in menu_items}
    basket_items = []
    subtotal = Decimal('0.00')

    for item_id, quantity in basket['items'].items():
        if not str(item_id).isdigit():
            continue
        menu_item = menu_item_map.get(int(item_id))
        if not menu_item:
            continue
        quantity = int(quantity)
        line_total = menu_item.price * quantity
        subtotal += line_total
        basket_items.append({
            'menu_item': menu_item,
            'quantity': quantity,
            'line_total': line_total,
        })

    total = subtotal
    return basket_items, subtotal, total


@login_required
def customer_order_create(request):
    if get_user_role(request.user) != 'customer':
        return redirect('order_create')

    basket = get_customer_basket(request)

    if request.method == 'POST':
        action = request.POST.get('action', 'add')

        if action == 'remove':
            menu_item_id = request.POST.get('menu_item')
            if menu_item_id in basket['items']:
                basket['items'].pop(menu_item_id)
                save_customer_basket(request, basket)
                messages.success(request, 'Item removed from your basket.')
            return redirect('customer_order_create')

        if action == 'place_order':
            basket['notes'] = request.POST.get('notes', '').strip()
            basket_items, _subtotal, _total = get_customer_basket_summary(basket)
            if not basket_items:
                messages.error(request, 'Add at least one item before sending your order.')
                return redirect('customer_order_create')

            order = Order.objects.create(
                order_number='TEMP',
                customer_name=request.user.username,
                notes=basket['notes'],
                created_by=request.user,
                status='pending',
            )
            order.order_number = f"ORD-{order.id:04d}"
            order.save(update_fields=['order_number'])
            for basket_item in basket_items:
                OrderItem.objects.create(
                    order=order,
                    menu_item=basket_item['menu_item'],
                    quantity=basket_item['quantity'],
                )
            order.calculate_totals()
            request.session.pop('customer_basket', None)
            request.session.modified = True
            messages.success(request, f'Your order {order.order_number} was sent to staff.')
            return redirect('customer_portal')

        form = CustomerOrderForm(request.POST)
        if form.is_valid():
            menu_item_id = str(form.cleaned_data['menu_item'].pk)
            quantity = form.cleaned_data['quantity']
            basket['items'][menu_item_id] = basket['items'].get(menu_item_id, 0) + quantity
            basket['notes'] = form.cleaned_data['notes']
            save_customer_basket(request, basket)
            messages.success(request, f'{form.cleaned_data["menu_item"].name} added to your basket.')
            return redirect(get_safe_next_url(request))
    else:
        form = CustomerOrderForm(initial={'menu_item': request.GET.get('menu_item')})

    basket_items, basket_subtotal, basket_total = get_customer_basket_summary(basket)
    return render(request, 'cafe_app/customer_order_form.html', {
        'form': form,
        'basket_items': basket_items,
        'basket_subtotal': basket_subtotal,
        'basket_total': basket_total,
        'basket_notes': basket['notes'],
    })


@role_required('admin')
def admin_portal(request):
    mark_operations_seen(request)
    ensure_role_groups()
    users = list(User.objects.all().order_by('-is_superuser', '-is_staff', 'username'))
    role_counts = {
        'admin': sum(1 for user in users if get_user_role(user) == 'admin'),
        'staff': sum(1 for user in users if get_user_role(user) == 'staff'),
        'customer': sum(1 for user in users if get_user_role(user) == 'customer'),
    }
    user_rows = [
        {
            'user': user,
            'role': get_user_role(user),
            'profile': get_customer_profile(user),
            'can_change': not user.is_superuser or user.pk == request.user.pk,
        }
        for user in users
    ]
    context = {
        'user_rows': user_rows,
        'role_counts': role_counts,
        'pending_orders': Order.objects.filter(status='pending').count(),
        'unpaid_orders': Order.objects.filter(payment_status__in=['unpaid', 'pending']).count(),
        'coupons': Coupon.objects.count(),
        'reviews': Review.objects.select_related('user')[:10],
        'review_count': Review.objects.count(),
        'add_user_form': AdminUserCreateForm(),
    }
    return render(request, 'cafe_app/admin_portal.html', context)


def apply_user_role_and_membership(user, role, membership, is_active=True):
    ensure_role_groups()
    staff_group = Group.objects.get(name='Staff')
    customer_group = Group.objects.get(name='Customer')

    user.groups.remove(staff_group, customer_group)
    user.is_active = is_active

    if role == 'admin':
        user.is_staff = True
        user.groups.add(staff_group)
    elif role == 'staff':
        user.is_staff = False
        user.groups.add(staff_group)
    else:
        user.is_staff = False
        user.groups.add(customer_group)

    if user.is_superuser:
        user.is_staff = True

    user.save()
    profile = get_customer_profile(user)
    if membership in dict(CustomerProfile.MEMBERSHIP_CHOICES):
        profile.membership = membership
        profile.save(update_fields=['membership', 'updated_at'])


@role_required('admin')
def admin_user_create(request):
    if request.method == 'POST':
        form = AdminUserCreateForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
            )
            apply_user_role_and_membership(
                user,
                form.cleaned_data['role'],
                form.cleaned_data['membership'],
                form.cleaned_data['is_active'],
            )
            messages.success(request, f'User {user.username} created.')
        else:
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)

    return redirect('admin_portal')


@role_required('admin')
def user_role_update(request, user_id):
    ensure_role_groups()
    target = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        role = request.POST.get('role')
        membership = request.POST.get('membership', 'regular')
        is_active = request.POST.get('is_active') == 'on'

        if target.is_superuser:
            messages.error(request, 'Superuser accounts always remain admins.')
            return redirect('admin_portal')

        if target.pk == request.user.pk and not is_active:
            messages.error(request, 'You cannot deactivate your own account.')
            return redirect('admin_portal')

        apply_user_role_and_membership(target, role, membership, is_active)
        messages.success(request, f'{target.username} role updated.')

    return redirect('admin_portal')


# Menu Management Views
@login_required
def menu_list(request):
    if is_staff_or_admin(request.user):
        mark_menu_seen(request)
    menu_items = MenuItem.objects.all()
    category_filter = request.GET.get('category')
    
    if category_filter:
        menu_items = menu_items.filter(category=category_filter)
    
    context = {
        'menu_items': menu_items,
        'category_filter': category_filter,
        'is_admin': request.user.is_staff,
    }
    return render(request, 'cafe_app/menu_list.html', context)


@role_required('admin')
def menu_create(request):
    if request.method == 'POST':
        form = MenuItemForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Menu item created successfully!')
            return redirect('menu_list')
    else:
        form = MenuItemForm()
    
    return render(request, 'cafe_app/menu_form.html', {'form': form, 'action': 'Create'})


@role_required('admin')
def menu_edit(request, pk):
    menu_item = get_object_or_404(MenuItem, pk=pk)
    if request.method == 'POST':
        form = MenuItemForm(request.POST, request.FILES, instance=menu_item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Menu item updated successfully!')
            return redirect('menu_list')
    else:
        form = MenuItemForm(instance=menu_item)
    
    return render(request, 'cafe_app/menu_form.html', {'form': form, 'action': 'Edit'})


@role_required('admin')
def menu_delete(request, pk):
    menu_item = get_object_or_404(MenuItem, pk=pk)
    if request.method == 'POST':
        menu_item.delete()
        messages.success(request, 'Menu item deleted successfully!')
        return redirect('menu_list')
    
    return render(request, 'cafe_app/menu_confirm_delete.html', {'menu_item': menu_item})


# Order Management Views
@role_required('staff', 'admin')
def order_list(request):
    mark_orders_seen(request)
    status_filter = request.GET.get('status')
    orders = Order.objects.all()
    
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    context = {
        'orders': orders,
        'status_filter': status_filter,
        'is_admin': request.user.is_staff,
    }
    return render(request, 'cafe_app/order_list.html', context)


@role_required('staff', 'admin')
def order_create(request):
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.created_by = request.user
            order.save()
            
            # Generate order number
            order.order_number = f"ORD-{order.id:04d}"
            order.save()
            
            messages.success(request, f'Order {order.order_number} created! Now add items.')
            return redirect('order_detail', pk=order.pk)
    else:
        form = OrderForm()
    
    return render(request, 'cafe_app/order_form.html', {'form': form, 'action': 'Create'})


@role_required('staff', 'admin')
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    menu_items = MenuItem.objects.filter(is_available=True)
    
    if request.method == 'POST':
        item_form = OrderItemForm(request.POST)
        if item_form.is_valid():
            menu_item = item_form.cleaned_data['menu_item']
            quantity = item_form.cleaned_data['quantity']
            
            # Check if item already exists in order
            existing_item = order.items.filter(menu_item=menu_item).first()
            if existing_item:
                existing_item.quantity += quantity
                existing_item.save()
            else:
                OrderItem.objects.create(
                    order=order,
                    menu_item=menu_item,
                    quantity=quantity
                )
            
            order.calculate_totals()
            messages.success(request, 'Item added to order!')
            return redirect('order_detail', pk=order.pk)
    else:
        item_form = OrderItemForm()
    
    context = {
        'order': order,
        'menu_items': menu_items,
        'item_form': item_form,
        'coupon_form': CouponCodeForm(),
        'payment_form': PaymentMethodForm(initial={'payment_method': order.payment_method if order.payment_method != 'unpaid' else 'cash'}),
        'is_admin': request.user.is_staff,
    }
    return render(request, 'cafe_app/order_detail.html', context)


@role_required('staff', 'admin')
def order_update_status(request, pk):
    order = get_object_or_404(Order, pk=pk)
    new_status = request.POST.get('status')
    
    if new_status in ['pending', 'preparing', 'completed', 'cancelled']:
        order.status = new_status
        order.save()
        messages.success(request, f'Order status updated to {new_status}!')
    
    return redirect('order_detail', pk=order.pk)


@role_required('staff', 'admin')
def order_verify(request, pk):
    order = get_object_or_404(Order, pk=pk)

    if request.method == 'POST':
        if order.status == 'pending':
            order.status = 'preparing'
            order.save(update_fields=['status', 'updated_at'])
            messages.success(request, f'Order {order.order_number} verified and moved to preparing.')
        else:
            messages.info(request, f'Order {order.order_number} is already {order.get_status_display().lower()}.')

    return redirect(request.POST.get('next') or 'order_list')


@role_required('staff', 'admin')
def order_remove_item(request, pk, item_pk):
    order = get_object_or_404(Order, pk=pk)
    item = get_object_or_404(OrderItem, pk=item_pk)
    
    if item.order == order:
        item.delete()
        order.calculate_totals()
        messages.success(request, 'Item removed from order!')
    
    return redirect('order_detail', pk=order.pk)


@role_required('staff', 'admin')
def order_apply_coupon(request, pk):
    order = get_object_or_404(Order, pk=pk)
    
    if request.method == 'POST':
        form = CouponCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code'].strip().upper()
            coupon = Coupon.objects.filter(code__iexact=code, is_active=True).first()
            if not coupon:
                messages.error(request, 'Coupon code is invalid or inactive.')
                return redirect('order_detail', pk=order.pk)
            if not coupon.has_remaining_uses:
                messages.error(request, 'Coupon code has reached its use limit.')
                return redirect('order_detail', pk=order.pk)

            order.coupon = coupon
            order.calculate_totals()
            messages.success(request, f'Coupon {coupon.code} applied.')
    
    return redirect('order_detail', pk=order.pk)


@role_required('staff', 'admin')
def order_remove_coupon(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        order.coupon = None
        order.calculate_totals()
        messages.success(request, 'Coupon removed.')
    return redirect('order_detail', pk=order.pk)


@role_required('staff', 'admin')
def order_select_payment(request, pk):
    order = get_object_or_404(Order, pk=pk)

    if not order.items.exists():
        messages.error(request, 'Add items before taking payment.')
        return redirect('order_detail', pk=order.pk)

    if request.method == 'POST':
        form = PaymentMethodForm(request.POST)
        if form.is_valid():
            payment_method = form.cleaned_data['payment_method']
            order.calculate_totals()

            if payment_method == 'cash':
                order.payment_method = 'cash'
                order.payment_status = 'paid'
                order.esewa_reference = ''
                order.save()
                messages.success(request, 'Cash payment recorded. Thank you, visit again.')
                return redirect('order_detail', pk=order.pk)

            order.payment_method = 'esewa'
            order.payment_status = 'pending'
            order.esewa_reference = f"ESEWA-{uuid4().hex[:10].upper()}"
            order.save()
            return redirect('order_esewa_payment', pk=order.pk)

    return redirect('order_detail', pk=order.pk)


@role_required('staff', 'admin')
def order_esewa_payment(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if order.payment_method != 'esewa':
        order.payment_method = 'esewa'
        order.payment_status = 'pending'
        order.esewa_reference = f"ESEWA-{uuid4().hex[:10].upper()}"
        order.save()

    return render(request, 'cafe_app/esewa_payment.html', {'order': order})


@role_required('staff', 'admin')
def order_esewa_success(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        order.payment_method = 'esewa'
        order.payment_status = 'paid'
        if not order.esewa_reference:
            order.esewa_reference = f"ESEWA-{uuid4().hex[:10].upper()}"
        order.save()
        messages.success(request, 'eSewa payment completed. Thank you, visit again.')
    return redirect('order_detail', pk=order.pk)


@role_required('staff', 'admin')
def order_invoice(request, pk):
    order = get_object_or_404(Order, pk=pk)
    context = {
        'order': order,
        'is_admin': request.user.is_staff,
    }
    return render(request, 'cafe_app/order_invoice.html', context)


# Authentication Views
def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            ensure_role_groups()
            user = form.save()
            user.groups.add(Group.objects.get(name='Customer'))
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    
    return render(request, 'cafe_app/signup.html', {'form': form})
