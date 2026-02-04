# Generated manually: use actual price when product inserted at position from frontend

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0006_productreview_agreed_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='use_actual_price',
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text='If True, always use product price (no 30-70% agreed price). Set when inserted at position from frontend.',
            ),
        ),
    ]
