
from decimal import Decimal
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from django.conf import settings
from django.core import signing
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser

from orders.models import Order
from .models import Payment
from .serializers import STKPushSerializer
from .services import (
    initiate_stk_push,
    reconcile_payment,
    validate_mpesa_configuration,
)


PAYMENT_STATUS_TOKEN_SALT = 'payments.customer-status'


def create_payment_status_token(payment):
    return signing.dumps(
        {'payment_id': payment.pk},
        salt=PAYMENT_STATUS_TOKEN_SALT,
        compress=True
    )



class InitiateSTKPushAPIView(APIView):

    def post(self, request, order_id):

        serializer = STKPushSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data['phone_number']

        callback_url = settings.MPESA_CALLBACK_URL

        if not callback_url or not callback_url.startswith('https://'):

            return Response(
                {
                    'error': 'A public HTTPS callback URL is not configured.'
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        try:
            validate_mpesa_configuration()
        except ValueError as error:
            return Response(
                {'error': str(error)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        with transaction.atomic():

            order = get_object_or_404(
                Order.objects.select_for_update(),
                pk=order_id
            )

            if order.status != 'pending':

                return Response(
                    {
                        'error': 'This order is not available for payment.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            amount = order.total_amount

            if amount <= 0 or amount != amount.to_integral_value():

                return Response(
                    {
                        'error': 'Order amount must be a positive whole number.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            existing_payment = Payment.objects.filter(
                order=order,
                status='pending'
            ).first()

            if existing_payment:

                return Response(
                    {
                        'message': (
                            'A payment request is already in progress. '
                            'Check your phone or wait for its status.'
                        ),
                        'payment_id': existing_payment.id,
                        'order_id': order.id,
                        'amount': str(existing_payment.amount),
                        'phone_number': existing_payment.phone_number,
                        'status': existing_payment.status,
                        'status_token': create_payment_status_token(
                            existing_payment
                        ),
                        'requires_reconciliation': (
                            existing_payment.requires_reconciliation
                        )
                    },
                    status=status.HTTP_200_OK
                )

            payment = Payment.objects.create(
                order=order,
                phone_number=phone_number,
                amount=amount
            )

        try:

            mpesa_response = initiate_stk_push(
                phone_number=phone_number,
                amount=int(amount),
                account_reference=f'ORDER{order.id}',
                callback_url=callback_url
            )

        except (
            requests.RequestException,
            ValueError,
            KeyError
        ):

            payment.requires_reconciliation = True

            payment.result_description = (
                'The payment request outcome could not be confirmed. '
                'Safaricom transaction verification is required.'
            )

            payment.save(
                update_fields=[
                    'requires_reconciliation',
                    'result_description',
                    'updated_at'
                ]
            )

            return Response(
                {
                    'error': 'Unable to confirm the payment request outcome.',
                    'payment_id': payment.id,
                    'payment_status': payment.status,
                    'status_token': create_payment_status_token(payment),
                    'requires_reconciliation': True
                },
                status=status.HTTP_502_BAD_GATEWAY
            )

        if not isinstance(mpesa_response, dict):

            payment.requires_reconciliation = True

            payment.result_description = (
                'Safaricom returned an invalid response. '
                'Transaction verification is required.'
            )

            payment.save(
                update_fields=[
                    'requires_reconciliation',
                    'result_description',
                    'updated_at'
                ]
            )

            return Response(
                {
                    'error': 'Safaricom returned an invalid response.',
                    'payment_id': payment.id,
                    'payment_status': payment.status,
                    'status_token': create_payment_status_token(payment),
                    'requires_reconciliation': True
                },
                status=status.HTTP_502_BAD_GATEWAY
            )

        response_code = mpesa_response.get('ResponseCode')

        if response_code is not None and str(response_code) != '0':

            payment.status = 'failed'

            payment.result_description = mpesa_response.get(
                'ResponseDescription',
                'Safaricom rejected the payment request.'
            )

            payment.save(
                update_fields=[
                    'status',
                    'result_description',
                    'updated_at'
                ]
            )

            return Response(
                {
                    'error': 'Safaricom did not accept the payment request.',
                    'details': payment.result_description,
                    'payment_status': payment.status,
                    'payment_id': payment.id,
                    'status_token': create_payment_status_token(payment)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        merchant_request_id = mpesa_response.get(
            'MerchantRequestID'
        )

        checkout_request_id = mpesa_response.get(
            'CheckoutRequestID'
        )

        if (
            str(response_code) != '0'
            or not merchant_request_id
            or not checkout_request_id
        ):

            payment.requires_reconciliation = True

            payment.result_description = (
                'Safaricom returned an incomplete response. '
                'Transaction verification is required.'
            )

            payment.save(
                update_fields=[
                    'requires_reconciliation',
                    'result_description',
                    'updated_at'
                ]
            )

            return Response(
                {
                    'error': 'Safaricom returned an incomplete response.',
                    'payment_id': payment.id,
                    'payment_status': payment.status,
                    'status_token': create_payment_status_token(payment),
                    'requires_reconciliation': True
                },
                status=status.HTTP_502_BAD_GATEWAY
            )

        payment.merchant_request_id = merchant_request_id

        payment.checkout_request_id = checkout_request_id

        payment.result_description = mpesa_response.get(
            'ResponseDescription'
        )

        payment.save(
            update_fields=[
                'merchant_request_id',
                'checkout_request_id',
                'result_description',
                'updated_at'
            ]
        )

        return Response(
            {
                'message': 'STK Push sent successfully. Check your phone.',
                'payment_id': payment.id,
                'order_id': order.id,
                'amount': str(payment.amount),
                'phone_number': payment.phone_number,
                'status': payment.status,
                'status_token': create_payment_status_token(payment),
                'requires_reconciliation': payment.requires_reconciliation
            },
            status=status.HTTP_200_OK
        )


class MpesaCallbackAPIView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):

        callback_data = request.data

        body = callback_data.get('Body') if isinstance(
            callback_data, dict
        ) else None
        stk_callback = (
            body.get('stkCallback')
            if isinstance(body, dict)
            else None
        )

        if not isinstance(stk_callback, dict):
            return Response(
                {
                    'ResultCode': 1,
                    'ResultDesc': 'Invalid callback data'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        checkout_request_id = stk_callback.get(
            'CheckoutRequestID'
        )

        merchant_request_id = stk_callback.get(
            'MerchantRequestID'
        )

        result_code = stk_callback.get('ResultCode')

        result_description = stk_callback.get('ResultDesc')

        if (
            not checkout_request_id
            or not merchant_request_id
            or result_code is None
        ):

            return Response(
                {
                    'ResultCode': 1,
                    'ResultDesc': 'Invalid callback data'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():

            try:

                payment = Payment.objects.select_for_update().get(
                    checkout_request_id=checkout_request_id
                )

            except Payment.DoesNotExist:

                return Response(
                    {
                        'ResultCode': 0,
                        'ResultDesc': 'Callback received'
                    },
                    status=status.HTTP_200_OK
                )

            if payment.status != 'pending':

                return Response(
                    {
                        'ResultCode': 0,
                        'ResultDesc': 'Callback already processed'
                    },
                    status=status.HTTP_200_OK
                )

            if merchant_request_id != payment.merchant_request_id:

                return Response(
                    {
                        'ResultCode': 1,
                        'ResultDesc': 'Merchant request ID mismatch'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            payment.callback_data = callback_data

            payment.result_code = str(result_code)

            payment.result_description = result_description

            if str(result_code) != '0':
                payment.status = 'failed'
                payment.requires_reconciliation = False
                payment.save(
                    update_fields=[
                        'callback_data',
                        'result_code',
                        'result_description',
                        'status',
                        'requires_reconciliation',
                        'updated_at'
                    ]
                )
                return Response(
                    {
                        'ResultCode': 0,
                        'ResultDesc': 'Callback received'
                    },
                    status=status.HTTP_200_OK
                )

            callback_metadata = stk_callback.get('CallbackMetadata')
            callback_items = (
                callback_metadata.get('Item', [])
                if isinstance(callback_metadata, dict)
                else []
            )
            if not isinstance(callback_items, list):
                callback_items = []

            metadata = {
                item['Name']: item.get('Value')
                for item in callback_items
                if (
                    isinstance(item, dict)
                    and isinstance(item.get('Name'), str)
                )
            }

            try:
                amount_matches = (
                    metadata.get('Amount') is not None
                    and Decimal(str(metadata['Amount'])) == payment.amount
                )
            except (ArithmeticError, ValueError):
                amount_matches = False

            receipt = metadata.get('MpesaReceiptNumber')
            callback_phone = metadata.get('PhoneNumber')
            callback_order_status = payment.order.status

            if (
                not amount_matches
                or not receipt
                or str(callback_phone) != payment.phone_number
                or Payment.objects.filter(
                    mpesa_receipt_number=str(receipt)
                ).exclude(pk=payment.pk).exists()
                or callback_order_status != 'pending'
            ):
                payment.requires_reconciliation = True
                payment.result_description = (
                    'Callback transaction details could not be verified. '
                    'Payment reconciliation is required.'
                )
                payment.save(
                    update_fields=[
                        'callback_data',
                        'result_code',
                        'result_description',
                        'requires_reconciliation',
                        'updated_at'
                    ]
                )
                return Response(
                    {
                        'ResultCode': 0,
                        'ResultDesc': 'Callback received for verification'
                    },
                    status=status.HTTP_200_OK
                )

            transaction_date = metadata.get('TransactionDate')
            if transaction_date:
                try:
                    parsed_date = datetime.strptime(
                        str(transaction_date),
                        '%Y%m%d%H%M%S'
                    )
                except ValueError:
                    payment.requires_reconciliation = True
                    payment.result_description = (
                        'Callback transaction date is invalid. '
                        'Payment reconciliation is required.'
                    )
                    payment.save(
                        update_fields=[
                            'callback_data',
                            'result_code',
                            'result_description',
                            'requires_reconciliation',
                            'updated_at'
                        ]
                    )
                    return Response(
                        {
                            'ResultCode': 0,
                            'ResultDesc': 'Callback received for verification'
                        },
                        status=status.HTTP_200_OK
                    )

                payment.transaction_date = timezone.make_aware(
                    parsed_date,
                    ZoneInfo('Africa/Nairobi')
                )

            payment.status = 'successful'
            payment.mpesa_receipt_number = str(receipt)
            payment.requires_reconciliation = False
            payment.save(
                update_fields=[
                    'callback_data',
                    'result_code',
                    'result_description',
                    'transaction_date',
                    'status',
                    'mpesa_receipt_number',
                    'requires_reconciliation',
                    'updated_at'
                ]
            )

            order = Order.objects.select_for_update().get(
                pk=payment.order_id
            )
            order.status = 'paid'
            order.save(update_fields=['status', 'updated_at'])

        return Response(
            {
                'ResultCode': 0,
                'ResultDesc': 'Callback received'
            },
            status=status.HTTP_200_OK
        )



class PaymentStatusAPIView(APIView):

    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            token_data = signing.loads(
                token,
                salt=PAYMENT_STATUS_TOKEN_SALT,
                max_age=24 * 60 * 60
            )
        except signing.BadSignature:
            return Response(
                {'error': 'Payment status link is invalid or expired.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if not isinstance(token_data, dict):
            return Response(
                {'error': 'Payment status link is invalid or expired.'},
                status=status.HTTP_404_NOT_FOUND
            )

        payment = Payment.objects.select_related('order').filter(
            pk=token_data.get('payment_id')
        ).first()

        if payment is None:
            return Response(
                {'error': 'Payment status link is invalid or expired.'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {
                'status': payment.status,
                'order_status': payment.order.status,
                'amount': str(payment.amount),
                'phone_number': payment.phone_number,
                'receipt_number': payment.mpesa_receipt_number,
                'requires_reconciliation': payment.requires_reconciliation
            },
            status=status.HTTP_200_OK
        )



class QuerySTKStatusAPIView(APIView):

    permission_classes = [IsAdminUser]

    def post(self, request, payment_id):

        try:

            result = reconcile_payment(payment_id)

        except (
            requests.RequestException,
            ValueError,
            KeyError
        ):

            return Response(
                {
                    'error': (
                        'Unable to verify payment status '
                        'with Safaricom.'
                    )
                },
                status=status.HTTP_502_BAD_GATEWAY
            )

        outcome = result['outcome']

        if outcome == 'not_found':

            return Response(
                result,
                status=status.HTTP_404_NOT_FOUND
            )

        if outcome == 'already_processed':

            return Response(
                result,
                status=status.HTTP_400_BAD_REQUEST
            )

        if outcome == 'manual_review':

            return Response(
                result,
                status=status.HTTP_400_BAD_REQUEST
            )

        if outcome == 'successful':

            return Response(
                result,
                status=status.HTTP_200_OK
            )
        if outcome == 'failed':

            return Response(
                result,
                status=status.HTTP_200_OK
            )

        return Response(
            result,
            status=status.HTTP_200_OK
        )
