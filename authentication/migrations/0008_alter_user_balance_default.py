# Generated manually for default balance $10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0007_user_is_training_account_user_original_account'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='balance',
            field=models.DecimalField(
                decimal_places=2,
                default=10.00,
                help_text='User account balance (default $10 for new registrations and training accounts)',
                max_digits=10,
            ),
        ),
    ]
