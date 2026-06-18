from decimal import InvalidOperation as _DecimalInvalidOperation

from django.core.exceptions import ObjectDoesNotExist
from django.db import models

BUDGET_CATEGORIES = [
    ('materials', 'Materials'),
    ('venue', 'Venue'),
    ('swag', 'Swag'),
    ('tickets', 'Tickets'),
    ('donations', 'Donations'),
    ('travel', 'Travel'),
    ('sponsorships', 'Sponsorships'),
    ('misc', 'Misc'),
]


class EventGuest(models.Model):
    event = models.ForeignKey('Event', on_delete=models.CASCADE, related_name='event_guests')
    person = models.ForeignKey('people.Person', on_delete=models.CASCADE, related_name='event_guests')
    invited = models.BooleanField(default=False)
    invited_date = models.DateField(null=True, blank=True)
    able_to_come = models.BooleanField(default=False)
    registered = models.BooleanField(default=False)
    attended = models.BooleanField(default=False)

    class Meta:
        unique_together = ('event', 'person')

    def __str__(self):
        return f"{self.person} — {self.event}"


class EventBudget(models.Model):
    event = models.OneToOneField('Event', on_delete=models.CASCADE, related_name='budget')

    @property
    def total_proposed(self):
        try:
            s = sum(float(li.proposed_amount or 0) for li in self.line_items.all())
            return s if s else None
        except (_DecimalInvalidOperation, TypeError, ValueError):
            return None

    @property
    def total_actual(self):
        try:
            s = sum(float(li.actual_amount or 0) for li in self.line_items.all())
            return s if s else None
        except (_DecimalInvalidOperation, TypeError, ValueError):
            return None

    def category_totals(self):
        totals = {}
        try:
            for li in self.line_items.all():
                if li.category not in totals:
                    totals[li.category] = {'proposed': 0.0, 'actual': 0.0}
                totals[li.category]['proposed'] += float(li.proposed_amount or 0)
                totals[li.category]['actual'] += float(li.actual_amount or 0)
        except (_DecimalInvalidOperation, TypeError, ValueError):
            pass
        return totals


class BudgetLineItem(models.Model):
    budget = models.ForeignKey(EventBudget, on_delete=models.CASCADE, related_name='line_items')
    category = models.CharField(max_length=20, choices=BUDGET_CATEGORIES)
    name = models.CharField(max_length=200)
    proposed_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    actual_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ['category', 'id']


class Event(models.Model):
    client = models.ForeignKey('clients.Client', on_delete=models.SET_NULL, null=True, blank=True, related_name='events')
    name = models.CharField(max_length=200)
    date = models.DateField()
    time = models.TimeField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    location = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    num_tickets = models.PositiveIntegerField(null=True, blank=True)
    registrations_due = models.DateField(null=True, blank=True)
    proposed_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    approved_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    guests = models.ManyToManyField('people.Person', through='EventGuest', related_name='events')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_events')
    updated_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_events')

    class EventType(models.TextChoices):
        CONFERENCE = 'CONFERENCE', 'Conference'
        MEETING    = 'MEETING',    'Meeting'
        PARTY      = 'PARTY',      'Party'
        FUNDRAISER = 'FUNDRAISER', 'Fundraiser'
        DONATION   = 'DONATION',   'Donation'
        AWARDS     = 'AWARDS',     'Awards'
        OTHER      = 'OTHER',      'Other'

    event_type = models.CharField(max_length=20, choices=EventType.choices, blank=True, default='')

    @property
    def total_budget_proposed(self):
        try:
            return self.budget.total_proposed
        except ObjectDoesNotExist:
            return None

    @property
    def total_budget_actual(self):
        try:
            return self.budget.total_actual
        except ObjectDoesNotExist:
            return None

    def __str__(self):
        return self.name


class EventPayment(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='payments')
    year = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('event', 'year')

    def __str__(self):
        return f"{self.event} — {self.year}: ${self.amount}"
