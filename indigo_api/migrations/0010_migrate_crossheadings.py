# Generated by Django 2.2.20 on 2021-10-29 11:35

from django.db import migrations
from indigo_api.data_migrations import RealCrossHeadings
from django.db.models import signals


def forwards(apps, schema_editor):
    from indigo_api.models import Document
    from indigo_api.models import Annotation
    from indigo_api.models.documents import post_save_document
    from reversion.models import Version

    # disconnect signals
    signals.post_save.disconnect(post_save_document, Document)

    db_alias = schema_editor.connection.alias
    migration = RealCrossHeadings()

    for doc in Document.objects.using(db_alias).order_by('-pk'):
        print(f"Migrating {doc}")
        if migration.migrate_document(doc):
            print("  Changed")
            doc.save()

            # update annotations
            for old, new in migration.eid_mappings.items():
                Annotation.objects.using(db_alias)\
                    .filter(document_id=doc.id, anchor_id=old)\
                    .update(anchor_id=new)
        else:
            print("  No changes")

    # migrate historical document versions
    print("Migrating versions")
    for version in Version.objects.get_for_model(Document).order_by('-pk').iterator():
        print(f"Migrating version {version.pk}")
        if migration.migrate_document_version(version):
            print("  Changed")
            version.save()
        else:
            print("  No changes")


class Migration(migrations.Migration):

    dependencies = [
        ('indigo_api', '0009_migrate_attachment_eids'),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]