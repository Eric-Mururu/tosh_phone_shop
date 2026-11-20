
from django.db import models

from orders.models import Order


class Payment(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
    ]

    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name='payments'
    )

    phone_number = models.CharField(
        max_length=15
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    merchant_request_id = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    checkout_request_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True
    )

    mpesa_receipt_number = models.CharField(
        max_length=30,
        blank=True,
        null=True
    )

    result_code = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    result_description = models.TextField(
        blank=True,
        null=True
    )

    transaction_date = models.DateTimeField(
        blank=True,
        null=True
    )

    callback_data = models.JSONField(
        blank=True,
        null=True
    )

    requires_reconciliation = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"Payment {self.id} for Order {self.order.id}"
