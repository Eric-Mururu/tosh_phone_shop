
import { useEffect, useState } from 'react'
import './App.css'

const getCsrfToken = async () => {
  const response = await fetch('/api/csrf/')
  const data = await response.json().catch(() => null)

  if (!response.ok || !data?.csrfToken) {
    throw new Error(
      `Unable to prepare a secure request (HTTP ${response.status}).`
    )
  }

  return data.csrfToken
}

function App() {
  const [phones, setPhones] = useState([])
  const [cart, setCart] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showCart, setShowCart] = useState(false)
  const [showCheckout, setShowCheckout] = useState(false)
  const [selectedPhone, setSelectedPhone] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [checkoutError, setCheckoutError] = useState('')
  const [orderResult, setOrderResult] = useState(null)
  const [paymentResult, setPaymentResult] = useState(null)
  const [paymentPhone, setPaymentPhone] = useState('')
  const [paymentPollAttempts, setPaymentPollAttempts] = useState(0)
  const [paymentScreenDismissed, setPaymentScreenDismissed] = useState(false)
  const [navigationTarget, setNavigationTarget] = useState('')
  const [cartMessage, setCartMessage] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('All')
  const [searchTerm, setSearchTerm] = useState('')
  const [sortOption, setSortOption] = useState('default')

  const [customer, setCustomer] = useState({
    customer_name: '',
    customer_phone: '',
    customer_email: '',
    delivery_address: ''
  })

  const requestStkPush = async (order, phoneNumber) => {
    const csrfToken = await getCsrfToken()
    const response = await fetch(
      `/api/payments/orders/${order.id}/stk-push/`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ phone_number: phoneNumber })
      }
    )
    const data = await response.json().catch(() => ({}))

    if (!response.ok && !data.status_token) {
      const validationMessage = Object.values(data)
        .flat()
        .filter((message) => typeof message === 'string')
        .join(' ')
      throw new Error(
        data.error ||
        data.detail ||
        validationMessage ||
        'Unable to start the M-Pesa payment.'
      )
    }

    if (!data.status_token) {
      throw new Error('The payment status link was not returned by the server.')
    }

    return {
      ...data,
      order,
      status: data.status || data.payment_status || 'pending',
      initiation_error: response.ok ? '' : data.error
    }
  }

  // Retrieve products from Django
  useEffect(() => {
    fetch('/api/products/')
      .then((response) => {
        if (!response.ok) {
          throw new Error('Failed to retrieve products')
        }

        return response.json()
      })
      .then((data) => {
        setPhones(Array.isArray(data) ? data : data.results || [])
        setLoading(false)
      })
      .catch((error) => {
        console.error('Product retrieval error:', error)
        setError('Unable to load products. Please try again.')
        setLoading(false)
      })
  }, [])

  useEffect(() => {
    const token = paymentResult?.status_token

    if (
      !token ||
      paymentResult.status !== 'pending' ||
      paymentPollAttempts >= 24
    ) {
      return
    }

    let cancelled = false
    const timer = setTimeout(async () => {
      try {
        const response = await fetch(
          `/api/payments/status/${encodeURIComponent(token)}/`
        )
        const data = await response.json().catch(() => ({}))

        if (!response.ok) {
          throw new Error(data.error || 'Unable to check payment status.')
        }

        if (cancelled) {
          return
        }

        if (data.status === 'successful') {
          setOrderResult({
            ...paymentResult.order,
            status: data.order_status,
            mpesa_receipt_number: data.receipt_number
          })
          setPaymentResult(null)
          setPaymentPollAttempts(0)
          window.scrollTo({ top: 0, behavior: 'smooth' })
          return
        }

        setPaymentResult((currentPayment) => (
          currentPayment
            ? {
                ...currentPayment,
                status: data.status,
                requires_reconciliation: data.requires_reconciliation
              }
            : currentPayment
        ))
        setPaymentPollAttempts((attempts) => attempts + 1)
      } catch (error) {
        if (cancelled) {
          return
        }

        setPaymentResult((currentPayment) => (
          currentPayment
            ? { ...currentPayment, status_check_error: error.message }
            : currentPayment
        ))
        setPaymentPollAttempts((attempts) => attempts + 1)
      }
    }, 5000)

    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [paymentResult, paymentPollAttempts])

  useEffect(() => {
    if (!navigationTarget) {
      return
    }

    const frame = window.requestAnimationFrame(() => {
      const target = document.getElementById(navigationTarget)

      if (target) {
        window.history.replaceState(null, '', `#${navigationTarget}`)
        target.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }

      setNavigationTarget('')
    })

    return () => window.cancelAnimationFrame(frame)
  }, [navigationTarget])

  // Calculate total items
  const cartCount = cart.reduce(
    (total, item) => total + item.quantity,
    0
  )
  const cartTotal = cart.reduce(
    (total, item) => total + Number(item.price) * item.quantity,
    0
  )

const filteredPhones = phones.filter((phone) => {

  const matchesCategory =
    selectedCategory === 'All' ||
    phone.brand.toLowerCase() === selectedCategory.toLowerCase()

  const matchesSearch =
    phone.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    phone.brand.toLowerCase().includes(searchTerm.toLowerCase()) ||
    phone.description.toLowerCase().includes(searchTerm.toLowerCase())

  return matchesCategory && matchesSearch

})

const sortedPhones = [...filteredPhones].sort((a, b) => {

  if (sortOption === 'price-low') {
    return Number(a.price) - Number(b.price)
  }

  if (sortOption === 'price-high') {
    return Number(b.price) - Number(a.price)
  }

  if (sortOption === 'name-asc') {
    return a.name.localeCompare(b.name)
  }

  if (sortOption === 'name-desc') {
    return b.name.localeCompare(a.name)
  }

  return 0

})

  // Add phone to cart
  const addToCart = (phone) => {

    const existingItem = cart.find(
      (item) => item.id === phone.id
    )

    // Check available stock
    if (existingItem && existingItem.quantity >= phone.stock) {
      alert('You cannot add more than the available stock.')
      return
    }

    // Update shopping cart
    setCart((currentCart) => {

      const itemAlreadyAdded = currentCart.find(
        (item) => item.id === phone.id
      )

      if (itemAlreadyAdded) {

        return currentCart.map((item) =>
          item.id === phone.id
            ? {
                ...item,
                quantity: item.quantity + 1
              }
            : item
        )
      }

      return [
        ...currentCart,
        {
          ...phone,
          quantity: 1
        }
      ]
    })

    // Display success notification
    setCartMessage(`${phone.name} added to your cart!`)

    // Remove notification after 3 seconds
    setTimeout(() => {
      setCartMessage('')
    }, 3000)

  }


  // Remove phone from cart
  const removeFromCart = (phoneId) => {
    setCart((currentCart) =>
      currentCart.filter((item) => item.id !== phoneId)
    )
  }

  // Update quantity
  const updateQuantity = (phoneId, change) => {
    setCart((currentCart) =>
      currentCart.map((item) => {
        if (item.id !== phoneId) {
          return item
        }

        const newQuantity = item.quantity + change

        if (newQuantity < 1) {
          return item
        }

        if (newQuantity > item.stock) {
          alert('You have reached the available stock.')
          return item
        }

        return {
          ...item,
          quantity: newQuantity
        }
      })
    )
  }

  // Open product details
  const viewProduct = (phone) => {
    setSelectedPhone(phone)
    setShowCart(false)
    setShowCheckout(false)
    setOrderResult(null)

    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    })
  }

  // Return to product listing
  const backToProducts = () => {
    setSelectedPhone(null)
    setShowCheckout(false)
    setShowCart(false)
  }

  const navigateToSection = (sectionId) => (event) => {
    event.preventDefault()
    setSelectedPhone(null)
    setShowCheckout(false)
    setShowCart(false)
    setOrderResult(null)
    setPaymentScreenDismissed(Boolean(paymentResult))
    setNavigationTarget(sectionId)
  }

  // Update customer form fields
  const handleCustomerChange = (event) => {
    const { name, value } = event.target

    setCustomer((currentCustomer) => ({
      ...currentCustomer,
      [name]: value
    }))
  }

  // Open checkout
  const openCheckout = () => {
    if (cart.length === 0) {
      alert('Your shopping cart is empty.')
      return
    }

    setShowCart(false)
    setShowCheckout(true)
    setSelectedPhone(null)
    setCheckoutError('')
    setOrderResult(null)

    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    })
  }

  // Submit order to Django
  const submitOrder = async (event) => {
    event.preventDefault()

    setSubmitting(true)
    setCheckoutError('')
    setOrderResult(null)

    const orderData = {
      ...customer,
      items: cart.map((item) => ({
        phone: item.id,
        quantity: item.quantity
      }))
    }

    let createdOrder = null

    try {
      const csrfToken = await getCsrfToken()
      const response = await fetch(
        '/api/orders/',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify(orderData)
        }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          data.detail || data.error || JSON.stringify(data)
        )
      }

      createdOrder = data
      setPaymentPhone(customer.customer_phone)
      const payment = await requestStkPush(
        createdOrder,
        customer.customer_phone
      )
      setPaymentResult(payment)
      setPaymentScreenDismissed(false)
      setPaymentPollAttempts(0)
      setCart([])
      setShowCheckout(false)

      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      })

    } catch (error) {
      if (createdOrder) {
        setPaymentResult({
          order: createdOrder,
          status: 'pending',
          initiation_error: error.message
        })
        setPaymentPhone(customer.customer_phone)
        setPaymentPollAttempts(0)
        setCart([])
        setShowCheckout(false)
        window.scrollTo({ top: 0, behavior: 'smooth' })
      } else {
        console.error('Order submission error:', error)
        setCheckoutError(error.message)
      }
    } finally {
      setSubmitting(false)
    }
  }

  const retryPayment = async () => {
    if (!paymentResult?.order) {
      return
    }

    setSubmitting(true)

    try {
      const payment = await requestStkPush(
        paymentResult.order,
        paymentPhone
      )
      setPaymentResult(payment)
      setPaymentPhone(payment.phone_number || paymentPhone)
      setPaymentScreenDismissed(false)
      setPaymentPollAttempts(0)
    } catch (error) {
      setPaymentResult((currentPayment) => (
        currentPayment
          ? {
              ...currentPayment,
              initiation_error: error.message
            }
          : currentPayment
      ))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="app">

      {/* Navigation */}
      <header className="navbar">
        <a
          className="logo"
          href="#home"
          onClick={navigateToSection('home')}
          aria-label="Tosh Phone Shop home"
        >
          TOSH<span> PHONE SHOP</span>
        </a>

        <nav>
        <a href="#home" onClick={navigateToSection('home')}>Home</a>
        <a href="#products" onClick={navigateToSection('products')}>Phones</a>
        <a href="#categories" onClick={navigateToSection('categories')}>Categories</a>
        <a href="#about" onClick={navigateToSection('about')}>About</a>
        <a href="#contact" onClick={navigateToSection('contact')}>Contact</a>
        </nav>

        <div className="nav-actions">
          <button
            className="cart-button"
            onClick={() => {
              setShowCart((isOpen) => !isOpen)
              setShowCheckout(false)
              setSelectedPhone(null)
              setOrderResult(null)
            }}
          >
            Cart ({cartCount})
          </button>
        </div>
      </header>

      {paymentResult && paymentScreenDismissed && (
        <button
          type="button"
          className="payment-status-resume"
          onClick={() => {
            setPaymentScreenDismissed(false)
            window.scrollTo({ top: 0, behavior: 'smooth' })
          }}
        >
          M-Pesa {paymentResult.status} · Order #{paymentResult.order?.id} ·
          {' '}View status
        </button>
      )}

      {/* Order Confirmation */}
      {orderResult && (
        <section className="order-confirmation">

          <div className="confirmation-card">

            <div className="success-icon">
              ✓
            </div>

            <p className="confirmation-eyebrow">
              ORDER CONFIRMATION
            </p>

            <h1>Payment Received!</h1>

            <p className="confirmation-message">
              Thank you, {orderResult.customer_name}.
              Your M-Pesa payment has been confirmed and your order is received.
            </p>

            <div className="confirmation-status">
              <span>Order Status</span>
              <strong>{orderResult.status}</strong>
            </div>

            <div className="confirmation-details">

              <div className="confirmation-detail">
                <span>Order Number</span>
                <strong>#{orderResult.id}</strong>
              </div>

              <div className="confirmation-detail">
                <span>Total Amount</span>
                <strong>
                  KSh {Number(orderResult.total_amount).toLocaleString('en-KE')}
                </strong>
              </div>

              {orderResult.mpesa_receipt_number && (
                <div className="confirmation-detail">
                  <span>M-Pesa Receipt</span>
                  <strong>{orderResult.mpesa_receipt_number}</strong>
                </div>
              )}

            </div>

            <div className="confirmation-note">
              <p>
                Keep your M-Pesa receipt for your records. We will contact you
                using the details provided to arrange delivery.
              </p>
            </div>

            <button
              className="continue-shopping-button"
              onClick={() => {
                setOrderResult(null)
                backToProducts()
              }}
            >
              Continue Shopping
            </button>

            <p className="confirmation-footer">
              Thank you for shopping with Tosh Phone Shop.
            </p>

          </div>

        </section>
      )}

      {paymentResult && !paymentScreenDismissed && !showCart && !showCheckout && (
        <section className="payment-status-section">
          <div className="payment-status-card">
            <p className="payment-status-eyebrow">M-PESA CHECKOUT</p>
            <h1>
              {paymentResult.status === 'failed'
                ? 'Payment was not completed'
                : !paymentResult.status_token
                  ? 'Payment setup needs attention'
                  : 'Check your phone'}
            </h1>

            <p className="payment-status-intro">
              {paymentResult.status === 'failed'
                ? 'The payment was not completed. You can try again below.'
                : !paymentResult.status_token
                  ? 'Your order was created, but the M-Pesa request could not be started. Check the phone number and try again, or contact support.'
                  : paymentResult.initiation_error
                    ? 'Safaricom has not confirmed whether the prompt was sent. We are checking the payment status; do not make a second payment yet.'
                    : `We sent an M-Pesa payment request to ${paymentResult.phone_number || paymentPhone}. Enter your M-Pesa PIN to approve it.`}
            </p>

            <div className="payment-status-summary">
              <div>
                <span>Order</span>
                <strong>#{paymentResult.order?.id}</strong>
              </div>
              <div>
                <span>Amount</span>
                <strong>
                  KSh {Number(
                    paymentResult.order?.total_amount || paymentResult.amount
                  ).toLocaleString('en-KE')}
                </strong>
              </div>
              <div>
                <span>Payment status</span>
                <strong className={`payment-status-value ${paymentResult.status}`}>
                  {paymentResult.status === 'pending'
                    ? 'Waiting for confirmation'
                    : paymentResult.status}
                </strong>
              </div>
            </div>

            {paymentResult.initiation_error && (
              <p className="payment-status-message">
                {paymentResult.initiation_error}
              </p>
            )}

            {paymentResult.status_check_error && (
              <p className="payment-status-message">
                We could not check the payment status just now. We will retry
                automatically.
              </p>
            )}

            {paymentResult.requires_reconciliation && (
              <p className="payment-status-message">
                Your payment is being verified. Do not retry yet; contact us
                with order #{paymentResult.order?.id} if this message remains.
              </p>
            )}

            {paymentResult.status === 'pending' &&
              paymentPollAttempts >= 24 && (
                <p className="payment-status-message">
                  Confirmation is taking longer than expected. Do not make a
                  second payment; contact support with order #
                  {paymentResult.order?.id}.
                </p>
              )}

            {(paymentResult.status === 'failed' ||
              !paymentResult.status_token) && (
              <div className="payment-retry">
                <label htmlFor="payment-phone">M-Pesa phone number</label>
                <input
                  id="payment-phone"
                  type="tel"
                  value={paymentPhone}
                  onChange={(event) => setPaymentPhone(event.target.value)}
                  placeholder="e.g. 0712345678"
                />
                <button
                  type="button"
                  className="checkout-submit-button"
                  onClick={retryPayment}
                  disabled={submitting || !paymentPhone.trim()}
                >
                  {submitting ? 'Sending request...' : 'Try M-Pesa Again'}
                </button>
              </div>
            )}
          </div>
        </section>
      )}


      {/* Shopping Cart */}
      {showCart && (
        <section className="cart-section">

          <div className="cart-header">
            <p className="cart-eyebrow">YOUR SHOPPING BAG</p>
            <h1>Your Shopping Cart</h1>
            <p>Review your selected smartphones before checkout.</p>
          </div>

          {cart.length === 0 ? (

            <div className="empty-cart">
              <div className="empty-cart-icon">🛒</div>
              <h2>Your Cart Is Empty</h2>
              <p>You have not added any smartphones to your cart yet.</p>

              <button
                className="cart-checkout-button"
                onClick={backToProducts}
              >
                Continue Shopping
              </button>
            </div>

          ) : (

            <div className="cart-layout">

              {/* Cart Products */}

              <div className="cart-products-panel">

                <div className="cart-panel-heading">
                  <h2>Shopping Items</h2>
                  <span>{cartCount} items</span>
                </div>

                {cart.map((item) => (

                  <div className="cart-product" key={item.id}>

                    <div className="cart-product-image">
                      <img
                        src={
                          item.image ||
                          'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=300'
                        }
                        alt={item.name}
                      />
                    </div>

                    <div className="cart-product-info">

                      <h3>{item.name}</h3>

                      <p>{item.brand}</p>

                      <strong>
                        KSh {Number(item.price).toLocaleString('en-KE')}
                      </strong>

                      <button
                        className="cart-remove-button"
                        onClick={() => removeFromCart(item.id)}
                      >
                        Remove
                      </button>

                    </div>

                    <div className="cart-quantity">

                      <span>Quantity</span>

                      <div className="quantity-control">

                        <button
                          onClick={() => updateQuantity(item.id, -1)}
                        >
                          −
                        </button>

                        <strong>{item.quantity}</strong>

                        <button
                          onClick={() => updateQuantity(item.id, 1)}
                        >
                          +
                        </button>

                      </div>

                    </div>

                    <div className="cart-product-subtotal">

                      <span>Subtotal</span>

                      <strong>
                        KSh {(Number(item.price) * item.quantity).toLocaleString('en-KE')}
                      </strong>

                    </div>

                  </div>

                ))}

                <button
                  className="cart-continue-button"
                  onClick={backToProducts}
                >
                  Continue Shopping
                </button>

              </div>

              {/* Order Summary */}

              <aside className="cart-summary">

                <h2>Order Summary</h2>

                <div className="cart-summary-row">
                  <span>Total Items</span>
                  <strong>{cartCount}</strong>
                </div>

                <div className="cart-summary-row">
                  <span>Subtotal</span>
                  <strong>
                    KSh {cartTotal.toLocaleString('en-KE')}
                  </strong>
                </div>

                <div className="cart-summary-row">
                  <span>Delivery</span>
                  <strong>To be confirmed</strong>
                </div>

                <div className="cart-summary-total">
                  <span>Total</span>
                  <strong>
                    KSh {cartTotal.toLocaleString('en-KE')}
                  </strong>
                </div>

                <button
                  className="cart-checkout-button"
                  onClick={openCheckout}
                  disabled={paymentResult?.status === 'pending'}
                >
                  {paymentResult?.status === 'pending'
                    ? 'Payment In Progress'
                    : 'Proceed to Checkout'}
                </button>

                <p className="cart-summary-note">
                  Your order total is calculated using the selected
                  products and quantities.
                </p>

              </aside>

            </div>

          )}

        </section>
      )}


      {/* Checkout Page */}
      {showCheckout && (
        <section className="checkout-section">

          <div className="checkout-header">
            <button
              className="back-button"
              onClick={() => {
                setShowCheckout(false)
                setShowCart(true)
              }}
            >
              Back to Cart
            </button>

            <p className="checkout-eyebrow">SECURE CHECKOUT</p>

            <h1>Complete Your Order</h1>

            <p>
              Please provide your details below to complete your purchase.
            </p>

            <div className="checkout-progress">
              <div className="progress-step active">
                <span>1</span>
                <p>Customer Details</p>
              </div>

              <div className="progress-line"></div>

              <div className="progress-step">
                <span>2</span>
                <p>Payment</p>
              </div>

              <div className="progress-line"></div>

              <div className="progress-step">
                <span>3</span>
                <p>Confirmation</p>
              </div>
            </div>
          </div>

          <div className="checkout-container">

            {/* Customer Information */}
            <form
              onSubmit={submitOrder}
              className="checkout-form checkout-card"
            >
              <div className="checkout-card-heading">
                <div>
                  <span className="checkout-number">01</span>
                  <h2>Customer Information</h2>
                  <p>Enter your contact and delivery details.</p>
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="customer_name">Full Name</label>

                <input
                  id="customer_name"
                  type="text"
                  name="customer_name"
                  value={customer.customer_name}
                  onChange={handleCustomerChange}
                  placeholder="e.g. Wanjiku Mwangi"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="customer_phone">Phone Number</label>

                <input
                  id="customer_phone"
                  type="tel"
                  name="customer_phone"
                  value={customer.customer_phone}
                  onChange={handleCustomerChange}
                  placeholder="e.g. 0712345678"
                  required
                />
                <small>
                  Use the phone number you intend to use for M Pesa.
                </small>
              </div>

              <div className="form-group">
                <label htmlFor="customer_email">Email Address</label>

                <input
                  id="customer_email"
                  type="email"
                  name="customer_email"
                  value={customer.customer_email}
                  onChange={handleCustomerChange}
                  placeholder="e.g. wanjiku.mwangi@example.com"
                />
              </div>

              <div className="form-group">
                <label htmlFor="delivery_address">Delivery Address</label>

                <textarea
                  id="delivery_address"
                  name="delivery_address"
                  value={customer.delivery_address}
                  onChange={handleCustomerChange}
                  placeholder="e.g. Kilimani, Nairobi"
                  rows="4"
                  required
                />
              </div>

              {checkoutError && (
                <p className="checkout-error">
                  {checkoutError}
                </p>
              )}

              <button
                type="submit"
                className="checkout-submit-button"
                disabled={submitting}
              >
                {submitting
                  ? 'Sending M-Pesa Request...'
                  : 'Place Order & Pay with M-Pesa'}
              </button>

              <p className="checkout-security">
                An M-Pesa prompt will be sent to the phone number above.
              </p>
            </form>

            {/* Order Summary */}
            <aside className="checkout-summary checkout-card">

              <div className="checkout-card-heading">
                <div>
                  <span className="checkout-number">02</span>
                  <h2>Your Order</h2>
                  <p>Review your selected smartphones.</p>
                </div>

                <span className="checkout-item-count">
                  {cartCount} items
                </span>
              </div>

              <div className="checkout-products">

                {cart.map((item) => (
                  <div className="checkout-product" key={item.id}>

                    <div className="checkout-product-image">
                      <img
                        src={
                          item.image ||
                          'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=300'
                        }
                        alt={item.name}
                      />
                    </div>

                    <div className="checkout-product-info">
                      <h3>{item.name}</h3>

                      <p>{item.brand}</p>

                      <p>Quantity: {item.quantity}</p>

                      <strong>
                        KSh {(Number(item.price) * item.quantity).toLocaleString('en-KE')}
                      </strong>
                    </div>

                  </div>
                ))}

              </div>

              <div className="checkout-total">

                <div>
                  <span>Subtotal</span>
                  <strong>
                    KSh {cartTotal.toLocaleString('en-KE')}
                  </strong>
                </div>

                <div>
                  <span>Delivery</span>
                  <strong>To be confirmed</strong>
                </div>

                <div className="checkout-grand-total">
                  <span>Total</span>

                  <strong>
                    KSh {cartTotal.toLocaleString('en-KE')}
                  </strong>
                </div>

              </div>

              <div className="checkout-payment-note">
                <h3>M-Pesa payment</h3>
                <p>
                  Pay securely with an STK Push prompt sent to your phone after
                  you place the order.
                </p>
              </div>

            </aside>

          </div>

        </section>
      )}

      {cartMessage && (
  <div className="cart-notification">
    <span>✓</span>
    {cartMessage}
  </div>
)}

      {/* Product Details */}
      {selectedPhone && (
        <section className="product-details">

          <div className="details-top">
            <button className="back-button" onClick={backToProducts}>
              ← Back to Phones
            </button>

            <p>HOME / SMARTPHONES / {selectedPhone.brand}</p>
          </div>

          <div className="details-container">

            <div className="details-image">
              <img
                src={
                  selectedPhone.image ||
                  'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=600'
                }
                alt={selectedPhone.name}
              />

              <span className="image-label">QUALITY SMARTPHONES</span>
            </div>

            <div className="details-content">

              <p className="eyebrow">TOSH PHONE SHOP COLLECTION</p>

              <p className="details-brand">{selectedPhone.brand}</p>

              <h1>{selectedPhone.name}</h1>

              <div className="details-rating">
                <span>★★★★★</span>
                <small>Quality smartphone selection</small>
              </div>

              <h2 className="details-price">
                KSh {Number(selectedPhone.price).toLocaleString('en-KE')}
              </h2>

              <p className="details-description">
                {selectedPhone.description}
              </p>

              <div className="details-stock">
                <span className={selectedPhone.stock > 0 ? 'in-stock' : 'out-stock'}>
                  ● {selectedPhone.stock > 0 ? 'In Stock' : 'Out of Stock'}
                </span>

                <small>
                  {selectedPhone.stock > 0
                    ? `${selectedPhone.stock} units available`
                    : 'Currently unavailable'}
                </small>
              </div>

              <div className="details-features">
                <div>
                  <strong>01</strong>
                  <span>Quality Products</span>
                </div>

                <div>
                  <strong>02</strong>
                  <span>Affordable Prices</span>
                </div>

                <div>
                  <strong>03</strong>
                  <span>Secure Ordering</span>
                </div>
              </div>

              <button
                className="details-cart-button"
                onClick={() => addToCart(selectedPhone)}
                disabled={selectedPhone.stock <= 0}
              >
                {selectedPhone.stock > 0 ? 'Add to Shopping Cart →' : 'Out of Stock'}
              </button>

              <p className="details-payment-note">
                Secure ordering. M Pesa payment will be available at checkout.
              </p>

            </div>

          </div>
        </section>
      )}



      {/* Hero Section */}
      {!selectedPhone && !showCart && !showCheckout && !orderResult && (!paymentResult || paymentScreenDismissed) && (
        <section className="hero" id="home">
          <div className="hero-content">
            <p className="eyebrow">WELCOME TO TOSH PHONE SHOP</p>

            <h1>
              Find Your Perfect<span> Smartphone</span>
            </h1>

            <p className="hero-description">
              Discover quality smartphones at affordable prices.
              Shop your favourite brands with confidence.
            </p>

            <a href="#products" className="shop-button">
              Shop Now
            </a>
          </div>

          <div className="hero-image">
            <img
              src="https://images.unsplash.com/photo-1592899677977-9c10ca588bbd?w=900"
              alt="Modern smartphone"
            />
          </div>
        </section>
      )}


      {/* Categories */}
      {!selectedPhone && !showCart && !showCheckout && !orderResult && (!paymentResult || paymentScreenDismissed) && (
        <section className="categories" id="categories">

          <div className="category-heading">
            <p className="eyebrow">EXPLORE OUR COLLECTION</p>
            <h2>Shop By Brand</h2>
            <p>Find your favourite smartphone brand.</p>
          </div>
          <div className="product-tools">
            <div className="product-search">
              <input
                type="text"
                placeholder="Search by phone name, brand or description..."
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
              />

              <button
                type="button"
                className="search-button"
                onClick={() => {
                  document.getElementById('products')?.scrollIntoView({
                    behavior: 'smooth'
                  })
                }}
              >
                Search
              </button>

              <button
                type="button"
                className="clear-button"
                onClick={() => setSearchTerm('')}
              >
                Clear
              </button>
            </div>

            <div className="product-sort">
              <label htmlFor="sortOption">Sort by:</label>
              <select
                id="sortOption"
                value={sortOption}
                onChange={(event) => setSortOption(event.target.value)}
              >
                <option value="default">Default</option>
                <option value="price-low">Price: Low to High</option>
                <option value="price-high">Price: High to Low</option>
                <option value="name-asc">Name: A to Z</option>
                <option value="name-desc">Name: Z to A</option>
              </select>
            </div>
          </div>

          <div className="brand-filter">
            <p className="brand-filter-label">Browse by brand</p>
            <div className="category-grid">
              {['All', 'Apple', 'Samsung', 'Tecno', 'Infinix'].map((brand) => (
                <button
                  type="button"
                  key={brand}
                  className={`category-card ${
                    selectedCategory === brand ? 'active-category' : ''
                  }`}
                  aria-pressed={selectedCategory === brand}
                  onClick={() => {
                    setSelectedCategory(brand)
                    document.getElementById('products')?.scrollIntoView({
                      behavior: 'smooth'
                    })
                  }}
                >
                  {brand === 'All' ? 'All Phones' : brand}
                </button>
              ))}
            </div>
          </div>

        </section>
      )}



      {/* Products */}
      {!selectedPhone && !showCart && !showCheckout && !orderResult && (!paymentResult || paymentScreenDismissed) && (
        <section className="products" id="products">

          <div className="section-heading">
            <div>
              <p className="eyebrow">OUR COLLECTION</p>
              <h2>Featured Smartphones</h2>
              <p>Discover smartphones that match your lifestyle.</p>
            </div>

            <span className="product-count">{sortedPhones.length} Products</span>
          </div>

          {loading && <p>Loading smartphones...</p>}

          {error && <p>{error}</p>}

                      {!loading && !error && sortedPhones.length === 0 && (
              <p className="no-products">
                No smartphones available in this category.
              </p>
            )}

          <div className="product-grid">

            {sortedPhones.map((phone) => (
              <div className="product-card" key={phone.id}>

                <div className="product-image-container">

                  <img
                    src={
                      phone.image ||
                      'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=600'
                    }
                    alt={phone.name}
                  />

                  <span className="product-brand-label">
                    {phone.brand}
                  </span>

                </div>

                <div className="product-card-content">
                  <h3>{phone.name}</h3>

                  <p className="product-description">
                    {phone.description}
                  </p>

                  <div className="product-price">
                    KSh {Number(phone.price).toLocaleString('en-KE')}
                  </div>

                  <p className={
                    phone.stock > 0
                      ? 'product-in-stock'
                      : 'product-out-stock'
                  }>
                    {phone.stock > 0
                      ? `${phone.stock} units available`
                      : 'Out of stock'}
                  </p>

                  <div className="product-card-actions">

                    <button
                      className="product-view-button"
                      onClick={() => viewProduct(phone)}
                    >
                      View Details
                    </button>

                    <button
                      className="product-add-button"
                      onClick={() => addToCart(phone)}
                      disabled={phone.stock <= 0}
                    >
                      {phone.stock > 0 ? 'Add to Cart' : 'Unavailable'}
                    </button>

                  </div>

                </div>

              </div>
            ))}

          </div>

        </section>
      )}

      {/* WHY SHOP WITH US SECTION */}
      {!selectedPhone && !showCart && !showCheckout && !orderResult && (!paymentResult || paymentScreenDismissed) && (
        <section className="why-shop-section">
          <div className="why-shop-heading">
            <p className="eyebrow">THE TOSH ADVANTAGE</p>
            <h2>Why Shop With Us?</h2>
            <p>Enjoy a convenient and reliable smartphone shopping experience.</p>
          </div>

          <div className="why-shop-container">
            <div className="why-shop-card">
              <div className="why-shop-icon">✓</div>
              <h3>Quality Smartphones</h3>
              <p>Explore carefully selected smartphones from recognised brands.</p>
            </div>

            <div className="why-shop-card">
              <div className="why-shop-icon">KSh</div>
              <h3>Affordable Prices</h3>
              <p>Find smartphones at competitive prices to suit your budget.</p>
            </div>

            <div className="why-shop-card">
              <div className="why-shop-icon">↗</div>
              <h3>Convenient Ordering</h3>
              <p>Browse products, add your favourites to the cart and place orders online.</p>
            </div>

            <div className="why-shop-card">
              <div className="why-shop-icon">♥</div>
              <h3>Customer Support</h3>
              <p>We are committed to helping you make informed shopping decisions.</p>
            </div>
          </div>
        </section>
      )}

{/* About Us Section */}
{!selectedPhone && !showCart && !showCheckout && !orderResult && (!paymentResult || paymentScreenDismissed) && (
  <section className="about-section" id="about">

    <div className="about-container">

      <div className="about-content">
        <p className="eyebrow">GET TO KNOW US</p>

        <h2>About <span>Tosh Phone Shop</span></h2>

        <p>
          Welcome to Tosh Phone Shop, your trusted destination
          for quality smartphones. We aim to make smartphone
          shopping simple, convenient and affordable.
        </p>

        <p>
          We offer carefully selected smartphones from
          recognised brands, helping customers find devices
          that suit their needs and budgets.
        </p>

        <p>
          Our commitment is to provide quality products,
          affordable prices and a smooth shopping experience.
        </p>

        <a href="#products" className="about-button">
          Explore Our Phones
        </a>
      </div>

      <div className="about-highlights">

        <div className="about-highlight">
          <h3>Quality</h3>
          <p>Carefully selected smartphones.</p>
        </div>

        <div className="about-highlight">
          <h3>Affordability</h3>
          <p>Devices at competitive prices.</p>
        </div>

        <div className="about-highlight">
          <h3>Convenience</h3>
          <p>A simple and convenient shopping experience.</p>
        </div>

      </div>

    </div>

  </section>
)}


{/* Contact Us Section */}
{!selectedPhone && !showCart && !showCheckout && !orderResult && (!paymentResult || paymentScreenDismissed) && (
  <section className="contact-section" id="contact">

    <div className="contact-heading">
      <p className="eyebrow">WE ARE HERE TO HELP</p>
      <h2>Contact <span>Us</span></h2>
      <p>
        Have a question about our smartphones?
        Get in touch with our team.
      </p>
    </div>

    <div className="contact-container">

      <div className="contact-card">
        <h3>Phone Number</h3>
        <a className="contact-link" href="tel:+254700000000">
  +254 700 000 000
</a>
        <small>Call us for enquiries and assistance.</small>
      </div>

      <div className="contact-card">
        <h3>Email Address</h3>
        <a className="contact-link" href="mailto:hello@toshphoneshop.example">
          hello@toshphoneshop.example
        </a>
        <small>Send us your questions by email.</small>
      </div>

      <div className="contact-card">
        <h3>Our Location</h3>
        <p>Nairobi, Kenya</p>
        <small>Visit our business location.</small>
      </div>

      <div className="contact-card">
        <h3>Business Hours</h3>
        <p>Monday to Saturday</p>
        <small>8:00 AM to 6:00 PM</small>
      </div>

    </div>
    <div className="contact-whatsapp">
  <h3>Need help choosing a smartphone?</h3>

  <p>Chat with our team directly on WhatsApp.</p>

  <a
    href="https://wa.me/254700000000?text=Hello%20Tosh%20Phone%20Shop"
    target="_blank"
    rel="noopener noreferrer"
  >
    Chat on WhatsApp
  </a>
</div>
  </section>
)}


      {/* Footer */}
      {!selectedPhone && !showCart && !showCheckout && !orderResult && (!paymentResult || paymentScreenDismissed) && (
        <footer className="footer" id="footer">

          <div className="footer-container">

            <div className="footer-brand">
              <h2>TOSH <span>PHONE SHOP</span></h2>

              <p>
                Your trusted destination for quality smartphones.
                Discover great devices at affordable prices and enjoy
                a convenient shopping experience.
              </p>
            </div>

            <div className="footer-links">
              <h3>Quick Links</h3>

              <a href="#home">Home</a>
              <a href="#products">Shop Phones</a>
              <a href="#categories">Categories</a>
              <a href="#about">About Us</a>
            </div>

            <div className="footer-support">
              <h3>Customer Support</h3>

              <p>Need help choosing a smartphone?</p>

              <p>
                We are committed to providing quality products
                and a smooth shopping experience.
              </p>

              <p className="footer-payment">
                Secure shopping with M Pesa payment support.
              </p>
            </div>

          </div>

          <div className="footer-bottom">
            <p>© 2026 Tosh Phone Shop. All rights reserved.</p>
            <p>Quality Smartphones. Affordable Prices.</p>
          </div>

        </footer>
      )}

    </div>
  )
}

export default App
