from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="events_index"),
    path("create/", views.event_create, name="event_create"),
    path("<int:event_id>/update/", views.event_update, name="event_update"),
    path("<int:event_id>/guests/", views.event_guests, name="event_guests"),
    path("<int:event_id>/guests/add/", views.event_guest_add, name="event_guest_add"),
    path("<int:event_id>/guests/<int:person_id>/remove/", views.event_guest_remove, name="event_guest_remove"),
    path("<int:event_id>/guests/<int:person_id>/update/", views.event_guest_update, name="event_guest_update"),
]
