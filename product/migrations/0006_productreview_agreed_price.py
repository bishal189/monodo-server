# Generated manually for automatic price (30-70% of balance)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0005_alter_product_options_product_position'),
    ]

    operations = [
        migrations.AddField(
            model_name='productreview',
            name='agreed_price',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Price agreed for this user (30-70% of balance when assigned); used for commission',
                max_digits=10,
                null=True,
            ),
        ),
    ]
