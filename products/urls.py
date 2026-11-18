from django.urls import path

from .views import (
    PhoneListAPIView,
    PhoneDetailAPIView,
    PhoneCreateAPIView,
    PhoneUpdateAPIView,
    PhoneDeleteAPIView,
)


urlpatterns = [
    path(
        'products/',
        PhoneListAPIView.as_view(),
        name='product-list'
    ),

    path(
        'products/<int:pk>/',
        PhoneDetailAPIView.as_view(),
        name='product-detail'
    ),

    path(
        'products/create/',
        PhoneCreateAPIView.as_view(),
        name='product-create'
    ),

    path(
        'products/<int:pk>/update/',
        PhoneUpdateAPIView.as_view(),
        name='product-update'
    ),

    path(
    'products/<int:pk>/delete/',
    PhoneDeleteAPIView.as_view(),
    name='product-delete'
),
]