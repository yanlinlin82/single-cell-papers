# Generated by Django 5.0.7 on 2024-08-04 13:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='paper',
            name='source',
            field=models.CharField(blank=True, default='', max_length=32, null=True),
        ),
    ]