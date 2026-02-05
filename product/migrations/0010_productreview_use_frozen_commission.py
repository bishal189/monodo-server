# Generated manually: use frozen commission rate when user was frozen at submit

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0009_productreview_position'),
    ]

    operations = [
        migrations.AddField(
            model_name='productreview',
            name='use_frozen_commission',
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text='True if user was frozen at submit (insufficient balance). When they complete after top-up, use level.frozen_commission_rate.'
            ),
        ),
    ]
