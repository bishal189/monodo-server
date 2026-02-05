# Generated manually: user-specific position when product inserted at position for this user

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0008_productreview_use_actual_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='productreview',
            name='position',
            field=models.IntegerField(
                blank=True,
                db_index=True,
                help_text='User-specific display position when product is inserted at position for this user (e.g. 5). Used in GET /api/product/?user_id=X.',
                null=True
            ),
        ),
    ]
