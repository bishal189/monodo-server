# Generated manually for Contact model

import django.core.validators
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Contact',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(help_text='Short label, e.g. Support, WhatsApp', max_length=100)),
                (
                    'phone_number',
                    models.CharField(
                        help_text='Display / dial / WhatsApp number (include country code when applicable)',
                        max_length=32,
                        validators=[
                            django.core.validators.RegexValidator(
                                message='Enter a valid phone number (digits, optional +, spaces, hyphens).',
                                regex=r'^\+?[\d\s\-\(\)]+$',
                            )
                        ],
                    ),
                ),
                (
                    'sort_order',
                    models.PositiveSmallIntegerField(
                        db_index=True,
                        default=0,
                        help_text='Lower numbers appear first',
                    ),
                ),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Contact',
                'verbose_name_plural': 'Contacts',
                'db_table': 'contacts',
                'ordering': ['sort_order', 'id'],
            },
        ),
    ]
