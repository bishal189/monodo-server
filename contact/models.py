from django.db import models


class Contact(models.Model):
    """
    Single app-wide contact number (e.g. WhatsApp). Only one row should exist.
    """
    phone_number = models.CharField(
        max_length=32,
        blank=True,
        default='',
        help_text='WhatsApp / display number (include country code when applicable)',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contacts'
        verbose_name = 'Contact number'
        verbose_name_plural = 'Contact number'

    def __str__(self):
        return self.phone_number or '(not set)'
