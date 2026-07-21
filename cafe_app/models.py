from django.db import models
from django.db.models import F, Sum
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from decimal import Decimal

USD_TO_NPR_RATE = Decimal('133.25')
COUPON_DISCOUNT_LIMIT = Decimal('2500.00')


class MenuItem(models.Model):
    CATEGORY_CHOICES = [
        ('beverages', 'Beverages'),
        ('snacks', 'Snacks'),
        ('meals', 'Meals'),
        ('desserts', 'Desserts'),
    ]

    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='menu_images/', blank=True, null=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} - Rs. {self.price}"


class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percent', 'Percent'),
        ('fixed', 'Fixed Rupees'),
    ]

    code = models.CharField(max_length=30, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal('0.01')),
            MaxValueValidator(COUPON_DISCOUNT_LIMIT),
        ],
    )
    is_active = models.BooleanField(default=True)
    usage_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text='Leave empty for unlimited use.',
    )
    used_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        if self.discount_type == 'percent':
            return f"{self.code} - {self.amount}% off"
        return f"{self.code} - Rs. {self.amount} off"

    def calculate_discount(self, subtotal):
        if self.discount_type == 'percent':
            discount = (subtotal * self.amount / Decimal('100.00')).quantize(Decimal('0.01'))
        else:
            discount = self.amount
        return min(discount, subtotal, COUPON_DISCOUNT_LIMIT)

    @property
    def remaining_uses(self):
        if self.usage_limit is None:
            return None
        return max(self.usage_limit - self.used_count, 0)

    @property
    def has_remaining_uses(self):
        return self.usage_limit is None or self.used_count < self.usage_limit

    def record_use(self):
        Coupon.objects.filter(pk=self.pk).update(used_count=F('used_count') + 1)
        self.refresh_from_db(fields=['used_count'])


class CustomerProfile(models.Model):
    MEMBERSHIP_CHOICES = [
        ('regular', 'Regular'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
        ('diamond', 'Diamond'),
    ]
    MEMBERSHIP_THRESHOLDS = [
        ('regular', 0),
        ('silver', 100),
        ('gold', 250),
        ('platinum', 500),
        ('diamond', 1000),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    membership = models.CharField(max_length=20, choices=MEMBERSHIP_CHOICES, default='regular')
    points = models.PositiveIntegerField(default=0)
    free_coffee_rewards = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_membership_display()}"

    @classmethod
    def membership_for_points(cls, points):
        membership = 'regular'
        for tier, threshold in cls.MEMBERSHIP_THRESHOLDS:
            if points >= threshold:
                membership = tier
        return membership

    @classmethod
    def membership_rank(cls, membership):
        return [tier for tier, _threshold in cls.MEMBERSHIP_THRESHOLDS].index(membership)


class Review(models.Model):
    RATING_CHOICES = [(value, f'{value} star') for value in range(1, 6)]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    comment = models.TextField()
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.rating}/5"


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('preparing', 'Preparing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('cash', 'Cash'),
        ('esewa', 'eSewa'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ]

    order_number = models.CharField(max_length=50, unique=True)
    customer_name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    coupon_code = models.CharField(max_length=30, blank=True)
    coupon_redeemed = models.BooleanField(default=False)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, default='unpaid')
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='unpaid')
    reward_points_awarded = models.BooleanField(default=False)
    esewa_reference = models.CharField(max_length=60, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.order_number} - {self.customer_name}"

    def calculate_totals(self):
        """Calculate subtotal and total for the order."""
        subtotal = Decimal('0.00')
        for item in self.items.all():
            subtotal += item.menu_item.price * item.quantity

        self.subtotal = subtotal
        if self.coupon and self.coupon.is_active:
            self.discount = self.coupon.calculate_discount(subtotal)
            self.coupon_code = self.coupon.code
        elif not self.coupon:
            self.discount = Decimal('0.00')
            self.coupon_code = ''

        self.tax = Decimal('0.00')
        self.total = max(self.subtotal - self.discount, Decimal('0.00'))
        self.save()

    @property
    def is_paid(self):
        return self.payment_status == 'paid'

    def save(self, *args, **kwargs):
        if self.payment_status == 'paid' and self.status != 'cancelled':
            self.status = 'completed'
            update_fields = kwargs.get('update_fields')
            if update_fields is not None:
                kwargs['update_fields'] = set(update_fields) | {'status', 'updated_at'}
        super().save(*args, **kwargs)
        if self.payment_status == 'paid' and self.coupon and not self.coupon_redeemed:
            self.coupon.record_use()
            self.coupon_redeemed = True
            Order.objects.filter(pk=self.pk).update(coupon_redeemed=True)
        if self.payment_status == 'paid' and not self.reward_points_awarded:
            self.award_customer_rewards()

    def award_customer_rewards(self):
        if not self.created_by_id:
            return
        if self.created_by.is_staff or self.created_by.is_superuser:
            return
        if self.created_by.groups.filter(name='Staff').exists():
            return

        item_count = self.items.aggregate(total=Sum('quantity'))['total'] or 0
        if item_count <= 0:
            return

        profile, _created = CustomerProfile.objects.get_or_create(user=self.created_by)
        current_rank = CustomerProfile.membership_rank(profile.membership)
        profile.points += item_count
        new_membership = CustomerProfile.membership_for_points(profile.points)
        new_rank = CustomerProfile.membership_rank(new_membership)

        update_fields = ['points', 'updated_at']
        if new_rank > current_rank:
            profile.membership = new_membership
            profile.free_coffee_rewards += 1
            update_fields.extend(['membership', 'free_coffee_rewards'])

        profile.save(update_fields=update_fields)
        self.reward_points_awarded = True
        Order.objects.filter(pk=self.pk).update(reward_points_awarded=True)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    price_at_order = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.menu_item.name} x {self.quantity}"

    @property
    def line_total(self):
        return self.price_at_order * self.quantity

    def save(self, *args, **kwargs):
        self.price_at_order = self.menu_item.price
        super().save(*args, **kwargs)
