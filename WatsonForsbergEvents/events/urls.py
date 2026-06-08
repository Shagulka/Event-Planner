from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="events_index"),
    path("create/", views.event_create, name="event_create"),
    path("metrics/", views.metrics, name="events_metrics"),
    path("metrics/data/", views.metrics_data, name="events_metrics_data"),
    path("<int:event_id>/update/", views.event_update, name="event_update"),
    path("<int:event_id>/registration/", views.event_registration, name="event_registration"),
    path("<int:event_id>/delete/", views.event_delete, name="event_delete"),
    path("<int:event_id>/guests/", views.event_guests, name="event_guests"),
    path("<int:event_id>/guests/add/", views.event_guest_add, name="event_guest_add"),
    path("<int:event_id>/guests/<int:person_id>/remove/", views.event_guest_remove, name="event_guest_remove"),
    path("<int:event_id>/guests/<int:person_id>/update/", views.event_guest_update, name="event_guest_update"),
]
