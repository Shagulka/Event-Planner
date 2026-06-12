import csv
import os
from django.core.management.base import BaseCommand
from django.db import transaction
from clients.models import Client
from people.models import Person


CSV_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', '..', 'WFcontacts.csv'
)



def _parse_name(full_name):
    """Parse 'Last, First' or 'First Last' into (first, last)."""
    full_name = full_name.strip()
    if ',' in full_name:
        last, _, first = full_name.partition(',')
        return first.strip(), last.strip()
    parts = full_name.split()
    if len(parts) >= 2:
        return ' '.join(parts[:-1]), parts[-1]
    return full_name, ''


class Command(BaseCommand):
    help = 'Seed the database with people and companies from WFcontacts.csv'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete all existing Person and Client records before seeding',
        )

    @transaction.atomic
    def handle(self, *_args, **options):
        if options['clear']:
            Person.objects.all().delete()
            Client.objects.all().delete()
            self.stdout.write(self.style.WARNING('Cleared existing people and companies.'))

        csv_path = os.path.normpath(CSV_PATH)
        if not os.path.exists(csv_path):
            self.stderr.write(f'CSV not found at: {csv_path}')
            return

        # First pass: collect unique companies with their address/market_area/phone
        companies = {}  # name -> {address, market_area, phone}
        rows = []
        with open(csv_path, newline='', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                rows.append(row)
                company_name = row.get('Company Name', '').strip()
                if company_name and company_name not in companies:
                    companies[company_name] = {
                        'address': row.get('Business Address', '').strip(),
                        'market_area': row.get('Market Areas', '').strip(),
                        'phone': (row.get('Office Phone') or '').strip(),
                    }

        # Create or update Client records
        client_map = {}  # company_name -> Client instance
        created_companies = 0
        for name, data in companies.items():
            client, created = Client.objects.get_or_create(
                name=name,
                defaults={
                    'address': data['address'],
                    'market_area': data['market_area'],
                    'phone': data['phone'],
                },
            )
            client_map[name] = client
            if created:
                created_companies += 1

        self.stdout.write(f'Companies: {created_companies} created, {len(companies) - created_companies} already existed.')

        # Second pass: create Person records, link to companies, track key contacts
        created_people = 0
        skipped_people = 0
        # company_name -> first Person with Key Contact=1
        key_contacts = {}

        for row in rows:
            full_name = row.get('Full Name', '').strip()
            if not full_name:
                continue

            first_name, last_name = _parse_name(full_name)
            email = row.get('E-mail Address', '').strip()
            phone = (row.get('Direct Phone') or row.get('Office Phone') or '').strip()
            cell = (row.get('Cell') or '').strip()
            title = row.get('Title', '').strip()
            company_name = row.get('Company Name', '').strip()
            is_key = row.get('Key Contact', '').strip() == '1'

            # Use email + name as uniqueness key; fall back to name-only if no email
            lookup = {'first_name': first_name, 'last_name': last_name}
            if email:
                lookup['email'] = email

            person, created = Person.objects.get_or_create(
                **lookup,
                defaults={
                    'name': f'{first_name} {last_name}'.strip(),
                    'email': email,
                    'phone_number': phone,
                    'cell_phone_number': cell,
                    'title': title,
                    'is_watson_forsberg': company_name == 'Watson-Forsberg',
                },
            )

            if created:
                created_people += 1
            else:
                skipped_people += 1

            if company_name and company_name in client_map:
                person.company.add(client_map[company_name])
                if is_key and company_name not in key_contacts:
                    key_contacts[company_name] = person

        # Assign key contacts as contact_person on each Client
        assigned = 0
        for company_name, person in key_contacts.items():
            client = client_map[company_name]
            if not client.contact_person_id:
                client.contact_person = person
                client.save(update_fields=['contact_person'])
                assigned += 1

        self.stdout.write(f'People: {created_people} created, {skipped_people} already existed.')
        self.stdout.write(f'Key contacts assigned: {assigned}.')
        self.stdout.write(self.style.SUCCESS('Seeding complete.'))
