# Generated by Django 5.0.7 on 2024-08-06 16:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_paper_parse_time'),
    ]

    operations = [
        migrations.AddField(
            model_name='paper',
            name='abstract',
            field=models.TextField(blank=True, default='', null=True),
        ),
    ]
