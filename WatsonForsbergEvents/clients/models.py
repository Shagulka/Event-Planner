from django.db import models

class Client(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    contact_person = models.ForeignKey('people.Person', null=True, blank=True, on_delete=models.SET_NULL, related_name='contact_for')
    address = models.TextField(blank=True)
    market_area = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name
