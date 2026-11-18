
from decimal import Decimal
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from orders.models import Order
from .models import Payment
from .serializers import STKPushSerializer
from .services import initiate_stk_push


class InitiateSTKPushAPIView(APIView):

    def post(self, request, order_id):

        order = get_object_or_404(
            Order,
            pk=order_id
        )

        if order.status != 'pending':
            return Response(
                {
                    'error': 'This order is not available for payment.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = STKPushSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data['phone_number']

        amount = order.total_amount

        if amount <= 0 or amount != amount.to_integral_value():
            return Response(
                {
                    'error': 'Order amount must be a positive whole number.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        callback_url = settings.MPESA_CALLBACK_URL

        if not callback_url or not callback_url.startswith('https://'):
            return Response(
                {
                    'error': 'A public HTTPS callback URL is not configured.'
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
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

            if mpesa_response.get('ResponseCode') != '0':

                payment.status = 'failed'

                payment.result_description = mpesa_response.get(
                    'ResponseDescription',
                    'STK Push request was not accepted.'
                )

                payment.save()

                return Response(
                    {
                        'error': 'Safaricom did not accept the payment request.',
                        'details': payment.result_description
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            payment.merchant_request_id = mpesa_response.get(
                'MerchantRequestID'
            )

            payment.checkout_request_id = mpesa_response.get(
                'CheckoutRequestID'
            )

            payment.result_description = mpesa_response.get(
                'ResponseDescription'
            )

            payment.save()

            return Response(
                {
                    'message': 'STK Push sent successfully. Check your phone.',
                    'payment_id': payment.id,
                    'order_id': order.id,
                    'amount': str(payment.amount),
                    'status': payment.status
                },
                status=status.HTTP_200_OK
            )

        except (requests.RequestException, ValueError, KeyError):

            payment.status = 'failed'

            payment.result_description = (
                'Unable to communicate with Safaricom.'
            )

            payment.save()

            return Response(
                {
                    'error': 'Unable to initiate M-Pesa payment. Please try again.'
                },
                status=status.HTTP_502_BAD_GATEWAY
            )



class MpesaCallbackAPIView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):

        callback_data = request.data

        stk_callback = (
            callback_data
            .get('Body', {})
            .get('stkCallback', {})
        )

        checkout_request_id = stk_callback.get(
            'CheckoutRequestID'
        )

        merchant_request_id = stk_callback.get(
            'MerchantRequestID'
        )

        result_code = stk_callback.get('ResultCode')

        result_description = stk_callback.get('ResultDesc')

        if not checkout_request_id or result_code is None:
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

            payment.callback_data = callback_data

            payment.result_code = str(result_code)

            payment.result_description = result_description

            if str(result_code) == '0':

                items = stk_callback.get(
                    'CallbackMetadata', {}
                ).get('Item', [])

                metadata = {
                    item['Name']: item.get('Value')
                    for item in items
                    if 'Name' in item
                }

                receipt = metadata.get('MpesaReceiptNumber')

                amount = metadata.get('Amount')

                phone = metadata.get('PhoneNumber')

                if (
                    not receipt
                    or amount is None
                    or phone is None
                    or Decimal(str(amount)) != payment.amount
                    or str(phone) != payment.phone_number
                    or merchant_request_id != payment.merchant_request_id
                ):

                    payment.result_description = (
                        'Payment confirmation details did not match.'
                    )

                    payment.save()

                    return Response(
                        {
                            'ResultCode': 0,
                            'ResultDesc': 'Callback received'
                        },
                        status=status.HTTP_200_OK
                    )

                transaction_date = metadata.get('TransactionDate')

                if transaction_date:

                    payment.transaction_date = timezone.make_aware(
                        datetime.strptime(
                            str(transaction_date),
                            '%Y%m%d%H%M%S'
                        ),
                        ZoneInfo('Africa/Nairobi')
                    )

                payment.mpesa_receipt_number = str(receipt)

                payment.status = 'successful'

                payment.order.status = 'paid'

                payment.order.save(update_fields=['status'])

            else:

                payment.status = 'failed'

            payment.save()

        return Response(
            {
                'ResultCode': 0,
                'ResultDesc': 'Accepted'
            },
            status=status.HTTP_200_OK
        )
