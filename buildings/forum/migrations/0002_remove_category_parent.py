# Generated by Django 5.1.3 on 2024-12-06 20:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("forum", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="category",
            name="parent",
        ),
    ]