# Generated by Django 2.2.24 on 2022-01-30 16:39

from django.db import migrations, connection


def eol_to_br(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Document = apps.get_model('indigo_api', 'Document')
    doc_type_id = ContentType.objects.get_for_model(Document).id

    with connection.cursor() as cursor:
        cursor.execute("""
UPDATE indigo_api_document
SET document_xml = REPLACE(document_xml, '<eol/>', '<br/>'), updated_at = NOW()
WHERE document_xml LIKE '%%<eol/>%%';

UPDATE reversion_version
SET serialized_data = REPLACE(serialized_data, '<eol/>', '<br/>')
WHERE content_type_id = %s AND serialized_data LIKE '%%<eol/>%%';
""", [doc_type_id])


def br_to_eol(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Document = apps.get_model('indigo_api', 'Document')
    doc_type_id = ContentType.objects.get_for_model(Document).id

    with connection.cursor() as cursor:
        cursor.execute("""
UPDATE indigo_api_document
SET document_xml = REPLACE(document_xml, '<br/>', '<eol/>'), updated_at = NOW()
WHERE document_xml LIKE '%%<br/>%%';

UPDATE reversion_version
SET serialized_data = REPLACE(serialized_data, '<br/>', '<eol/>')
WHERE content_type_id = %s AND serialized_data LIKE '%%<br/>%%';
""", [doc_type_id])


class Migration(migrations.Migration):

    dependencies = [
        ('indigo_api', '0011_language_tasks'),
    ]

    operations = [
        migrations.RunPython(eol_to_br, br_to_eol),
    ]
