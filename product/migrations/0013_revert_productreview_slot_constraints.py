# Revert 0012: restore unique_together (user, product) and remove slot constraints.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0012_productreview_slot_unique_constraints'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='productreview',
            name='product_review_unique_user_position',
        ),
        migrations.RemoveConstraint(
            model_name='productreview',
            name='product_review_unique_user_product_null_position',
        ),
        migrations.AlterUniqueTogether(
            name='productreview',
            unique_together={('user', 'product')},
        ),
    ]
