# Generated by Django 5.2.1 on 2025-05-31 08:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prison', '0003_rename_approved_visitor_is_approved_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='visitor',
            name='address',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='visitor',
            name='contact_number',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='visitor',
            name='denial_reason',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='visitor',
            name='id_number',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='visitor',
            name='last_updated',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='visitor',
            name='purpose_of_visit',
            field=models.TextField(blank=True, null=True),
        ),
    ]
