#FIRST SERIALIZER
from rest_framework import serializers
from .models import Order, OrderItem

#SECOND SERIALIIZER
from django.db import transaction
from products.models import Phone


class OrderItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderItem

        fields = [
            'id',
            'phone',
            'quantity',
            'unit_price',
            'subtotal',
        ]
        read_only_fields = [
        'id',
        'unit_price',
        'subtotal',
    ]


class OrderSerializer(serializers.ModelSerializer):

    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order

        fields = [
            'id',
            'customer_name',
            'customer_phone',
            'customer_email',
            'delivery_address',
            'status',
            'total_amount',
            'items',
            'created_at',
            'updated_at',
        ]

        read_only_fields = [
            'id',
            'status',
            'total_amount',
            'created_at',
            'updated_at',
        ]

    @transaction.atomic
    def create(self, validated_data):

        items_data = validated_data.pop('items')

        order = Order.objects.create(**validated_data)

        total = 0

        for item_data in items_data:

            phone = Phone.objects.select_for_update().get(
                pk=item_data['phone'].pk
            )

            quantity = item_data['quantity']

            if quantity > phone.stock:
                raise serializers.ValidationError(
                    f"Only {phone.stock} units of {phone.name} are available."
                )

            unit_price = phone.price

            OrderItem.objects.create(
                order=order,
                phone=phone,
                quantity=quantity,
                unit_price=unit_price
            )

            phone.stock -= quantity
            phone.save(update_fields=['stock'])

            total += quantity * unit_price

        order.total_amount = total
        order.save(update_fields=['total_amount'])

        return order        