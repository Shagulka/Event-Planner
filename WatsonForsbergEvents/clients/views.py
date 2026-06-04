import json
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from .models import Client


@login_required
@require_GET
def list_clients(request):
    clients = Client.objects.order_by('name')
    return JsonResponse([{'id': c.id, 'name': c.name} for c in clients], safe=False)


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
    client = Client.objects.create(name=name, notes=data.get('notes', ''))
    return JsonResponse({'id': client.id, 'name': client.name})
