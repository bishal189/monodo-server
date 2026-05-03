from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.permissions import IsAdmin

from .models import Contact
from .serializers import ContactSerializer, ContactWriteSerializer


def _get_or_empty_contact():
    row = Contact.objects.first()
    if row:
        return row
    return None


class ContactNumberView(APIView):
    """
    GET: public — single contact number for the frontend.
    POST: admin only — set/update the number (single row).
    """

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdmin()]
        return [AllowAny()]

    def get(self, request):
        contact = _get_or_empty_contact()
        if not contact:
            return Response({'phone_number': '', 'updated_at': None})
        return Response(ContactSerializer(contact).data)

    def post(self, request):
        serializer = ContactWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data['phone_number']
        contact = Contact.objects.first()
        if contact:
            contact.phone_number = phone_number
            contact.save(update_fields=['phone_number', 'updated_at'])
        else:
            contact = Contact.objects.create(phone_number=phone_number)
        return Response(
            ContactSerializer(contact).data,
            status=status.HTTP_200_OK,
        )
