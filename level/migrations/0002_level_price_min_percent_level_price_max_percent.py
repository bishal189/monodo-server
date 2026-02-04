# Generated manually for dynamic price percentage range

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('level', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='level',
            name='price_min_percent',
            field=models.DecimalField(
                decimal_places=2,
                default=30.0,
                help_text='Min % of balance for next product price (e.g. 30 for 30%)',
                max_digits=5,
            ),
        ),
        migrations.AddField(
            model_name='level',
            name='price_max_percent',
            field=models.DecimalField(
                decimal_places=2,
                default=70.0,
                help_text='Max % of balance for next product price (e.g. 70 for 70%)',
                max_digits=5,
            ),
        ),
    ]
