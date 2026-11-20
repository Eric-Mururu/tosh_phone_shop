
import requests
import base64

from decimal import Decimal
from datetime import datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from payments.models import Payment
from orders.models import Order


def get_mpesa_base_url():
    if settings.MPESA_ENVIRONMENT == 'sandbox':
        return 'https://sandbox.safaricom.co.ke'

    if settings.MPESA_ENVIRONMENT == 'production':
        return 'https://api.safaricom.co.ke'

    raise ValueError(
        'MPESA_ENVIRONMENT must be either sandbox or production.'
    )


def validate_mpesa_configuration():
    required_settings = {
        'MPESA_CONSUMER_KEY': settings.MPESA_CONSUMER_KEY,
        'MPESA_CONSUMER_SECRET': settings.MPESA_CONSUMER_SECRET,
        'MPESA_SHORTCODE': settings.MPESA_SHORTCODE,
        'MPESA_PASSKEY': settings.MPESA_PASSKEY,
    }
    missing_settings = [
        name for name, value in required_settings.items() if not value
    ]

    if missing_settings:
        raise ValueError(
            'Missing M-Pesa configuration: '
            + ', '.join(missing_settings)
        )

    get_mpesa_base_url()

    if settings.MPESA_TRANSACTION_TYPE not in (
        'CustomerPayBillOnline',
        'CustomerBuyGoodsOnline'
    ):
        raise ValueError(
            'MPESA_TRANSACTION_TYPE must be CustomerPayBillOnline '
            'or CustomerBuyGoodsOnline.'
        )


# ==========================================
# 1. GET M PESA ACCESS TOKEN
# ==========================================

def get_mpesa_access_token():

    consumer_key = settings.MPESA_CONSUMER_KEY

    consumer_secret = settings.MPESA_CONSUMER_SECRET

    if not consumer_key or not consumer_secret:
        raise ValueError(
            "M Pesa Consumer Key or Consumer Secret is missing."
        )

    base_url = get_mpesa_base_url()
    url = f'{base_url}/oauth/v1/generate'

    params = {
        'grant_type': 'client_credentials'
    }

    response = requests.get(
        url,
        params=params,
        auth=(consumer_key, consumer_secret),
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    return data['access_token']


# ==========================================
# 2. GENERATE M PESA PASSWORD
# ==========================================

def generate_mpesa_password():

    shortcode = settings.MPESA_SHORTCODE

    passkey = settings.MPESA_PASSKEY

    if not shortcode or not passkey:
        raise ValueError(
            "M Pesa Shortcode or Passkey is missing."
        )

    timestamp = datetime.now(
        ZoneInfo('Africa/Nairobi')
    ).strftime('%Y%m%d%H%M%S')

    password_string = shortcode + passkey + timestamp

    password = base64.b64encode(
        password_string.encode('utf-8')
    ).decode('utf-8')

    return timestamp, password


# ==========================================
# 3. INITIATE STK PUSH
# ==========================================

def initiate_stk_push(
    phone_number,
    amount,
    account_reference,
    callback_url
):

    if settings.MPESA_TRANSACTION_TYPE not in (
        'CustomerPayBillOnline',
        'CustomerBuyGoodsOnline'
    ):
        raise ValueError(
            'MPESA_TRANSACTION_TYPE must be CustomerPayBillOnline '
            'or CustomerBuyGoodsOnline.'
        )

    access_token = get_mpesa_access_token()

    timestamp, password = generate_mpesa_password()

    base_url = get_mpesa_base_url()
    url = f'{base_url}/mpesa/stkpush/v1/processrequest'

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    payload = {
        'BusinessShortCode': settings.MPESA_SHORTCODE,
        'Password': password,
        'Timestamp': timestamp,
        'TransactionType': settings.MPESA_TRANSACTION_TYPE,
        'Amount': int(amount),
        'PartyA': phone_number,
        'PartyB': settings.MPESA_SHORTCODE,
        'PhoneNumber': phone_number,
        'CallBackURL': callback_url,
        'AccountReference': account_reference,
        'TransactionDesc': 'Tosh Phone Shop Payment',
    }

    response = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


# ==========================================
# 4. QUERY STK PUSH STATUS
# ==========================================

def query_stk_status(checkout_request_id):

    access_token = get_mpesa_access_token()

    timestamp, password = generate_mpesa_password()

    base_url = get_mpesa_base_url()
    url = f'{base_url}/mpesa/stkpushquery/v1/query'

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    payload = {
        'BusinessShortCode': settings.MPESA_SHORTCODE,
        'Password': password,
        'Timestamp': timestamp,
        'CheckoutRequestID': checkout_request_id,
    }

    response = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


# ==========================================
# 5. RECONCILE PAYMENT
# ==========================================

def reconcile_payment(payment_id):

    # Find the payment we want to investigate.

    payment = Payment.objects.filter(
        pk=payment_id
    ).first()

    if payment is None:

        return {
            'outcome': 'not_found',
            'message': 'Payment does not exist.'
        }

    # Only pending payments can be reconciled.

    if payment.status != 'pending':

        return {
            'outcome': 'already_processed',
            'message': 'This payment is no longer pending.',
            'payment_status': payment.status
        }

    # STK Query requires a Checkout Request ID.

    if not payment.checkout_request_id:

        return {
            'outcome': 'manual_review',
            'message': (
                'This payment has no Checkout Request ID. '
                'Manual investigation is required.'
            ),
            'payment_status': payment.status
        }

    # Ask Safaricom for the transaction status.

    mpesa_response = query_stk_status(
        payment.checkout_request_id
    )

    if not isinstance(mpesa_response, dict):

        return {
            'outcome': 'unresolved',
            'message': 'Safaricom returned an invalid response.',
            'payment_status': 'pending'
        }

    # Check whether Safaricom accepted our query.

    if str(mpesa_response.get('ResponseCode')) != '0':

        return {
            'outcome': 'unresolved',
            'message': 'Safaricom did not accept the query.',
            'payment_status': 'pending'
        }

    # Confirm that the transaction identifiers match.

    if (
        mpesa_response.get('CheckoutRequestID')
        != payment.checkout_request_id
        or
        mpesa_response.get('MerchantRequestID')
        != payment.merchant_request_id
    ):

        return {
            'outcome': 'unresolved',
            'message': 'The returned transaction IDs do not match.',
            'payment_status': 'pending'
        }

    result_code = mpesa_response.get('ResultCode')

    # Safaricom has not supplied a final result yet.

    if result_code is None:

        return {
            'outcome': 'pending',
            'message': 'Payment is still being processed.',
            'payment_status': 'pending'
        }

    result_code = str(result_code)

    # ======================================
    # SUCCESSFUL PAYMENT
    # ======================================

    if result_code == '0':

        with transaction.atomic():

            payment = Payment.objects.select_for_update().get(
                pk=payment_id
            )

            if payment.status != 'pending':

                return {
                    'outcome': 'already_processed',
                    'message': 'Payment has already been processed.',
                    'payment_status': payment.status
                }

            # Read the callback stored in our database.

            callback_data = payment.callback_data or {}

            stk_callback = (
                callback_data
                .get('Body', {})
                .get('stkCallback', {})
            )

            items = stk_callback.get(
                'CallbackMetadata', {}
            ).get('Item', [])

            metadata = {
                item['Name']: item.get('Value')
                for item in items
                if isinstance(item, dict) and 'Name' in item
            }

            receipt = metadata.get('MpesaReceiptNumber')

            amount = metadata.get('Amount')

            phone = metadata.get('PhoneNumber')

            callback_result = stk_callback.get('ResultCode')

            callback_checkout_id = stk_callback.get(
                'CheckoutRequestID'
            )

            callback_merchant_id = stk_callback.get(
                'MerchantRequestID'
            )

            # Verify the callback against the payment record.

            try:

                amount_matches = (
                    amount is not None
                    and Decimal(str(amount)) == payment.amount
                )

            except Exception:

                amount_matches = False

            if (
                str(callback_result) != '0'
                or callback_checkout_id != payment.checkout_request_id
                or callback_merchant_id != payment.merchant_request_id
                or not receipt
                or not amount_matches
                or phone is None
                or str(phone) != payment.phone_number
            ):

                return {
                    'outcome': 'unresolved',
                    'message': (
                        'Payment verification is incomplete '
                        'or transaction details do not match.'
                    ),
                    'payment_status': 'pending'
                }

            # Read the transaction date from callback metadata.

            transaction_date = metadata.get('TransactionDate')

            if transaction_date:

                try:

                    parsed_date = datetime.strptime(
                        str(transaction_date),
                        '%Y%m%d%H%M%S'
                    )

                    payment.transaction_date = timezone.make_aware(
                        parsed_date,
                        ZoneInfo('Africa/Nairobi')
                    )

                except ValueError:

                    return {
                        'outcome': 'unresolved',
                        'message': 'Invalid transaction date in callback.',
                        'payment_status': 'pending'
                    }

            # Update the payment record.

            payment.status = 'successful'

            payment.result_code = result_code

            payment.result_description = (
                mpesa_response.get('ResultDesc', '')
            )

            payment.mpesa_receipt_number = str(receipt)

            payment.requires_reconciliation = False

            payment.save()

            # Update the associated order.

            order = Order.objects.select_for_update().get(
                pk=payment.order_id
            )

            order.status = 'paid'

            order.save(
                update_fields=['status', 'updated_at']
            )

        return {
            'outcome': 'successful',
            'message': 'Payment successfully verified.',
            'payment_status': 'successful',
            'receipt_number': str(receipt),
            'order_status': 'paid'
        }

    # ======================================
    # FAILED PAYMENT
    # ======================================

    if result_code in ['1032', '1037']:

        with transaction.atomic():

            payment = Payment.objects.select_for_update().get(
                pk=payment_id
            )

            if payment.status == 'pending':

                payment.status = 'failed'

                payment.result_code = result_code

                payment.result_description = (
                    mpesa_response.get('ResultDesc', '')
                )

                payment.requires_reconciliation = False

                payment.save()

        return {
            'outcome': 'failed',
            'message': 'Payment was not completed.',
            'payment_status': payment.status,
            'details': payment.result_description
        }

    # ======================================
    # UNRESOLVED PAYMENT
    # ======================================

    return {
        'outcome': 'unresolved',
        'message': 'Safaricom returned an unresolved result.',
        'payment_status': 'pending',
        'result_code': result_code,
        'details': mpesa_response.get('ResultDesc')
    }
