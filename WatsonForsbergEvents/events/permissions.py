from functools import wraps
from django.http import JsonResponse


def require_edit_perm(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.has_perm('events.can_edit_events')):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper
