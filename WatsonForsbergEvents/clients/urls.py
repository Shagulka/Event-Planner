from django.urls import path
from . import views

urlpatterns = [
    path('', views.list_clients, name='clients_list'),
    path('directory/', views.index, name='clients_index'),
    path('create/', views.create_client, name='client_create'),
    path('<int:client_id>/detail/', views.client_detail, name='client_detail'),
    path('<int:client_id>/update/', views.update_client, name='client_update'),
    path('<int:client_id>/delete/', views.delete_client, name='client_delete'),
]
