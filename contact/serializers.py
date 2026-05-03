import re

from rest_framework import serializers

from .models import Contact

_PHONE_RE = re.compile(r'^\+?[\d\s\-\(\)]*$')


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['phone_number', 'updated_at']
        read_only_fields = ['updated_at']

    def validate_phone_number(self, value):
        value = (value or '').strip()
        if value and not _PHONE_RE.match(value):
            raise serializers.ValidationError(
                'Use digits with optional +, spaces, hyphens, or parentheses.'
            )
        return value


class ContactWriteSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=32, allow_blank=True, required=True)

    def validate_phone_number(self, value):
        value = (value or '').strip()
        if value and not _PHONE_RE.match(value):
            raise serializers.ValidationError(
                'Use digits with optional +, spaces, hyphens, or parentheses.'
            )
        return value
