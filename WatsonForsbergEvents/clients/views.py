import datetime
import json
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from .models import Client


@login_required
def index(request):
    clients = Client.objects.order_by('name')
    return render(request, 'company_list.html', {'clients': clients})


@login_required
@require_GET
def list_clients(request):
    clients = Client.objects.order_by('name')
    return JsonResponse([{'id': c.id, 'name': c.name} for c in clients], safe=False)


@login_required
@require_GET
def client_detail(request, client_id):
    client = get_object_or_404(Client, pk=client_id)
    today = datetime.date.today()

    people = (
        client.person_set.all()
        .prefetch_related('company')
        .order_by('last_name', 'first_name')
    )

    events = (
        client.events.all()
        .order_by('date')
    )

    upcoming, past = [], []
    for ev in events:
        entry = {
            'id': ev.id,
            'name': ev.name,
            'date': ev.date.isoformat(),
            'location': ev.location,
        }
        (upcoming if ev.date >= today else past).append(entry)
    past.reverse()

    return JsonResponse({
        'id': client.id,
        'name': client.name,
        'email': client.email,
        'phone': client.phone,
        'notes': client.notes,
        'people': [
            {
                'id': p.id,
                'name': p.name,
                'title': p.title,
                'email': p.email,
                'phone_number': p.phone_number,
            }
            for p in people
        ],
        'upcoming_events': upcoming,
        'past_events': past,
    })


@login_required
@require_POST
def create_client(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    name = data.get('name', '').strip()
    if not name:
        return JsonResponse({'error': 'name is required'}, status=400)
    client = Client.objects.create(
        name=name,
        email=data.get('email', '').strip(),
        phone=data.get('phone', '').strip(),
        notes=data.get('notes', ''),
    )
    return JsonResponse({
        'id': client.id, 'name': client.name,
        'email': client.email, 'phone': client.phone, 'notes': client.notes,
    })


@login_required
@require_POST
def update_client(request, client_id):
    client = get_object_or_404(Client, pk=client_id)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    name = data.get('name', '').strip()
    if not name:
        return JsonResponse({'error': 'name is required'}, status=400)
    client.name = name
    client.email = data.get('email', '').strip()
    client.phone = data.get('phone', '').strip()
    client.notes = data.get('notes', '')
    client.save()
    return JsonResponse({
        'id': client.id, 'name': client.name,
        'email': client.email, 'phone': client.phone, 'notes': client.notes,
    })


@login_required
@require_POST
def delete_client(request, client_id):
    client = get_object_or_404(Client, pk=client_id)
    client.delete()
    return JsonResponse({'ok': True})
