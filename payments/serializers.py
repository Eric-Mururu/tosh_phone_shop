
import re

from rest_framework import serializers


class STKPushSerializer(serializers.Serializer):

    phone_number = serializers.CharField(
        max_length=15
    )

    def validate_phone_number(self, value):

        phone = re.sub(r'[\s+]', '', value)

        if phone.startswith('0') and len(phone) == 10:
            phone = '254' + phone[1:]

        if not re.fullmatch(r'254[17]\d{8}', phone):
            raise serializers.ValidationError(
                "Enter a valid Kenyan M-Pesa number."
            )

        return phone
