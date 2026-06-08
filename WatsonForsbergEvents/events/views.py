import datetime
import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.conf import settings
from django.db.models import Count, Q
from .models import Event, EventGuest
from people.models import Person


@login_required
def index(request):
    today = datetime.date.today()
    events = (
        Event.objects
        .select_related("client")
        .annotate(uninvited_count=Count(
            'event_guests',
            filter=Q(event_guests__invited=False)
        ))
        .order_by("date")
    )

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
        .prefetch_related("person__company")
        .order_by("person__last_name", "person__first_name")
    )
    data = [
        {
            "person_id": g.person_id,
            "name": g.person.name,
            "email": g.person.email,
            "phone": g.person.phone_number,
            "company": ', '.join(c.name for c in g.person.company.all()),
            "title": g.person.title,
            "invited": g.invited,
            "invited_date": g.invited_date.isoformat() if g.invited_date else None,
            "able_to_come": g.able_to_come,
            "registered": g.registered,
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
        'company': ', '.join(c.name for c in person.company.all()),
        'title': person.title,
        'invited': guest.invited,
        'invited_date': guest.invited_date.isoformat() if guest.invited_date else None,
        'able_to_come': guest.able_to_come,
        'registered': guest.registered,
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

    allowed = {'invited', 'invited_date', 'able_to_come', 'registered'}
    for field, value in data.items():
        if field in allowed:
            setattr(guest, field, value)
    if guest.able_to_come:
        guest.invited = True
    if guest.registered:
        guest.invited = True
        guest.able_to_come = True
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

    event.updated_by = request.user
    event.save()
    return JsonResponse({'id': event.id, 'name': event.name})

@login_required
def event_registration(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    return render(request, 'registration.html', {'event': event})


@login_required
def metrics(request):
    today = datetime.date.today()
    return render(request, 'metrics.html', {
        'default_from': today.replace(month=1, day=1).isoformat(),
        'default_to': today.isoformat(),
    })


@login_required
@require_GET
def metrics_data(request):
    today = datetime.date.today()
    from_str = request.GET.get('from', '')
    to_str = request.GET.get('to', '')
    try:
        from_date = datetime.date.fromisoformat(from_str) if from_str else today.replace(month=1, day=1)
        to_date = datetime.date.fromisoformat(to_str) if to_str else today
    except ValueError:
        return JsonResponse({'error': 'Invalid date'}, status=400)

    events = (
        Event.objects
        .filter(date__gte=from_date, date__lte=to_date)
        .select_related('client')
        .annotate(
            guests_total=Count('event_guests'),
            invited_count=Count('event_guests', filter=Q(event_guests__invited=True)),
            able_count=Count('event_guests', filter=Q(event_guests__able_to_come=True)),
            registered_count=Count('event_guests', filter=Q(event_guests__registered=True)),
        )
        .order_by('date')
    )

    rows = []
    tot_guests = tot_invited = tot_able = tot_registered = 0
    for ev in events:
        tot_guests     += ev.guests_total
        tot_invited    += ev.invited_count
        tot_able       += ev.able_count
        tot_registered += ev.registered_count
        rows.append({
            'id': ev.id,
            'name': ev.name,
            'date': ev.date.isoformat(),
            'client': ev.client.name if ev.client else '',
            'num_tickets': ev.num_tickets,
            'proposed': float(ev.proposed_amount) if ev.proposed_amount else None,
            'approved': float(ev.approved_amount) if ev.approved_amount else None,
            'guests_total': ev.guests_total,
            'invited': ev.invited_count,
            'able_to_come': ev.able_count,
            'registered': ev.registered_count,
            'reg_rate': round(ev.registered_count / ev.invited_count * 100) if ev.invited_count else 0,
        })

    avg_rate = round(tot_registered / tot_invited * 100) if tot_invited else 0
    return JsonResponse({
        'events': rows,
        'totals': {
            'event_count': len(rows),
            'guests_total': tot_guests,
            'invited': tot_invited,
            'able': tot_able,
            'registered': tot_registered,
            'avg_reg_rate': avg_rate,
        },
    })


@login_required
@require_POST
def event_delete(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    event.delete()
    return JsonResponse({'ok': True})

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
        created_by=request.user,
        updated_by=request.user,
    )
    return JsonResponse({'id': event.id, 'name': event.name, 'date': event.date.isoformat()})
