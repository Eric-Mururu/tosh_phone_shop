
from django.urls import path

from .views import (
    InitiateSTKPushAPIView,
    MpesaCallbackAPIView,
    QuerySTKStatusAPIView,
    PaymentStatusAPIView,
)


urlpatterns = [

    path(
        'orders/<int:order_id>/stk-push/',
        InitiateSTKPushAPIView.as_view(),
        name='initiate-stk-push'
    ),

    path(
        'callback/',
        MpesaCallbackAPIView.as_view(),
        name='mpesa-callback'
    ),

    path(
        'status/<str:token>/',
        PaymentStatusAPIView.as_view(),
        name='payment-status'
    ),

    path(
        'payments/<int:payment_id>/query/',
        QuerySTKStatusAPIView.as_view(),
        name='query-stk-status'
    ),

]
