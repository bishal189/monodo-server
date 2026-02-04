# Generated manually: show amount that is frozen when insufficient balance

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0009_user_balance_frozen'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='balance_frozen_amount',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Amount that caused the freeze (product price user could not pay); shown when balance_frozen is True',
                max_digits=10,
                null=True,
            ),
        ),
    ]
