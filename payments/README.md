# M-Pesa STK Push setup

The checkout creates a pending order, requests an M-Pesa STK Push, and waits
for the Safaricom callback before marking the order paid. Payment credentials
belong in the project-root `.env` file; never commit that file or paste
credentials into source code or chat.

## Configure Daraja

1. Create a Daraja app and copy its Consumer Key and Consumer Secret.
2. Copy the shortcode and passkey for the selected Daraja environment.
3. Add the M-Pesa entries from `.env.example` to the project-root `.env`
   file, preserving any existing database and Django settings, then set:
   - `MPESA_ENVIRONMENT=sandbox` while testing, or `production` after Safaricom
     has approved your business for live Daraja access.
   - `MPESA_CONSUMER_KEY`, `MPESA_CONSUMER_SECRET`, `MPESA_SHORTCODE`, and
     `MPESA_PASSKEY` from that same environment.
   - `MPESA_TRANSACTION_TYPE=CustomerPayBillOnline` for a PayBill or
     `CustomerBuyGoodsOnline` for a Till.
   - `MPESA_CALLBACK_URL` to
     `https://<your-public-host>/api/payments/callback/`.
4. Ensure the callback host is publicly accessible over HTTPS and is allowed
   by Django's `ALLOWED_HOSTS`. Localhost is not reachable by Safaricom; use a
   public HTTPS tunnel during development or a deployed HTTPS domain.
5. In production, set `DEBUG=False` and a private, randomly generated
   `SECRET_KEY`; signed customer payment-status links depend on that key.
6. Restart Django after changing `.env`.

The payment page shows the customer the order total and polls a signed,
temporary status link. A successful callback is checked against the order's
checkout ID, amount, and phone number before the order is marked paid. The
receipt is shown on the confirmation page and is available in Django admin.
If callback details do not match, the payment stays pending and is flagged
for reconciliation rather than being marked paid.

The payee name shown in the M-Pesa prompt is registered to the shortcode by
Safaricom; it is not a custom STK Push payload field. The sandbox demo
shortcode may display a generic name such as “Daraja”. To show “Tosh Phone
Shop”, use a live shortcode whose Safaricom-registered display name is “Tosh
Phone Shop”.

Sandbox credentials can only trigger test payments supported by Safaricom's
sandbox. Receiving real customer payments requires a live shortcode, live
Daraja credentials, and Safaricom production approval.
