# Generated by Django 2.2.20 on 2021-10-29 11:35

from django.db import migrations
from indigo_api.data_migrations import CorrectAttachmentEids


def forwards(apps, schema_editor):
    """ Migrate attachment eIds, and change annotations to no longer use the attachment scope prefix.
    """
    from indigo_api.models import Document
    from indigo_api.models import Annotation

    db_alias = schema_editor.connection.alias
    migration = CorrectAttachmentEids()

    for doc in Document.objects.using(db_alias):
        if migration.migrate_document(doc):
            doc.save()

            # update annotations
            for old, new in migration.eid_mappings.items():
                # update sec_1 -> att_1__sec_1
                Annotation.objects.using(db_alias)\
                    .filter(document_id=doc.id, anchor_id=old)\
                    .update(anchor_id=new)

                # update prefixed anchors: att_1/sec_1 -> att_1__sec_1
                prefix = new.split('__', 1)[0] + '/'
                assert(prefix.startswith('att_'))
                old = prefix + old
                new = prefix + new
                Annotation.objects.using(db_alias) \
                    .filter(document_id=doc.id, anchor_id=old) \
                    .update(anchor_id=new)


class Migration(migrations.Migration):

    dependencies = [
        ('indigo_api', '0008_taxonomy_vocabulary'),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),

        # strip att_1/ from att_1/att_1__sec_1 in anchor ids
        migrations.RunSQL(
            """
UPDATE indigo_api_annotation
SET anchor_id = substr(anchor_id, strpos(anchor_id, '/') + 1)
WHERE anchor_id like '%/%';
            """,
            migrations.RunSQL.noop),
    ]
