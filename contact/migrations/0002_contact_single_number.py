# Simplify Contact to a single phone_number + updated_at

from django.db import migrations, models


def merge_contact_rows_fix(apps, schema_editor):
    Contact = apps.get_model('contact', 'Contact')
    rows = list(Contact.objects.order_by('id'))
    if len(rows) <= 1:
        return
    keep = rows[0]
    changed = False
    for r in rows[1:]:
        if (not keep.phone_number) and r.phone_number:
            keep.phone_number = r.phone_number
            changed = True
        r.delete()
    if changed:
        keep.save(update_fields=['phone_number'])


class Migration(migrations.Migration):

    dependencies = [
        ('contact', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(merge_contact_rows_fix, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='contact',
            name='created_at',
        ),
        migrations.RemoveField(
            model_name='contact',
            name='is_active',
        ),
        migrations.RemoveField(
            model_name='contact',
            name='label',
        ),
        migrations.RemoveField(
            model_name='contact',
            name='sort_order',
        ),
        migrations.AlterField(
            model_name='contact',
            name='phone_number',
            field=models.CharField(
                blank=True,
                default='',
                help_text='WhatsApp / display number (include country code when applicable)',
                max_length=32,
            ),
        ),
        migrations.AlterModelOptions(
            name='contact',
            options={
                'verbose_name': 'Contact number',
                'verbose_name_plural': 'Contact number',
            },
        ),
    ]
