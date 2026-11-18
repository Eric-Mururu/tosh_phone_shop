
from rest_framework import serializers
from .models import Phone


class PhoneSerializer(serializers.ModelSerializer):

    class Meta:
        model = Phone

        fields = [
            'id',
            'name',
            'brand',
            'description',
            'price',
            'image',
            'stock',
            'created_at',
            'updated_at',
        ]
