from django.urls import path
from . import views

urlpatterns = [
    path('', views.list_clients, name='clients_list'),
    path('create/', views.create_client, name='client_create'),
]
