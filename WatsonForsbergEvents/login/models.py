from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from people.models import Person


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    person = models.OneToOneField(Person, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.user.username


@receiver(post_save, sender=User)
def auto_link_user_to_person(sender, instance, **kwargs):  # noqa: ARG001
    if not instance.email:
        return
    # Skip if already linked
    if UserProfile.objects.filter(user=instance).exists():
        return
    try:
        person = Person.objects.get(email=instance.email, is_watson_forsberg=True)
        if not UserProfile.objects.filter(person=person).exists():
            UserProfile.objects.create(user=instance, person=person)
    except Person.DoesNotExist:
        pass
