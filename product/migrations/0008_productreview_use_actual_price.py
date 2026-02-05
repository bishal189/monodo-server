# Generated manually: per-user use_actual_price when product inserted at position

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0007_product_use_actual_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='productreview',
            name='use_actual_price',
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text='If True, this user sees product at actual price (no 30-70%). Set when product is inserted at position for this user.'
            ),
        ),
    ]
