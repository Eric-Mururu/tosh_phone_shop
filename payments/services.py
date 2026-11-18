
import requests
from django.conf import settings
import base64
from datetime import datetime
from zoneinfo import ZoneInfo


def get_mpesa_access_token():

    consumer_key = settings.MPESA_CONSUMER_KEY

    consumer_secret = settings.MPESA_CONSUMER_SECRET

    if not consumer_key or not consumer_secret:
        raise ValueError(
            "M-Pesa Consumer Key or Consumer Secret is missing."
        )

    if settings.MPESA_ENVIRONMENT == 'sandbox':

        base_url = 'https://sandbox.safaricom.co.ke'

    else:

        base_url = 'https://api.safaricom.co.ke'

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



def generate_mpesa_password():

    shortcode = settings.MPESA_SHORTCODE

    passkey = settings.MPESA_PASSKEY

    if not shortcode or not passkey:
        raise ValueError(
            "M-Pesa Shortcode or Passkey is missing."
        )

    timestamp = datetime.now(
        ZoneInfo('Africa/Nairobi')
    ).strftime('%Y%m%d%H%M%S')

    password_string = shortcode + passkey + timestamp

    password = base64.b64encode(
        password_string.encode('utf-8')
    ).decode('utf-8')

    return timestamp, password


def initiate_stk_push(
    phone_number,
    amount,
    account_reference,
    callback_url
):

    access_token = get_mpesa_access_token()

    timestamp, password = generate_mpesa_password()

    if settings.MPESA_ENVIRONMENT == 'sandbox':

        base_url = 'https://sandbox.safaricom.co.ke'

    else:

        base_url = 'https://api.safaricom.co.ke'

    url = f'{base_url}/mpesa/stkpush/v1/processrequest'

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    payload = {
        'BusinessShortCode': settings.MPESA_SHORTCODE,
        'Password': password,
        'Timestamp': timestamp,
        'TransactionType': 'CustomerPayBillOnline',
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
