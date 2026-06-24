def editor_permission(request):
    can_edit = (
        request.user.is_authenticated
        and (request.user.is_superuser or request.user.has_perm('events.can_edit_events'))
    )
    return {'can_edit': can_edit}
