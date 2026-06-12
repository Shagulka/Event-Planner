import datetime
import json
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from .models import Client


@login_required
def index(request):
    clients = Client.objects.select_related('contact_person').order_by('name')
    return render(request, 'company_list.html', {
        'clients': clients,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
    })


@login_required
@require_GET
def list_clients(request):
    q = request.GET.get('q', '').strip()
    clients = Client.objects.order_by('name')
    if q:
        clients = clients.filter(name__icontains=q)[:50]
    return JsonResponse([{'id': c.id, 'name': c.name} for c in clients], safe=False)


def _contact_person_data(client):
    cp = client.contact_person
    if not cp:
        return None
    return {
        'id': cp.id,
        'name': cp.name,
        'title': cp.title,
        'email': cp.email,
        'cell_phone_number': cp.cell_phone_number,
        'phone_number': cp.phone_number,
    }


@login_required
@require_GET
def client_detail(request, client_id):
    client = get_object_or_404(Client.objects.select_related('contact_person'), pk=client_id)
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
        'address': client.address,
        'market_area': client.market_area,
        'website': client.website,
        'notes': client.notes,
        'contact_person': _contact_person_data(client),
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
    contact_person_id = data.get('contact_person_id') or None
    client = Client.objects.create(
        name=name,
        email=data.get('email', '').strip(),
        phone=data.get('phone', '').strip(),
        address=data.get('address', '').strip(),
        market_area=data.get('market_area', '').strip(),
        website=data.get('website', '').strip(),
        notes=data.get('notes', ''),
        contact_person_id=contact_person_id,
    )
    client.refresh_from_db()
    return JsonResponse({
        'id': client.id, 'name': client.name,
        'email': client.email, 'phone': client.phone,
        'address': client.address, 'market_area': client.market_area,
        'notes': client.notes,
        'contact_person': _contact_person_data(client),
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
    client.address = data.get('address', '').strip()
    client.market_area = data.get('market_area', '').strip()
    client.website = data.get('website', '').strip()
    client.notes = data.get('notes', '')
    client.contact_person_id = data.get('contact_person_id') or None
    client.save()
    client.refresh_from_db()
    return JsonResponse({
        'id': client.id, 'name': client.name,
        'email': client.email, 'phone': client.phone,
        'address': client.address, 'market_area': client.market_area,
        'notes': client.notes,
        'contact_person': _contact_person_data(client),
    })


@login_required
@require_POST
def delete_client(request, client_id):
    client = get_object_or_404(Client, pk=client_id)
    client.delete()
    return JsonResponse({'ok': True})
