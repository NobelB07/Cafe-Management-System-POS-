from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .models import CustomerProfile, MenuItem, Order, OrderItem


class CustomerRewardTests(TestCase):
    def setUp(self):
        Group.objects.create(name='Customer')
        Group.objects.create(name='Staff')
        self.customer = User.objects.create_user(username='customer', password='pass')
        self.customer.groups.add(Group.objects.get(name='Customer'))
        self.item = MenuItem.objects.create(
            name='Test Coffee',
            price=Decimal('100.00'),
            category='beverages',
            is_available=True,
        )

    def create_paid_order(self, quantity):
        order = Order.objects.create(
            order_number=f'TEST-{quantity}',
            customer_name=self.customer.username,
            created_by=self.customer,
        )
        OrderItem.objects.create(order=order, menu_item=self.item, quantity=quantity)
        order.calculate_totals()
        order.payment_method = 'cash'
        order.payment_status = 'paid'
        order.save()
        return order

    def test_paid_customer_order_awards_item_quantity_once(self):
        order = self.create_paid_order(5)
        profile = CustomerProfile.objects.get(user=self.customer)

        self.assertEqual(profile.points, 5)
        self.assertEqual(profile.membership, 'regular')
        self.assertEqual(profile.free_coffee_rewards, 0)

        order.notes = 'Saved again after payment'
        order.save()
        profile.refresh_from_db()
        order.refresh_from_db()

        self.assertTrue(order.reward_points_awarded)
        self.assertEqual(profile.points, 5)

    def test_membership_upgrade_at_threshold_adds_one_free_coffee_reward(self):
        profile = CustomerProfile.objects.create(
            user=self.customer,
            points=995,
            membership='platinum',
            free_coffee_rewards=2,
        )

        self.create_paid_order(5)
        profile.refresh_from_db()

        self.assertEqual(profile.points, 1000)
        self.assertEqual(profile.membership, 'diamond')
        self.assertEqual(profile.free_coffee_rewards, 3)


class CustomerBasketTests(TestCase):
    def setUp(self):
        Group.objects.create(name='Customer')
        Group.objects.create(name='Staff')
        self.customer = User.objects.create_user(username='basket-customer', password='pass')
        self.customer.groups.add(Group.objects.get(name='Customer'))
        self.item = MenuItem.objects.create(
            name='Basket Coffee',
            price=Decimal('150.00'),
            category='beverages',
            is_available=True,
        )

    def test_customer_can_remove_item_from_basket_before_ordering(self):
        self.client.login(username='basket-customer', password='pass')
        order_url = reverse('customer_order_create')

        self.client.post(order_url, {
            'action': 'add',
            'menu_item': self.item.pk,
            'quantity': 2,
            'notes': '',
        })
        session = self.client.session
        self.assertEqual(session['customer_basket']['items'][str(self.item.pk)], 2)

        self.client.post(order_url, {
            'action': 'remove',
            'menu_item': self.item.pk,
        })
        session = self.client.session
        self.assertNotIn(str(self.item.pk), session['customer_basket']['items'])

        self.client.post(order_url, {
            'action': 'place_order',
            'notes': '',
        })
        self.assertEqual(Order.objects.count(), 0)

    def test_add_to_basket_returns_customer_to_same_page(self):
        self.client.login(username='basket-customer', password='pass')
        next_url = reverse('menu_list')

        response = self.client.post(reverse('customer_order_create'), {
            'action': 'add',
            'next': next_url,
            'menu_item': self.item.pk,
            'quantity': 1,
            'notes': '',
        })

        self.assertRedirects(response, next_url)

    def test_top_navigation_shows_empty_basket(self):
        self.client.login(username='basket-customer', password='pass')

        response = self.client.get(reverse('customer_portal'))

        self.assertContains(response, 'Basket Empty')
