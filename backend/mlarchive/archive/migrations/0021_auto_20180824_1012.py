# -*- coding: utf-8 -*-
# Generated by Django 1.11.14 on 2018-08-24 10:12


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('archive', '0020_auto_20180808_1533'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attachment',
            name='filename',
            field=models.CharField(blank=True, default='', max_length=65),
        ),
    ]
