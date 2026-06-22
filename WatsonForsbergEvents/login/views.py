import datetime

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render, redirect

from events.models import Event, EventGuest
from people.models import Person
from .models import UserProfile


def _try_link_user_to_person(user):
    """Auto-link a user to a WF staff person with the same email, if not already linked."""
    if not user.email or UserProfile.objects.filter(user=user).exists():
        return
    try:
        person = Person.objects.get(email__iexact=user.email, is_watson_forsberg=True)
        if not UserProfile.objects.filter(person=person).exists():
            UserProfile.objects.create(user=user, person=person)
    except Person.DoesNotExist:
        pass


def login_view(request):
    next_url = request.GET.get("next") or request.POST.get("next") or "/events/"
    if request.user.is_authenticated:
        return redirect(next_url)

    error = None
    username = ""

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            _try_link_user_to_person(user)
            return redirect(next_url)
        error = "Invalid username or password."

    return render(request, "login.html", {"error": error, "username": username, "next": next_url})


def logout_view(request):
    logout(request)
    return redirect("/login/")


@login_required
def my_events(request):
    # One-time auto-link for users who existed before the signal was added
    _try_link_user_to_person(request.user)

    try:
        person = request.user.userprofile.person
    except UserProfile.DoesNotExist:
        person = None

    if not person:
        return render(request, "my_events.html", {"no_profile": True})

    today = datetime.date.today()

    guest_records = {
        eg.event_id: eg
        for eg in EventGuest.objects.filter(person=person)
    }

    all_events = list(
        Event.objects
        .filter(id__in=guest_records.keys())
        .select_related("client")
        .annotate(
            uninvited_count=Count("event_guests", filter=Q(event_guests__invited=False), distinct=True),
            total_guests=Count("event_guests", distinct=True),
        )
        .order_by("date")
    )
    for ev in all_events:
        ev.my_guest = guest_records.get(ev.id)

    upcoming = [
        ev for ev in all_events
        if (ev.end_date and ev.end_date >= today) or (not ev.end_date and ev.date >= today)
    ]
    past = [
        ev for ev in all_events
        if (ev.end_date and ev.end_date < today) or (not ev.end_date and ev.date < today)
    ]

    return render(request, "my_events.html", {
        "person": person,
        "upcoming_events": upcoming,
        "past_events": past,
        "today": today,
        "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
    })
