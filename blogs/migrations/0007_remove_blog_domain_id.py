# Generated by Django 3.0.6 on 2020-05-25 09:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blogs', '0006_auto_20200525_0945'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='blog',
            name='domain_id',
        ),
    ]