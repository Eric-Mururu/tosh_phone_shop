
from decimal import Decimal

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

from rest_framework.test import APIClient

from unittest.mock import patch

from orders.models import Order
from payments.models import Payment
from payments.services import initiate_stk_push


class STKQueryTests(TestCase):

    def setUp(self):

        User = get_user_model()

        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='testpassword123'
        )

        self.client = APIClient()

        self.client.force_authenticate(
            user=self.admin
        )

        self.order = Order.objects.create(
            customer_name='Test Customer',
            customer_phone='254712345678',
            customer_email='customer@example.com',
            delivery_address='Nairobi',
            status='pending',
            total_amount=Decimal('47000.00')
        )

        self.payment = Payment.objects.create(
            order=self.order,
            phone_number='254712345678',
            amount=Decimal('47000.00'),
            status='pending',
            merchant_request_id='TESTMERCHANT001',
            checkout_request_id='TESTCHECKOUT001'
        )

    @patch('payments.services.query_stk_status')
    def test_successful_payment(self, mock_query):

        mock_query.return_value = {
            'ResponseCode': '0',
            'MerchantRequestID': 'TESTMERCHANT001',
            'CheckoutRequestID': 'TESTCHECKOUT001',
            'ResultCode': '0',
            'ResultDesc': 'The service request is processed successfully.'
        }

        self.payment.callback_data = {
            'Body': {
                'stkCallback': {
                    'MerchantRequestID': 'TESTMERCHANT001',
                    'CheckoutRequestID': 'TESTCHECKOUT001',
                    'ResultCode': 0,
                    'ResultDesc': 'The service request is processed successfully.',
                    'CallbackMetadata': {
                        'Item': [
                            {
                                'Name': 'Amount',
                                'Value': 47000
                            },
                            {
                                'Name': 'MpesaReceiptNumber',
                                'Value': 'TESTRECEIPT001'
                            },
                            {
                                'Name': 'TransactionDate',
                                'Value': 20261118190000
                            },
                            {
                                'Name': 'PhoneNumber',
                                'Value': 254712345678
                            }
                        ]
                    }
                }
            }
        }

        self.payment.save()

        response = self.client.post(
            f'/api/payments/payments/{self.payment.id}/query/'
        )

        self.payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.payment.status, 'successful')
        self.assertEqual(self.order.status, 'paid')

    @patch('payments.services.query_stk_status')
    def test_cancelled_payment(self, mock_query):

        mock_query.return_value = {
            'ResponseCode': '0',
            'MerchantRequestID': 'TESTMERCHANT001',
            'CheckoutRequestID': 'TESTCHECKOUT001',
            'ResultCode': '1032',
            'ResultDesc': 'Request cancelled by user.'
        }

        response = self.client.post(
            f'/api/payments/payments/{self.payment.id}/query/'
        )

        self.payment.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.payment.status, 'failed')

    @patch('payments.services.query_stk_status')
    def test_pending_payment(self, mock_query):

        mock_query.return_value = {
            'ResponseCode': '0',
            'MerchantRequestID': 'TESTMERCHANT001',
            'CheckoutRequestID': 'TESTCHECKOUT001',
            'ResponseDescription': 'Query accepted'
        }

        response = self.client.post(
            f'/api/payments/payments/{self.payment.id}/query/'
        )

        self.payment.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.payment.status, 'pending')

    @override_settings(
        MPESA_CALLBACK_URL='https://example.com/callback/',
        MPESA_CONSUMER_KEY='test-key',
        MPESA_CONSUMER_SECRET='test-secret',
        MPESA_SHORTCODE='123456',
        MPESA_PASSKEY='test-passkey',
        MPESA_ENVIRONMENT='sandbox',
        MPESA_TRANSACTION_TYPE='CustomerPayBillOnline'
    )
    @patch('payments.views.initiate_stk_push')
    def test_duplicate_payment_request(
        self,
        mock_stk_push
    ):

        response = self.client.post(
            f'/api/payments/orders/{self.order.id}/stk-push/',
            {
                'phone_number': '0712345678'
            },
            format='json'
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Payment.objects.filter(
                order=self.order,
                status='pending'
            ).count(),
            1
        )

        mock_stk_push.assert_not_called()


class STKPushFlowTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.order = Order.objects.create(
            customer_name='Test Customer',
            customer_phone='254712345678',
            customer_email='customer@example.com',
            delivery_address='Nairobi',
            status='pending',
            total_amount=Decimal('47000.00')
        )

    @override_settings(
        MPESA_CALLBACK_URL='https://example.com/api/payments/callback/',
        MPESA_CONSUMER_KEY='test-key',
        MPESA_CONSUMER_SECRET='test-secret',
        MPESA_SHORTCODE='123456',
        MPESA_PASSKEY='test-passkey',
        MPESA_ENVIRONMENT='sandbox',
        MPESA_TRANSACTION_TYPE='CustomerPayBillOnline'
    )
    @patch('payments.views.initiate_stk_push')
    def test_order_checkout_starts_stk_and_returns_status_link(
        self,
        mock_stk_push
    ):
        mock_stk_push.return_value = {
            'ResponseCode': '0',
            'MerchantRequestID': 'MERCHANT-001',
            'CheckoutRequestID': 'CHECKOUT-001',
            'ResponseDescription': 'Success. Request accepted for processing'
        }

        response = self.client.post(
            f'/api/payments/orders/{self.order.id}/stk-push/',
            {'phone_number': '0712345678'},
            format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'pending')
        self.assertTrue(response.data['status_token'])
        mock_stk_push.assert_called_once_with(
            phone_number='254712345678',
            amount=47000,
            account_reference=f'ORDER{self.order.id}',
            callback_url='https://example.com/api/payments/callback/'
        )

        payment = Payment.objects.get(order=self.order)
        self.assertEqual(payment.checkout_request_id, 'CHECKOUT-001')

        status_response = self.client.get(
            f"/api/payments/status/{response.data['status_token']}/"
        )
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.data['status'], 'pending')

        invalid_status_response = self.client.get(
            f"/api/payments/status/{response.data['status_token']}tampered/"
        )
        self.assertEqual(invalid_status_response.status_code, 404)

    @override_settings(
        MPESA_CALLBACK_URL='https://example.com/api/payments/callback/',
        MPESA_CONSUMER_KEY='test-key',
        MPESA_CONSUMER_SECRET='test-secret',
        MPESA_SHORTCODE='123456',
        MPESA_PASSKEY='test-passkey',
        MPESA_ENVIRONMENT='sandbox',
        MPESA_TRANSACTION_TYPE='CustomerPayBillOnline'
    )
    @patch('payments.views.initiate_stk_push')
    def test_repeat_request_returns_existing_pending_payment(
        self,
        mock_stk_push
    ):
        payment = Payment.objects.create(
            order=self.order,
            phone_number='254712345678',
            amount=Decimal('47000.00'),
            merchant_request_id='MERCHANT-001',
            checkout_request_id='CHECKOUT-001'
        )

        response = self.client.post(
            f'/api/payments/orders/{self.order.id}/stk-push/',
            {'phone_number': '0712345678'},
            format='json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['payment_id'], payment.id)
        self.assertTrue(response.data['status_token'])
        mock_stk_push.assert_not_called()

    @override_settings(
        MPESA_CALLBACK_URL='https://example.com/api/payments/callback/',
        MPESA_CONSUMER_KEY='',
        MPESA_CONSUMER_SECRET='',
        MPESA_SHORTCODE='',
        MPESA_PASSKEY=''
    )
    @patch('payments.views.initiate_stk_push')
    def test_missing_credentials_do_not_create_pending_payment(
        self,
        mock_stk_push
    ):
        response = self.client.post(
            f'/api/payments/orders/{self.order.id}/stk-push/',
            {'phone_number': '0712345678'},
            format='json'
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn('MPESA_CONSUMER_KEY', response.data['error'])
        self.assertFalse(Payment.objects.filter(order=self.order).exists())
        mock_stk_push.assert_not_called()

    def test_successful_callback_marks_payment_and_order_paid(self):
        payment = Payment.objects.create(
            order=self.order,
            phone_number='254712345678',
            amount=Decimal('47000.00'),
            merchant_request_id='MERCHANT-001',
            checkout_request_id='CHECKOUT-001'
        )

        response = self.client.post(
            '/api/payments/callback/',
            {
                'Body': {
                    'stkCallback': {
                        'MerchantRequestID': 'MERCHANT-001',
                        'CheckoutRequestID': 'CHECKOUT-001',
                        'ResultCode': 0,
                        'ResultDesc': 'The service request is processed successfully.',
                        'CallbackMetadata': {
                            'Item': [
                                {'Name': 'Amount', 'Value': 47000},
                                {
                                    'Name': 'MpesaReceiptNumber',
                                    'Value': 'TESTRECEIPT001'
                                },
                                {
                                    'Name': 'TransactionDate',
                                    'Value': 20261118190000
                                },
                                {
                                    'Name': 'PhoneNumber',
                                    'Value': 254712345678
                                }
                            ]
                        }
                    }
                }
            },
            format='json'
        )

        payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payment.status, 'successful')
        self.assertEqual(payment.mpesa_receipt_number, 'TESTRECEIPT001')
        self.assertEqual(self.order.status, 'paid')

    def test_mismatched_callback_is_not_marked_as_paid(self):
        payment = Payment.objects.create(
            order=self.order,
            phone_number='254712345678',
            amount=Decimal('47000.00'),
            merchant_request_id='MERCHANT-001',
            checkout_request_id='CHECKOUT-001'
        )

        response = self.client.post(
            '/api/payments/callback/',
            {
                'Body': {
                    'stkCallback': {
                        'MerchantRequestID': 'MERCHANT-001',
                        'CheckoutRequestID': 'CHECKOUT-001',
                        'ResultCode': 0,
                        'ResultDesc': 'Success',
                        'CallbackMetadata': {
                            'Item': [
                                {'Name': 'Amount', 'Value': 1},
                                {
                                    'Name': 'MpesaReceiptNumber',
                                    'Value': 'TESTRECEIPT002'
                                },
                                {
                                    'Name': 'PhoneNumber',
                                    'Value': 254712345678
                                }
                            ]
                        }
                    }
                }
            },
            format='json'
        )

        payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payment.status, 'pending')
        self.assertTrue(payment.requires_reconciliation)
        self.assertEqual(self.order.status, 'pending')

    def test_cancelled_callback_marks_payment_failed(self):
        payment = Payment.objects.create(
            order=self.order,
            phone_number='254712345678',
            amount=Decimal('47000.00'),
            merchant_request_id='MERCHANT-001',
            checkout_request_id='CHECKOUT-001'
        )

        response = self.client.post(
            '/api/payments/callback/',
            {
                'Body': {
                    'stkCallback': {
                        'MerchantRequestID': 'MERCHANT-001',
                        'CheckoutRequestID': 'CHECKOUT-001',
                        'ResultCode': 1032,
                        'ResultDesc': 'Request cancelled by user.'
                    }
                }
            },
            format='json'
        )

        payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payment.status, 'failed')
        self.assertEqual(self.order.status, 'pending')


class STKPushServiceTests(TestCase):

    @override_settings(
        MPESA_SHORTCODE='600123',
        MPESA_PASSKEY='test-passkey',
        MPESA_ENVIRONMENT='sandbox',
        MPESA_TRANSACTION_TYPE='CustomerBuyGoodsOnline'
    )
    @patch('payments.services.requests.post')
    @patch('payments.services.generate_mpesa_password')
    @patch('payments.services.get_mpesa_access_token')
    def test_stk_push_uses_sandbox_till_transaction(
        self,
        mock_access_token,
        mock_password,
        mock_post
    ):
        mock_access_token.return_value = 'test-access-token'
        mock_password.return_value = ('20261119120000', 'test-password')
        mock_post.return_value.json.return_value = {
            'ResponseCode': '0'
        }

        response = initiate_stk_push(
            phone_number='254712345678',
            amount=47000,
            account_reference='ORDER1',
            callback_url='https://example.com/api/payments/callback/'
        )

        self.assertEqual(response['ResponseCode'], '0')
        args, kwargs = mock_post.call_args
        self.assertEqual(
            args[0],
            'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
        )
        self.assertEqual(kwargs['json']['TransactionType'], 'CustomerBuyGoodsOnline')
        self.assertEqual(kwargs['json']['BusinessShortCode'], '600123')
