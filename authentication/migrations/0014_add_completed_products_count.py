# Add persistent completed_products_count (never decremented on re-insert)

from django.db import migrations, models


def backfill_completed_products_count(apps, schema_editor):
    User = apps.get_model('authentication', 'User')
    ProductReview = apps.get_model('product', 'ProductReview')
    for user in User.objects.all():
        count = ProductReview.objects.filter(user=user, status='COMPLETED').count()
        user.completed_products_count = count
        user.save(update_fields=['completed_products_count'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0013_remove_user_matching_min_max_percent'),
        ('product', '0004_productreview'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='completed_products_count',
            field=models.PositiveIntegerField(default=0, help_text='Total number of product reviews completed (never decremented; re-inserting resets review but not this count)'),
        ),
        migrations.RunPython(backfill_completed_products_count, noop),
    ]
