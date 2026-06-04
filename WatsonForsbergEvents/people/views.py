import json
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from .models import Person


@login_required
def index(request):
    people = Person.objects.order_by('last_name', 'first_name')
    return render(request, "people_list.html", {"people": people})


@login_required
@require_GET
def search(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 1:
        return JsonResponse([], safe=False)
    people = (
        Person.objects
        .filter(name__icontains=q)
        .order_by('last_name', 'first_name')[:20]
    )
    return JsonResponse([
        {'id': p.id, 'name': p.name, 'company': p.company, 'title': p.title, 'email': p.email}
        for p in people
    ], safe=False)



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
        company=data.get('company', ''),
        title=data.get('title', ''),
        is_watson_forsberg=data.get('is_watson_forsberg', False),
    )
    if person.is_watson_forsberg and person.company == '':
        person.company = "Watson-Forsberg"
        person.save()
    if (person.company.lower() == 'watson-forsberg' or person.company.lower() == 'watson forsberg') and not person.is_watson_forsberg:
        person.is_watson_forsberg = True
        person.company = "Watson-Forsberg"
        person.save()
    return JsonResponse({
        'id': person.id, 'name': person.name,
        'first_name': person.first_name, 'last_name': person.last_name,
        'email': person.email, 'phone_number': person.phone_number,
        'company': person.company, 'title': person.title,
        'is_watson_forsberg': person.is_watson_forsberg,
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
    person.company = data.get('company', '').strip()
    person.title = data.get('title', '').strip()
    person.is_watson_forsberg = data.get('is_watson_forsberg', False)
    person.save()
    return JsonResponse({
        'id': person.id, 'name': person.name,
        'first_name': person.first_name, 'last_name': person.last_name,
        'email': person.email, 'phone_number': person.phone_number,
        'company': person.company, 'title': person.title,
        'is_watson_forsberg': person.is_watson_forsberg,
    })


@login_required
@require_POST
def delete(request, person_id):
    person = get_object_or_404(Person, pk=person_id)
    person.delete()
    return JsonResponse({'ok': True})
