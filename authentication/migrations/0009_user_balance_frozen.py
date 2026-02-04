# Generated manually: freeze balance when insufficient to complete review

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0008_alter_user_balance_default'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='balance_frozen',
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text='True when balance was insufficient to complete a review (frozen until balance is credited or review completed)',
            ),
        ),
    ]
