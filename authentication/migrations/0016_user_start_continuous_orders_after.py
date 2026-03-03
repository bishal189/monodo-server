# Generated manually: per-user order overview (start_continuous_orders_after)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0015_user_matching_max_percent_user_matching_min_percent_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='start_continuous_orders_after',
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Per-user override for order overview: continuous orders start after this many. If null, level's value is used.",
                null=True
            ),
        ),
    ]
