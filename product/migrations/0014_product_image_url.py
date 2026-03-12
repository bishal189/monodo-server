from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0013_revert_productreview_slot_constraints'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='image_url',
            field=models.URLField(blank=True, help_text='Optional image URL (e.g. from JSON or placeholder); used when image file is not set.', max_length=500, null=True),
        ),
    ]
