# -*- coding: utf-8 -*-
# Generated by Django 1.11.18 on 2019-02-19 12:05
from django.db import migrations


def forwards(apps, schema_editor):
    PublicationDocument = apps.get_model("indigo_api", "PublicationDocument")
    for pubdoc in PublicationDocument.objects.all():
        pubdoc.filename = '{}-publication-document.pdf'.format(pubdoc.work.frbr_uri[1:].replace('/', '-'))
        pubdoc.save()


def backwards(apps, schema_editor):
    PublicationDocument = apps.get_model("indigo_api", "PublicationDocument")
    PublicationDocument.objects.update(filename='publication-document.pdf')


class Migration(migrations.Migration):

    dependencies = [
        ('indigo_api', '0089_remove_workflow_closed_by_user'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]