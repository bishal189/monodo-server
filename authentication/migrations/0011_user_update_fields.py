# Generated for Update User form: credibility, withdrawal limits, matching range, rob/withdrawal flags, draws, winning amounts

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0010_user_balance_frozen_amount'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='credibility',
            field=models.PositiveSmallIntegerField(default=100, help_text='Credibility score 0-100'),
        ),
        migrations.AddField(
            model_name='user',
            name='withdrawal_min_amount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='withdrawal_max_amount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='withdrawal_needed_to_complete_order',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='matching_min_percent',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='matching_max_percent',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='allow_rob_order',
            field=models.BooleanField(default=True, help_text='Whether to allow rob order'),
        ),
        migrations.AddField(
            model_name='user',
            name='allow_withdrawal',
            field=models.BooleanField(default=True, help_text='Whether to allow withdrawal'),
        ),
        migrations.AddField(
            model_name='user',
            name='number_of_draws',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='winning_amount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='custom_winning_amount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]
