# Tosh Phone Shop

A full-stack e-commerce web application for buying smartphones in Kenya. Customers browse a phone catalogue, build a cart, check out with their delivery details, and start payment through an M-Pesa STK Push prompt on their phone.

**Live site:** https://tosh-phone-shop.onrender.com
*(Hosted on a free tier, so the first load after a period of inactivity can take up to a minute.)*

## Screenshots

<!-- Add 3 screenshots to a /docs folder and update the paths below -->
| Catalogue | Cart | Checkout |
|---|---|---|
| ![Catalogue](docs/catalogue.png) | ![Cart](docs/cart.png) | ![Checkout](docs/checkout.png) |

## Features

**Storefront**
1. Product catalogue showing phones retrieved from the backend API
2. Product details view
3. Product search
4. Brand filtering
5. Product sorting
6. Responsive design for mobile and desktop

**Cart and checkout**
7. Shopping cart with add, remove and quantity adjustment
8. Checkout form for customer details and delivery address
9. Order creation and storage in the database
10. Order totals calculated on the backend from product prices, not trusted from the client

**Payments (M-Pesa Daraja)**
11. M-Pesa STK Push payment initiation
12. Callback reception from Safaricom
13. Payment records and transaction information stored in the database

**Administration**
14. Django Admin for managing products, orders and payments

## Tech stack

| Component | Technology |
|---|---|
| Frontend | React.js |
| Frontend tooling | Vite |
| Language (frontend) | JavaScript |
| Styling | CSS |
| Language (backend) | Python |
| Backend framework | Django |
| API | Django REST Framework |
| Database | MySQL |
| Payments | Safaricom Daraja API |
| Version control | Git and GitHub |

## How the M-Pesa payment flow works

1. The customer browses phones and adds products to the cart.
2. At checkout, the customer enters their name, phone number, email and delivery address.
3. React sends the order to the Django REST API.
4. Django validates the order, checks product availability, calculates the total and saves the order in MySQL.
5. React requests an M-Pesa STK Push from the Django payment endpoint.
6. Django calls the Safaricom Daraja API to request an STK Push for the customer's phone number and the order amount.
7. The customer receives an M-Pesa prompt on their phone and enters their PIN to authorize the payment.
8. Safaricom sends a callback to the Django backend with the transaction response.
9. The backend stores the callback information for payment tracking and reconciliation.

### Current status of payments

Implemented: order creation, STK Push initiation, and callback reception and storage.

Still in progress: automatic payment reconciliation, and showing a fully verified payment result to the customer. The payment query endpoint is currently restricted to administrators.

## Project structure

```
tosh_phone_shop/
├── config/          # Django settings, URLs, WSGI
├── products/        # Product models, serializers, views, URLs
├── orders/          # Order models, serializers, views, URLs
├── payments/        # Payment models, serializers, views, URLs (Daraja integration)
├── frontend/        # React + Vite application
│   ├── src/         # App.jsx, App.css, main.jsx
│   ├── public/
│   ├── package.json
│   └── index.html
├── media/           # Uploaded product images
├── static/
├── manage.py
├── requirements.txt
├── .env.example     # Environment variable template
└── .gitignore
```

## Running locally

### Prerequisites
- Python 3
- Node.js and npm
- MySQL
- A Safaricom Daraja sandbox app (for testing payments)

### Backend
```bash
git clone <this-repo-url>
cd tosh_phone_shop

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # then fill in your own values
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Testing M-Pesa locally
Safaricom must be able to reach your callback URL, so expose your local server with a tunnelling tool and set the public callback URL in your `.env`. Use Daraja sandbox credentials, never real keys, in development.

## Demo access

There is no public customer login. Customers can browse and check out without an account. The Django Admin (`/admin`) requires an administrator account created with `createsuperuser`.

## Security notes

- Secrets and API keys live in `.env`, which is not committed. See `.env.example` for the variables needed.
- Order totals are calculated on the server from stored product prices.

## Roadmap

1. Automatic payment reconciliation using Daraja's STK Push query for payments that stay pending
2. Update order payment status only from a verified Daraja callback, handling duplicate callbacks safely
3. Show a verified payment result to the customer after checkout
4. A customer-facing payment status endpoint
5. Automated tests for the order and payment flows
6. Customer accounts and order history

## Author

**Eric Gitonga** — Full-Stack Developer (React, Django REST, M-Pesa Daraja)
LinkedIn: https://www.linkedin.com/in/eric-gitonga-dev
