from django.contrib import admin
from .models import Coupon, CustomerProfile, MenuItem, Order, OrderItem, Review


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('price_at_order',)


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'is_available', 'created_at']
    list_filter = ['category', 'is_available']
    search_fields = ['name', 'description']
    list_editable = ['is_available']


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'amount', 'usage_limit', 'used_count', 'remaining_uses_display', 'is_active', 'created_at']
    list_filter = ['discount_type', 'is_active']
    search_fields = ['code']
    list_editable = ['usage_limit', 'is_active']
    readonly_fields = ['used_count']

    @admin.display(description='Remaining')
    def remaining_uses_display(self, obj):
        remaining = obj.remaining_uses
        return 'Unlimited' if remaining is None else remaining


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'membership', 'points', 'free_coffee_rewards', 'updated_at']
    list_filter = ['membership']
    search_fields = ['user__username']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'rating', 'is_visible', 'created_at']
    list_filter = ['rating', 'is_visible', 'created_at']
    search_fields = ['user__username', 'comment']
    list_editable = ['is_visible']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'customer_name', 'status', 'payment_method', 'payment_status', 'reward_points_awarded', 'total', 'created_at']
    list_filter = ['status', 'payment_method', 'payment_status', 'created_at']
    search_fields = ['order_number', 'customer_name']
    readonly_fields = ['order_number', 'created_at', 'updated_at', 'esewa_reference', 'reward_points_awarded']
    inlines = [OrderItemInline]
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'menu_item', 'quantity', 'price_at_order']
    list_filter = ['menu_item__category']
