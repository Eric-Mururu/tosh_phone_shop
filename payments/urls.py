
from django.urls import path

from .views import (
    InitiateSTKPushAPIView,
    MpesaCallbackAPIView,
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

]
