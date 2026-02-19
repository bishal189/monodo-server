# Remove matching_min_percent and matching_max_percent from User; use level's price_min_percent/price_max_percent instead

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0012_alter_user_balance_frozen_amount_and_more'),
    ]

    operations = [
        migrations.RemoveField(model_name='user', name='matching_min_percent'),
        migrations.RemoveField(model_name='user', name='matching_max_percent'),
    ]
