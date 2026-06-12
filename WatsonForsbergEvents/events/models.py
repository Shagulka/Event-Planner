from django.db import models

class EventGuest(models.Model):
    event = models.ForeignKey('Event', on_delete=models.CASCADE, related_name='event_guests')
    person = models.ForeignKey('people.Person', on_delete=models.CASCADE, related_name='event_guests')
    invited = models.BooleanField(default=False)
    invited_date = models.DateField(null=True, blank=True)
    able_to_come = models.BooleanField(default=False)
    registered = models.BooleanField(default=False)
    attended   = models.BooleanField(default=False)

    class Meta:
        unique_together = ('event', 'person')

    def __str__(self):
        return f"{self.person} — {self.event}"

class Event(models.Model):
    client = models.ForeignKey('clients.Client', on_delete=models.SET_NULL, null=True, blank=True, related_name='events')
    name = models.CharField(max_length=200)
    date = models.DateField()
    time = models.TimeField(null=True, blank=True)
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
        OTHER      = 'OTHER',      'Other'

    event_type = models.CharField(max_length=20, choices=EventType.choices, blank=True, default='')

    budget_materials_proposed = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    budget_materials_actual   = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    budget_venue_proposed     = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    budget_venue_actual       = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    budget_tickets_proposed   = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    budget_tickets_actual     = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    budget_misc_proposed      = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    budget_misc_actual        = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    @property
    def total_budget_proposed(self):
        vals = [v for v in [
            self.budget_materials_proposed, self.budget_venue_proposed,
            self.budget_tickets_proposed, self.budget_misc_proposed,
        ] if v is not None]
        return sum(vals) if vals else None

    @property
    def total_budget_actual(self):
        vals = [v for v in [
            self.budget_materials_actual, self.budget_venue_actual,
            self.budget_tickets_actual, self.budget_misc_actual,
        ] if v is not None]
        return sum(vals) if vals else None

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