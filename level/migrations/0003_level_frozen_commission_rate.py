# Generated manually: dynamic commission when user was frozen at submit

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('level', '0002_level_price_min_percent_level_price_max_percent'),
    ]

    operations = [
        migrations.AddField(
            model_name='level',
            name='frozen_commission_rate',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                default=6.00,
                help_text='Commission rate when user was frozen at submit (e.g. 6.00 for 6%). Used when they complete after topping up.',
                max_digits=5,
                null=True
            ),
        ),
    ]
