# Allow same product at multiple positions (slots). One review per (user, position) when position set;
# one review per (user, product) when position is null (pool assignments).

from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0011_alter_product_use_actual_price_and_more'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='productreview',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='productreview',
            constraint=models.UniqueConstraint(
                condition=Q(position__isnull=False),
                fields=('user', 'position'),
                name='product_review_unique_user_position',
            ),
        ),
        migrations.AddConstraint(
            model_name='productreview',
            constraint=models.UniqueConstraint(
                condition=Q(position__isnull=True),
                fields=('user', 'product'),
                name='product_review_unique_user_product_null_position',
            ),
        ),
    ]
