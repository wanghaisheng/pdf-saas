# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-08-21 15:55
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('indigo_app', '0014_rename_language_country_tables'),
        ('indigo_api', '0058_import_language_country_from_indigo_app'),
    ]

    operations = [
        migrations.AlterField(
            model_name='editor',
            name='country',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='indigo_api.Country'),
        ),
        migrations.AlterField(
            model_name='locality',
            name='country',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='indigo_api.Country'),
        ),
        migrations.AlterField(
            model_name='publication',
            name='country',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='indigo_api.Country'),
        ),
    ]