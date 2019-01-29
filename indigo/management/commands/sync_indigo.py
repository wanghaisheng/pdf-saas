from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import User

import dj_database_url

from indigo_api.models import Work, Locality, Country, Language, Amendment, Document, Attachment, attachment_filename
from indigo_social.badges import CountryBadge


class Command(BaseCommand):
    help = 'Copies content from one indigo to another'

    def add_arguments(self, parser):
        parser.add_argument('sourcedb')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.setup_db(options['sourcedb'])

        if self.dry_run:
            self.stdout.write(self.style.WARNING('DRY-RUN, won\'t actually do anything.'))

        with transaction.atomic():
            self.copy_languages()
            self.copy_places()
            self.copy_users()
            self.copy_works()
            self.copy_amendments()
            self.copy_documents()

            if self.dry_run:
                raise Exception()

    def setup_db(self, dburl):
        self.source_db = 'source-db'
        self.target_db = 'default'

        dbconfig = dj_database_url.parse(dburl)
        settings.DATABASES[self.source_db] = dbconfig
        self.stdout.write(self.style.SUCCESS('Copying \n  FROM %s\n    TO %s' % (dbconfig, settings.DATABASES[self.target_db])))

    def get_user(self, user):
        """ Get a target user object from a source user object.
        """
        return self.user_emails.get(user.email, self.user_names.get(user.username))

    def copy_users(self):
        """ Copy User and Editor objects. Ignores social logins.
        """
        existing = User.objects.only("username", "email")
        usernames = set(u.username for u in existing)
        emails = set(u.email for u in existing)

        users = User.objects.using(self.source_db)\
            .prefetch_related('editor')\
            .all()

        for src in users:
            if src.username in usernames:
                self.stdout.write(self.style.WARNING('Ignoring existing user with username %s' % src.username))
                continue

            if src.email in emails:
                self.stdout.write(self.style.WARNING('Ignoring existing user with email %s' % src.email))
                continue

            self.stdout.write(self.style.SUCCESS('Copying user %s' % src))
            editor = src.editor
            src.pk = None
            src.save(force_insert=True, using=self.target_db)
            src.refresh_from_db()

            countries = [self.countries[c.code] for c in editor.permitted_countries.all()]
            if editor.country:
                country = self.countries[src.editor.country.code]
            else:
                country = None

            editor.pk = None
            editor.user_id = src.pk
            if country:
                editor.country_id = country.pk
            editor.save(force_insert=True, using=self.target_db)
            editor.permitted_countries.set(countries)

        users = User.objects.all()
        self.user_names = {u.username: u for u in users}
        self.user_emails = {u.email: u for u in users}

    def copy_languages(self):
        self.languages = {lang.code: lang for lang in Language.objects.all()}

        for lang in Language.objects.using(self.source_db).all():
            if lang.code in self.languages:
                self.stdout.write(self.style.WARNING('Ignoring existing language %s' % lang.code))
                continue

            self.stdout.write(self.style.SUCCESS('Copying language %s' % lang.code))
            lang.pk = None
            lang.save(force_insert=True, using=self.target_db)

        self.languages = {l.code: l for l in Language.objects.all()}

    def copy_places(self):
        self.countries = {c.code: c for c in Country.objects.all()}

        countries = Country.objects.using(self.source_db)\
            .prefetch_related('primary_language')\
            .all()

        for country in countries:
            if country.code in self.countries:
                self.stdout.write(self.style.WARNING('Ignoring existing country %s' % country.code))
                continue

            self.stdout.write(self.style.SUCCESS('Copying country %s' % country.code))
            country.pk = None
            country.primary_language_id = self.languages[country.primary_language].pk
            country.save(force_insert=True, using=self.target_db)

        # reload
        self.countries = {c.code: c for c in Country.objects.all()}
        self.localities = {c.place_code: c for c in Locality.objects.all()}

        localities = Locality.objects.using(self.source_db)\
            .prefetch_related('country')\
            .all()

        for loc in localities:
            if loc.place_code in self.localities:
                self.stdout.write(self.style.WARNING('Ignoring existing locality %s' % loc.place_code))
                continue

            self.stdout.write(self.style.SUCCESS('Copying locality %s' % loc.place_code))
            loc.pk = None
            loc.country_id = self.countries[loc.country.code].pk
            loc.save(force_insert=True, using=self.target_db)

        # reload badges
        CountryBadge.create_all()
        self.localities = {c.place_code: c for c in Locality.objects.all()}

    def copy_works(self):
        existing = set(w.frbr_uri for w in Work.objects.using(self.target_db).all())

        works = Work.objects.using(self.source_db)\
            .prefetch_related('locality', 'country', 'repealed_by', 'parent_work', 'commencing_work',
                              'created_by_user', 'updated_by_user')\
            .all()
        work_lookup = {w.frbr_uri: w for w in works}

        # process works without dependencies first
        works = sorted(works, key=lambda w: [1 if w.repealed_by else 0, 1 if w.parent_work else 0, 1 if w.commencing_work else 0])

        for work in works:
            if work.frbr_uri in existing:
                self.stdout.write(self.style.WARNING('Ignoring existing work %s' % work.frbr_uri))
                continue

            self.stdout.write(self.style.SUCCESS('Copying work %s' % work.frbr_uri))
            work.pk = None
            work.country_id = self.countries[work.country.code].pk
            if work.locality:
                work.locality_id = self.localities[work.locality.place_code].pk

            if work.repealed_by:
                work.repealed_by_id = work_lookup[work.repealed_by.frbr_uri].pk

            if work.parent_work:
                work.parent_work_id = work_lookup[work.parent_work.frbr_uri].pk

            if work.commencing_work:
                work.commencing_work_id = work_lookup[work.commencing_work.frbr_uri].pk

            if work.created_by_user:
                work.created_by_user_id = self.get_user(work.created_by_user).pk
            if work.updated_by_user:
                work.updated_by_user_id = self.get_user(work.updated_by_user).pk

            work.save(force_insert=True, using=self.target_db)

        self.works = {w.frbr_uri: work for w in Work.objects.using(self.source_db).all()}

    def copy_amendments(self):
        existing = Amendment.objects.using(self.target_db)\
            .prefetch_related('amended_work', 'amending_work')\
            .all()
        existing = {(a.amended_work.frbr_uri, a.amending_work.frbr_uri) for a in existing}

        amendments = Amendment.objects.using(self.source_db)\
            .prefetch_related('amended_work', 'amending_work')\
            .all()

        for amendment in amendments:
            key = (amendment.amended_work.frbr_uri, amendment.amending_work.frbr_uri)
            if key in existing:
                self.stdout.write(self.style.WARNING('Ignoring existing amendment %s' % str(key)))
                continue

            self.stdout.write(self.style.SUCCESS('Copying amendment %s' % str(key)))
            amendment.pk = None
            amendment.amended_work_id = self.works[amendment.amended_work.frbr_uri].pk
            amendment.amending_work_id = self.works[amendment.amending_work.frbr_uri].pk
            if amendment.created_by_user:
                amendment.created_by_user_id = self.get_user(amendment.created_by_user).pk
            if amendment.updated_by_user:
                amendment.updated_by_user_id = self.get_user(amendment.updated_by_user).pk
            amendment.save(force_insert=True, using=self.target_db)

    def copy_documents(self):
        existing = Document.objects.using(self.target_db).filter(deleted=False).all()
        existing = set(d.expression_uri.expression_uri() for d in existing)

        document_id_map = {}
        attachment_map = {}

        docs = Document.objects.using(self.source_db)\
            .prefetch_related('work', 'language', 'created_by_user', 'updated_by_user')\
            .filter(deleted=False)\
            .defer(None)\
            .all()

        for doc in docs:
            key = doc.expression_uri.expression_uri()
            if key in existing:
                self.stdout.write(self.style.WARNING('Ignoring existing document %s' % key))
                continue

            attachments = list(doc.attachments.all())
            notes = list(doc.annotations.all())

            self.stdout.write(self.style.SUCCESS('Copying document %s' % key))
            old_id = doc.pk
            doc.pk = None
            doc.work_id = self.works[doc.work.frbr_uri].pk
            doc.language_id = self.languages[doc.language.code].pk
            if doc.created_by_user:
                doc.created_by_user_id = self.get_user(doc.created_by_user).pk
            if doc.updated_by_user:
                doc.updated_by_user_id = self.get_user(doc.updated_by_user).pk

            # call parent class's save method directly
            super(Document, doc).save(force_insert=True, using=self.target_db)

            document_id_map[old_id] = doc.pk

            # attachments
            for attachment in attachments:
                self.stdout.write(self.style.SUCCESS('Copying attachment %s for %s' % (attachment.filename, key)))

                attachment.pk = None
                attachment.document_id = doc.pk
                attachment.save(force_insert=True, using=self.target_db)
                # update attachment id
                new_name = attachment_filename(attachment, attachment.filename)
                attachment_map[attachment.file.name] = new_name
                Attachment.objects.using(self.target_db).filter(pk=attachment.pk).update(file=new_name)

            # notes without parents first
            notes = sorted(notes, key=lambda: 1 if note.in_reply_to else 0)
            parents = {}

            # annotations
            for note in notes:
                self.stdout.write(self.style.SUCCESS('Copying annotation %d for %s' % (note.pk, key)))

                parents[note.pk] = note

                note.pk = None
                if note.created_by_user:
                    note.created_by_user_id = self.get_user(note.created_by_user).pk
                note.document_id = doc.id
                if note.in_reply_to:
                    note.in_reply_to_id = parents[note.in_reply_to_id].pk
                note.save(force_insert=True, using=self.target_db)

        self.stdout.write(self.style.SUCCESS('Document ID mapping: %s' % document_id_map))
        self.stdout.write(self.style.SUCCESS('Attachment filename mapping: %s' % attachment_map))
