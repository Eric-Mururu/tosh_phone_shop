import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from products.models import Phone


@override_settings(CSRF_TRUSTED_ORIGINS=['http://localhost:5173'])
class CheckoutCsrfTests(TestCase):

    def test_authenticated_checkout_accepts_bootstrapped_csrf_token(self):
        user = get_user_model().objects.create_user(
            username='checkout-customer',
            password='test-password'
        )
        phone = Phone.objects.create(
            name='Test phone',
            brand='Test brand',
            description='Test product',
            price='47000.00',
            stock=1
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)

        csrf_response = client.get('/api/csrf/')
        csrf_token = csrf_response.json()['csrfToken']

        response = client.post(
            '/api/orders/',
            data=json.dumps({
                'customer_name': 'Test Customer',
                'customer_phone': '254712345678',
                'customer_email': 'customer@example.com',
                'delivery_address': 'Nairobi',
                'items': [{'phone': phone.pk, 'quantity': 1}]
            }),
            content_type='application/json',
            HTTP_ORIGIN='http://localhost:5173',
            HTTP_X_CSRFTOKEN=csrf_token
        )

        self.assertEqual(csrf_response.status_code, 200)
        self.assertIn('csrftoken', csrf_response.cookies)
        self.assertEqual(response.status_code, 201)
