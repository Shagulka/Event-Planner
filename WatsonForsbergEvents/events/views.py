import datetime
import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.conf import settings
from .models import Event, EventGuest
from people.models import Person


@login_required
def index(request):
    today = datetime.date.today()
    events = Event.objects.select_related("client").order_by("date")

    return render(request, "event_list.html", {
        "upcoming_events": events.filter(date__gte=today),
        "past_events": events.filter(date__lt=today),
        "today": today,
        "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
    })


@login_required
@require_GET
def event_guests(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    guests = (
        EventGuest.objects
        .filter(event=event)
        .select_related("person")
        .order_by("person__last_name", "person__first_name")
    )
    data = [
        {
            "person_id": g.person_id,
            "name": g.person.name,
            "email": g.person.email,
            "phone": g.person.phone_number,
            "company": g.person.company,
            "title": g.person.title,
            "to_invite": g.to_invite,
            "invited": g.invited,
            "invited_date": g.invited_date.isoformat() if g.invited_date else None,
            "able_to_come": g.able_to_come,
            "registered": g.registered,
            "attended": g.attended,
        }
        for g in guests
    ]
    return JsonResponse({"event": event.name, "guests": data})


@login_required
@require_POST
def event_guest_add(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    person_id = data.get('person_id')
    if not person_id:
        return JsonResponse({'error': 'person_id required'}, status=400)

    person = get_object_or_404(Person, pk=person_id)
    guest, created = EventGuest.objects.get_or_create(event=event, person=person)

    return JsonResponse({
        'created': created,
        'person_id': person.id,
        'name': person.name,
        'email': person.email,
        'phone': person.phone_number,
        'company': person.company,
        'title': person.title,
        'to_invite': guest.to_invite,
        'invited': guest.invited,
        'invited_date': guest.invited_date.isoformat() if guest.invited_date else None,
        'able_to_come': guest.able_to_come,
        'registered': guest.registered,
        'attended': guest.attended,
    })


@login_required
@require_POST
def event_guest_remove(request, event_id, person_id):
    event = get_object_or_404(Event, pk=event_id)
    EventGuest.objects.filter(event=event, person_id=person_id).delete()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def event_guest_update(request, event_id, person_id):
    event = get_object_or_404(Event, pk=event_id)
    guest = get_object_or_404(EventGuest, event=event, person_id=person_id)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    allowed = {'to_invite', 'invited', 'invited_date', 'able_to_come', 'registered', 'attended'}
    for field, value in data.items():
        if field in allowed:
            setattr(guest, field, value)
    guest.save()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def event_update(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    name_str = data.get('name', '').strip()
    date_str = data.get('date', '').strip()
    if not name_str or not date_str:
        return JsonResponse({'error': 'name and date are required'}, status=400)

    try:
        event.date = datetime.date.fromisoformat(date_str)
    except ValueError:
        return JsonResponse({'error': 'Invalid date'}, status=400)

    event.name = name_str

    event.time = None
    if data.get('time'):
        try:
            event.time = datetime.time.fromisoformat(data['time'])
        except ValueError:
            pass

    from clients.models import Client
    event.client = Client.objects.filter(pk=data['client_id']).first() if data.get('client_id') else None

    event.location = data.get('location', '')
    event.description = data.get('description', '')
    event.notes = data.get('notes', '')
    event.num_tickets = data.get('num_tickets') or None
    event.registrations_due = data.get('registrations_due') or None
    event.proposed_amount = data.get('proposed_amount') or None
    event.approved_amount = data.get('approved_amount') or None
    event.save()
    return JsonResponse({'id': event.id, 'name': event.name})


@login_required
@require_POST
def event_create(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    date_str = data.get('date', '').strip()
    name_str = data.get('name', '').strip()
    if not name_str or not date_str:
        return JsonResponse({'error': 'name and date are required'}, status=400)

    try:
        date = datetime.date.fromisoformat(date_str)
    except ValueError:
        return JsonResponse({'error': 'Invalid date'}, status=400)

    time = None
    if data.get('time'):
        try:
            time = datetime.time.fromisoformat(data['time'])
        except ValueError:
            pass

    from clients.models import Client
    client = None
    if data.get('client_id'):
        client = Client.objects.filter(pk=data['client_id']).first()

    event = Event.objects.create(
        name=name_str,
        date=date,
        time=time,
        location=data.get('location', ''),
        description=data.get('description', ''),
        notes=data.get('notes', ''),
        num_tickets=data.get('num_tickets') or None,
        registrations_due=data.get('registrations_due') or None,
        proposed_amount=data.get('proposed_amount') or None,
        approved_amount=data.get('approved_amount') or None,
        client=client,
    )
    return JsonResponse({'id': event.id, 'name': event.name, 'date': event.date.isoformat()})
