# Generated by Django 2.2.12 on 2021-02-05 08:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('indigo_api', '0004_placesettings_no_publication_document_text'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='task',
            options={'permissions': (('submit_task', 'Can submit an open task for review'), ('cancel_task', 'Can cancel a task that is open or has been submitted for review'), ('reopen_task', 'Can reopen a task that is closed or cancelled'), ('unsubmit_task', 'Can unsubmit a task that has been submitted for review'), ('close_task', 'Can close a task that has been submitted for review'), ('close_any_task', 'Can close any task that has been submitted for review, regardless of who submitted it'), ('block_task', 'Can block a task from being done, and unblock it'))},
        ),
        migrations.AddField(
            model_name='task',
            name='blocked_by',
            field=models.ManyToManyField(help_text='Tasks blocking this task from being done.', related_name='blocking', to='indigo_api.Task'),
        ),
    ]