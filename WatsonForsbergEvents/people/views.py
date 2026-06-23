import datetime
import json
from django.db.models import Exists, OuterRef, Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from .models import Person


def _company_str(person):
    return ', '.join(c.name for c in person.company.all())


@login_required
def index(request):
    return render(request, "people_list.html", {})


@login_required
@require_GET
def people_data(request):
    from events.models import EventGuest
    today = datetime.date.today()
    people = (
        Person.objects
        .prefetch_related('company')
        .annotate(
            has_pending_invite=Exists(
                EventGuest.objects.filter(
                    person=OuterRef('pk'),
                    invited=False,
                    event__date__gte=today,
                )
            )
        )
        .order_by('last_name', 'first_name')
    )
    result = []
    for p in people:
        companies = list(p.company.all())
        result.append({
            'id': p.id,
            'name': p.name,
            'first_name': p.first_name,
            'last_name': p.last_name,
            'email': p.email,
            'phone_number': p.phone_number,
            'cell_phone_number': p.cell_phone_number,
            'company': ', '.join(c.name for c in companies),
            'client_id': str(companies[0].id) if companies else '',
            'title': p.title,
            'is_watson_forsberg': p.is_watson_forsberg,
            'notes': p.notes or '',
            'has_pending_invite': p.has_pending_invite,
        })
    return JsonResponse(result, safe=False)


@login_required
@require_GET
def search(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 1:
        return JsonResponse([], safe=False)
    people = (
        Person.objects
        .filter(Q(name__icontains=q) | Q(company__name__icontains=q))
        .distinct()
        .prefetch_related('company')
        .order_by('last_name', 'first_name')[:20]
    )
    return JsonResponse([
        {'id': p.id, 'name': p.name, 'company': _company_str(p), 'title': p.title, 'email': p.email}
        for p in people
    ], safe=False)

@login_required
@require_GET
def recommended_guests(request, event_id):
    from events.models import Event, EventGuest

    event = get_object_or_404(Event, pk=event_id)
    if not event.client_id:
        return JsonResponse([], safe=False)

    invited_person_ids = EventGuest.objects.filter(event=event).values_list('person_id', flat=True)
    recommended = (
        Person.objects
        .filter(company=event.client)
        .exclude(id__in=invited_person_ids)
        .prefetch_related('company')
        .order_by('last_name', 'first_name')
    )
    return JsonResponse([
        {'id': p.id, 'name': p.name, 'company': _company_str(p), 'title': p.title, 'email': p.email}
        for p in recommended
    ], safe=False)

@login_required
@require_GET
def detail(request, person_id):
    import datetime
    from events.models import EventGuest

    person = get_object_or_404(Person.objects.prefetch_related('company'), pk=person_id)
    today = datetime.date.today()

    guests = (
        EventGuest.objects
        .filter(person=person)
        .select_related('event', 'event__client')
        .order_by('event__date')
    )

    upcoming, past = [], []
    for g in guests:
        ev = g.event
        entry = {
            'id': ev.id,
            'name': ev.name,
            'date': ev.date.isoformat(),
            'location': ev.location,
            'client': ev.client.name if ev.client else '',
            'invited': g.invited,
            'able_to_come': g.able_to_come,
            'registered': g.registered,
            'attended': g.attended,
        }
        (upcoming if ev.date >= today else past).append(entry)

    past.reverse()

    return JsonResponse({
        'id': person.id,
        'name': person.name,
        'first_name': person.first_name,
        'last_name': person.last_name,
        'email': person.email,
        'phone_number': person.phone_number,
        'cell_phone_number': person.cell_phone_number,
        'companies': [{'id': c.id, 'name': c.name} for c in person.company.all()],
        'company': _company_str(person),
        'title': person.title,
        'is_watson_forsberg': person.is_watson_forsberg,
        'notes': person.notes,
        'upcoming_events': upcoming,
        'past_events': past,
    })


@login_required
@require_POST
def create(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    first_name = data.get('first_name', '').strip()
    last_name  = data.get('last_name', '').strip()
    if not first_name and not last_name:
        return JsonResponse({'error': 'First or last name is required'}, status=400)
    name = f"{first_name} {last_name}".strip()

    person = Person.objects.create(
        first_name=first_name,
        last_name=last_name,
        name=name,
        email=data.get('email', ''),
        phone_number=data.get('phone_number', ''),
        cell_phone_number=data.get('cell_phone_number', ''),
        title=data.get('title', ''),
        is_watson_forsberg=data.get('is_watson_forsberg', False),
        notes=data.get('notes', ''),
    )
    client_id = data.get('client_id') or None
    if client_id:
        person.company.set([client_id])

    if any(c.name == 'Watson-Forsberg' for c in person.company.all()):
        person.is_watson_forsberg = True
        person.save(update_fields=['is_watson_forsberg'])

    return JsonResponse({
        'id': person.id, 'name': person.name,
        'first_name': person.first_name, 'last_name': person.last_name,
        'email': person.email, 'phone_number': person.phone_number,
        'cell_phone_number': person.cell_phone_number,
        'companies': [{'id': c.id, 'name': c.name} for c in person.company.all()],
        'company': _company_str(person), 'title': person.title,
        'is_watson_forsberg': person.is_watson_forsberg,
        'notes': person.notes,
        'client_id': str(client_id) if client_id else '',
    })


@login_required
@require_POST
def update(request, person_id):
    person = get_object_or_404(Person, pk=person_id)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    first_name = data.get('first_name', '').strip()
    last_name  = data.get('last_name', '').strip()
    if not first_name and not last_name:
        return JsonResponse({'error': 'First or last name is required'}, status=400)

    person.first_name = first_name
    person.last_name  = last_name
    person.name = f"{first_name} {last_name}".strip()
    person.email = data.get('email', '').strip()
    person.phone_number = data.get('phone_number', '').strip()
    person.cell_phone_number = data.get('cell_phone_number', '').strip()
    person.title = data.get('title', '').strip()
    person.is_watson_forsberg = data.get('is_watson_forsberg', False)
    person.notes = data.get('notes', '')
    person.save()

    client_id = data.get('client_id') or None
    if client_id:
        person.company.set([client_id])
    else:
        person.company.clear()

    if any(c.name == 'Watson-Forsberg' for c in person.company.all()):
        person.is_watson_forsberg = True
        person.save(update_fields=['is_watson_forsberg'])

    from events.models import EventGuest
    today = datetime.date.today()
    has_pending_invite = EventGuest.objects.filter(
        person=person,
        invited=False,
        event__date__gte=today,
    ).exists()

    return JsonResponse({
        'id': person.id, 'name': person.name,
        'first_name': person.first_name, 'last_name': person.last_name,
        'email': person.email, 'phone_number': person.phone_number,
        'cell_phone_number': person.cell_phone_number,
        'companies': [{'id': c.id, 'name': c.name} for c in person.company.all()],
        'company': _company_str(person), 'title': person.title,
        'is_watson_forsberg': person.is_watson_forsberg,
        'notes': person.notes,
        'client_id': str(client_id) if client_id else '',
        'has_pending_invite': has_pending_invite,
    })


@login_required
@require_POST
def delete(request, person_id):
    person = get_object_or_404(Person, pk=person_id)
    person.delete()
    return JsonResponse({'ok': True})
