from django.conf import settings
from django.core.management.base import BaseCommand

import dj_database_url

from indigo_api.models import Work, Locality, Country, Language
from django.contrib.auth.models import User


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

        self.copy_languages()
        self.copy_places()
        #self.copy_users()

    def setup_db(self, dburl):
        self.source_db = 'source-db'
        self.target_db = 'default'

        dbconfig = dj_database_url.parse(dburl)
        settings.DATABASES[self.source_db] = dbconfig
        self.stdout.write(self.style.SUCCESS('Copying \n  FROM %s\n    TO %s' % (dbconfig, settings.DATABASES[self.target_db])))

    def copy_users(self):
        # TODO: only copy some users? maybe only those that created/edited documents and works
        # what about the Editor object?
        # what about social logins? - they can't be copied

        existing = User.objects.only("username", "email")
        usernames = set(u.username for u in existing)
        emails = set(u.email for u in existing)

        for src in User.objects.using(self.source_db).all():
            if src.username in usernames:
                self.stdout.write(self.style.WARNING('Ignoring existing user with username %s' % src.username))
                continue

            if src.email in emails:
                self.stdout.write(self.style.WARNING('Ignoring existing user with email %s' % src.email))
                continue

            self.stdout.write(self.style.SUCCESS('Will copy user %s' % src))
            if not self.dry_run:
                src.pk = None
                src.save(force_insert=True, using=self.target_db)

    def copy_languages(self):
        self.languages = {lang.code: lang for lang in Language.objects.all()}

        for lang in Language.objects.using(self.source_db).all():
            if lang.code in self.languages:
                self.stdout.write(self.style.WARNING('Ignoring existing language %s' % lang.code))
                continue

            self.stdout.write(self.style.SUCCESS('Will create language %s' % lang.code))
            if not self.dry_run:
                lang.pk = None
                lang.save(force_insert=True, using=self.target_db)

    def copy_places(self):
        self.countries = {c.code: c for c in Country.objects.all()}

        for country in Country.objects.using(self.source_db).all():
            if country.code in self.countries:
                self.stdout.write(self.style.WARNING('Ignoring existing country %s' % country.code))
                continue

            self.stdout.write(self.style.SUCCESS('Will create country %s' % country.code))
            if not self.dry_run:
                country.pk = None
                country.primary_language_id = self.languages[country.primary_language].pk
                country.save(force_insert=True, using=self.target_db)

        # reload
        self.countries = {c.code: c for c in Country.objects.all()}
        self.localities = {c.place_code: c for c in Locality.objects.all()}

        for loc in Locality.objects.using(self.source_db).all():
            if loc.place_code in self.localities:
                self.stdout.write(self.style.WARNING('Ignoring existing locality %s' % loc.place_code))
                continue

            self.stdout.write(self.style.SUCCESS('Will create locality %s' % loc.place_code))
            if not self.dry_run:
                loc.pk = None
                loc.country_id = self.countries[loc.country.code].pk
                loc.save(force_insert=True, using=self.target_db)
