# Generated by Django 5.2 on 2025-05-18 16:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0004_userdevice_alter_notification_notification_type_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='deduplication_key',
            field=models.CharField(blank=True, max_length=255, null=True, unique=True),
        ),
    ]
