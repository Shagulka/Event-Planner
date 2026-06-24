import datetime
import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.conf import settings
from django.db.models import Count, Q
import requests
from .models import Event, EventGuest, EventBudget, BudgetLineItem, BUDGET_CATEGORIES
from .permissions import require_edit_perm
from people.models import Person


@login_required
def index(request):
    today = datetime.date.today()
    events = (
        Event.objects
        .select_related("client")
        .annotate(
            uninvited_count=Count(
                'event_guests',
                filter=Q(event_guests__invited=False),
                distinct=True,
            ),
            total_guests=Count('event_guests', distinct=True),
        )
        .order_by("date")
    )

    upcoming_q = Q(end_date__gte=today) | Q(end_date__isnull=True, date__gte=today)
    past_q     = Q(end_date__lt=today)  | Q(end_date__isnull=True, date__lt=today)

    type_display = dict(Event.EventType.choices)
    raw_counts = (
        Event.objects
        .filter(upcoming_q)
        .exclude(event_type='')
        .values('event_type')
        .annotate(n=Count('id'))
        .order_by('event_type')
    )
    upcoming_type_counts = ' · '.join(
        f"{row['n']} {type_display.get(row['event_type'], row['event_type'])}"
        for row in raw_counts
    )

    return render(request, "event_list.html", {
        "upcoming_events": events.filter(upcoming_q).order_by("date"),
        "past_events": events.filter(past_q).order_by("date"),
        "today": today,
        "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
        "upcoming_type_counts": upcoming_type_counts,
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
            "added_on_calendar": g.added_on_calendar,
        }
        for g in guests
    ]
    return JsonResponse({"event": event.name, "guests": data})


@login_required
@require_edit_perm
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
@require_edit_perm
@require_POST
def event_guest_remove(request, event_id, person_id):
    event = get_object_or_404(Event, pk=event_id)
    EventGuest.objects.filter(event=event, person_id=person_id).delete()
    return JsonResponse({'ok': True})


@login_required
@require_edit_perm
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
    if guest.attended:
        guest.invited = True
        guest.able_to_come = True
        guest.registered = True
    guest.save()
    return JsonResponse({'ok': True})


def get_access_token():
    URL = f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": settings.MICROSOFT_CALENDAR_API_CLIENT_ID,
        "client_secret": settings.MICROSOFT_CALENDAR_API_CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
    }
    response = requests.post(URL, data=data)
    if response.status_code == 200:
        return response.json().get('access_token')
    return None



def _build_calendar_payload(event):
    is_all_day = not event.time
    is_multiple_day = bool(event.end_date and event.end_date != event.date)

    if is_all_day:
        start_dt = event.date.isoformat() + "T00:00:00"
        end_dt = ((event.end_date or event.date) + datetime.timedelta(days=1)).isoformat() + "T00:00:00"
    elif is_multiple_day:
        start_dt = event.date.isoformat() + "T" + event.time.isoformat()
        end_dt = (event.end_date.isoformat() + "T" + event.end_time.isoformat()) if event.end_time \
            else event.end_date.isoformat() + "T23:59:00"
    else:
        start_dt = event.date.isoformat() + "T" + event.time.isoformat()
        end_dt = ((event.end_date or event.date).isoformat() + "T" + event.end_time.isoformat()) if event.end_time \
            else (datetime.datetime.combine(event.date, event.time) + datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")

    return {
        "subject": event.name,
        "showAs": "free" if is_all_day or is_multiple_day else "busy",
        "isAllDay": is_all_day,
        "start": {"dateTime": start_dt, "timeZone": "Central Standard Time"},
        "end":   {"dateTime": end_dt,   "timeZone": "Central Standard Time"},
        "location": {"displayName": event.location or ""},
        "body": {"contentType": "HTML", "content": event.description or ""},
    }


@login_required
@require_edit_perm
@require_GET
def add_to_calendar(request, event_id):
    URL = f"https://graph.microsoft.com/v1.0/users/{settings.MICROSOFT_CALENDAR_USER}/events"
    event = get_object_or_404(Event, pk=event_id)
    data = _build_calendar_payload(event)
    token = get_access_token()
    if not token:
        return JsonResponse({'error': 'Could not obtain Microsoft access token'}, status=502)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response = requests.post(URL, headers=headers, json=data)
    if response.status_code == 201:
        graph_id = response.json().get('id', '')
        if graph_id:
            event.calendar_event_id = graph_id
            event.save(update_fields=['calendar_event_id'])
        return JsonResponse({'ok': True})
    else:
        return JsonResponse({'error': 'Failed to add to calendar'}, status=500)


@login_required
@require_edit_perm
@require_POST
def add_guests_to_calendar(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    pending_guests = (
        EventGuest.objects
        .filter(event=event, able_to_come=True, added_on_calendar=False)
        .select_related('person')
    )

    BASE_URL = f"https://graph.microsoft.com/v1.0/users/{settings.MICROSOFT_CALENDAR_USER}/events"
    token = get_access_token()
    if not token:
        return JsonResponse({'error': 'Could not obtain Microsoft access token'}, status=502)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Resolve the Graph calendar event ID
    graph_event_id = event.calendar_event_id
    if not graph_event_id:
        res = requests.get(BASE_URL, headers=headers)
        if res.status_code == 200:
            for ev in res.json().get('value', []):
                if ev.get('subject') == event.name:
                    graph_event_id = ev['id']
                    break
    if not graph_event_id:
        return JsonResponse({'error': 'Calendar event not found — add the event to the calendar first'}, status=404)

    event_url = f"{BASE_URL}/{graph_event_id}"

    # Fetch existing attendees so we don't clobber them
    res = requests.get(event_url, headers=headers)
    existing_attendees = res.json().get('attendees', []) if res.status_code == 200 else []
    existing_emails = {a['emailAddress']['address'].lower() for a in existing_attendees}

    new_attendees = []
    guests_to_mark = []
    for guest in pending_guests:
        if guest.person.email and guest.person.email.lower() not in existing_emails:
            new_attendees.append({
                "emailAddress": {"address": guest.person.email, "name": guest.person.name},
                "type": "required",
            })
            existing_emails.add(guest.person.email.lower())
        guests_to_mark.append(guest)

    if new_attendees:
        patch_res = requests.patch(
            event_url,
            headers=headers,
            json={"attendees": existing_attendees + new_attendees},
        )
        if patch_res.status_code not in (200, 204):
            return JsonResponse({'error': 'Failed to update calendar attendees'}, status=500)

    # Mark all coming guests as added (even those already on calendar)
    ids = [g.id for g in guests_to_mark]
    EventGuest.objects.filter(id__in=ids).update(added_on_calendar=True)

    return JsonResponse({'ok': True, 'added': len(new_attendees)})

@login_required
@require_edit_perm
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

    event.end_date = None
    if data.get('end_date'):
        try:
            event.end_date = datetime.date.fromisoformat(data['end_date'])
        except ValueError:
            pass

    event.end_time = None
    if data.get('end_time'):
        try:
            event.end_time = datetime.time.fromisoformat(data['end_time'])
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

    event.updated_by = request.user
    event.save()

    if event.calendar_event_id:
        token = get_access_token()
        if token:
            cal_url = f"https://graph.microsoft.com/v1.0/users/{settings.MICROSOFT_CALENDAR_USER}/events/{event.calendar_event_id}"
            requests.patch(cal_url, headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }, json=_build_calendar_payload(event))

    return JsonResponse({'id': event.id, 'name': event.name})


@login_required
@require_GET
def event_budget(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    try:
        budget = event.budget
        line_items = [
            {
                'id': li.id,
                'category': li.category,
                'name': li.name,
                'proposed_amount': float(li.proposed_amount) if li.proposed_amount is not None else None,
                'actual_amount': float(li.actual_amount) if li.actual_amount is not None else None,
            }
            for li in budget.line_items.all()
        ]
    except EventBudget.DoesNotExist:
        line_items = []
    return JsonResponse({'line_items': line_items})


@login_required
@require_edit_perm
@require_POST
def event_budget_save(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    valid_categories = {k for k, _ in BUDGET_CATEGORIES}
    line_items = data.get('line_items', [])

    budget, _ = EventBudget.objects.get_or_create(event=event)
    budget.line_items.all().delete()

    for item in line_items:
        category = item.get('category', '').strip()
        name = item.get('name', '').strip()
        if not category or category not in valid_categories or not name:
            continue
        BudgetLineItem.objects.create(
            budget=budget,
            category=category,
            name=name,
            proposed_amount=item.get('proposed_amount') or None,
            actual_amount=item.get('actual_amount') or None,
        )

    return JsonResponse({'ok': True})


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
        .filter(date__lte=to_date)
        .filter(Q(end_date__gte=from_date) | Q(end_date__isnull=True, date__gte=from_date))
        .select_related('client', 'budget')
        .prefetch_related('budget__line_items')
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
    agg_categories = {}

    for ev in events:
        tot_guests     += ev.guests_total
        tot_invited    += ev.invited_count
        tot_able       += ev.able_count
        tot_registered += ev.registered_count
        tot_attended   += ev.attended_count

        try:
            cat_totals = ev.budget.category_totals()
            total_a = sum(v['actual'] for v in cat_totals.values()) or None
            total_p = sum(v['proposed'] for v in cat_totals.values()) or None
            if total_a is not None and total_p is None:
                # Has actual but no proposed — treat proposed as actual
                total_p = total_a
                for cat in cat_totals:
                    cat_totals[cat]['proposed'] = cat_totals[cat]['actual']
        except EventBudget.DoesNotExist:
            cat_totals = {}
            total_p = None
            total_a = None

        # Category breakdown aggregates only events that have actual figures
        # (keeps utilisation/progress bars accurate)
        if total_a is not None:
            for cat, vals in cat_totals.items():
                if cat not in agg_categories:
                    agg_categories[cat] = {'proposed': 0.0, 'actual': 0.0}
                agg_categories[cat]['proposed'] += vals['proposed']
                agg_categories[cat]['actual'] += vals['actual']

        rows.append({
            'id': ev.id,
            'name': ev.name,
            'date': ev.date.isoformat(),
            'end_date': ev.end_date.isoformat() if ev.end_date else None,
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
            'total_proposed': total_p,
            'total_actual': total_a,
            'budget_categories': {
                cat: {'proposed': v['proposed'], 'actual': v['actual']}
                for cat, v in cat_totals.items()
            },
        })

    avg_rate = round(tot_registered / tot_invited * 100) if tot_invited else 0
    tot_p = sum(v['proposed'] for v in agg_categories.values())
    tot_a = sum(v['actual'] for v in agg_categories.values())

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
            'total_proposed': tot_p,
            'total_actual': tot_a,
            'budget_categories': agg_categories,
        },
    })


@login_required
@require_edit_perm
@require_POST
def event_delete(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    event.delete()
    return JsonResponse({'ok': True})


@login_required
@require_edit_perm
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

    end_date = None
    if data.get('end_date'):
        try:
            end_date = datetime.date.fromisoformat(data['end_date'])
        except ValueError:
            pass

    end_time = None
    if data.get('end_time'):
        try:
            end_time = datetime.time.fromisoformat(data['end_time'])
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
        end_date=end_date,
        end_time=end_time,
        location=data.get('location', ''),
        description=data.get('description', ''),
        notes=data.get('notes', ''),
        num_tickets=data.get('num_tickets') or None,
        registrations_due=data.get('registrations_due') or None,
        event_type=data.get('event_type', '').strip(),
        client=client,
        created_by=request.user,
        updated_by=request.user,
    )
    return JsonResponse({'id': event.id, 'name': event.name, 'date': event.date.isoformat()})
