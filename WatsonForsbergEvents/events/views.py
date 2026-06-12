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

    # Check if guest already exists
    guest_exists = EventGuest.objects.filter(event=event, person=person).exists()
    if guest_exists:
        guest = EventGuest.objects.get(event=event, person=person)
        return JsonResponse({
            'created': False,
            'already_exists': True,
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
        }, status=409)

    guest = EventGuest.objects.create(event=event, person=person)

    return JsonResponse({
        'created': True,
        'already_exists': False,
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

    allowed = {'invited', 'invited_date', 'able_to_come', 'registered', 'attended'}
    for field, value in data.items():
        if field in allowed:
            setattr(guest, field, value)
    if guest.able_to_come:
        guest.invited = True
    if guest.registered:
        guest.invited = True
        guest.able_to_come = True
    if  guest.attended:
        guest.invited = True
        guest.able_to_come = True
        guest.registered = True
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
    event.event_type = data.get('event_type', '').strip()
    event.budget_materials_proposed = data.get('budget_materials_proposed') or None
    event.budget_materials_actual   = data.get('budget_materials_actual')   or None
    event.budget_venue_proposed     = data.get('budget_venue_proposed')     or None
    event.budget_venue_actual       = data.get('budget_venue_actual')       or None
    event.budget_tickets_proposed   = data.get('budget_tickets_proposed')   or None
    event.budget_tickets_actual     = data.get('budget_tickets_actual')     or None
    event.budget_misc_proposed      = data.get('budget_misc_proposed')      or None
    event.budget_misc_actual        = data.get('budget_misc_actual')        or None

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
            attended_count=Count('event_guests', filter=Q(event_guests__attended=True)),
        )
        .order_by('date')
    )

    rows = []
    tot_guests = tot_invited = tot_able = tot_registered = tot_attended = 0
    tot_mat_p = tot_mat_a = tot_ven_p = tot_ven_a = 0
    tot_tic_p = tot_tic_a = tot_mis_p = tot_mis_a = 0

    def _f(v):
        return float(v) if v is not None else None

    for ev in events:
        tot_guests     += ev.guests_total
        tot_invited    += ev.invited_count
        tot_able       += ev.able_count
        tot_registered += ev.registered_count
        tot_attended   += ev.attended_count
        tot_mat_p += float(ev.budget_materials_proposed or 0)
        tot_mat_a += float(ev.budget_materials_actual   or 0)
        tot_ven_p += float(ev.budget_venue_proposed     or 0)
        tot_ven_a += float(ev.budget_venue_actual       or 0)
        tot_tic_p += float(ev.budget_tickets_proposed   or 0)
        tot_tic_a += float(ev.budget_tickets_actual     or 0)
        tot_mis_p += float(ev.budget_misc_proposed      or 0)
        tot_mis_a += float(ev.budget_misc_actual        or 0)
        tp = ev.total_budget_proposed
        ta = ev.total_budget_actual
        rows.append({
            'id': ev.id,
            'name': ev.name,
            'date': ev.date.isoformat(),
            'client': ev.client.name if ev.client else '',
            'event_type': ev.event_type,
            'event_type_display': ev.get_event_type_display() if ev.event_type else '',
            'num_tickets': ev.num_tickets,
            'guests_total': ev.guests_total,
            'invited': ev.invited_count,
            'able_to_come': ev.able_count,
            'registered': ev.registered_count,
            'attended': ev.attended_count,
            'reg_rate': round(ev.registered_count / ev.invited_count * 100) if ev.invited_count else 0,
            'total_proposed': _f(tp),
            'total_actual':   _f(ta),
            'budget_materials_proposed': _f(ev.budget_materials_proposed),
            'budget_materials_actual':   _f(ev.budget_materials_actual),
            'budget_venue_proposed':     _f(ev.budget_venue_proposed),
            'budget_venue_actual':       _f(ev.budget_venue_actual),
            'budget_tickets_proposed':   _f(ev.budget_tickets_proposed),
            'budget_tickets_actual':     _f(ev.budget_tickets_actual),
            'budget_misc_proposed':      _f(ev.budget_misc_proposed),
            'budget_misc_actual':        _f(ev.budget_misc_actual),
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
            'attended': tot_attended,
            'avg_reg_rate': avg_rate,
            'total_proposed': tot_mat_p + tot_ven_p + tot_tic_p + tot_mis_p,
            'total_actual':   tot_mat_a + tot_ven_a + tot_tic_a + tot_mis_a,
            'budget_categories': {
                'materials': {'proposed': tot_mat_p, 'actual': tot_mat_a},
                'venue':     {'proposed': tot_ven_p, 'actual': tot_ven_a},
                'tickets':   {'proposed': tot_tic_p, 'actual': tot_tic_a},
                'misc':      {'proposed': tot_mis_p, 'actual': tot_mis_a},
            },
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
        event_type=data.get('event_type', '').strip(),
        budget_materials_proposed=data.get('budget_materials_proposed') or None,
        budget_materials_actual=data.get('budget_materials_actual')     or None,
        budget_venue_proposed=data.get('budget_venue_proposed')         or None,
        budget_venue_actual=data.get('budget_venue_actual')             or None,
        budget_tickets_proposed=data.get('budget_tickets_proposed')     or None,
        budget_tickets_actual=data.get('budget_tickets_actual')         or None,
        budget_misc_proposed=data.get('budget_misc_proposed')           or None,
        budget_misc_actual=data.get('budget_misc_actual')               or None,
        client=client,
        created_by=request.user,
        updated_by=request.user,
    )
    return JsonResponse({'id': event.id, 'name': event.name, 'date': event.date.isoformat()})
