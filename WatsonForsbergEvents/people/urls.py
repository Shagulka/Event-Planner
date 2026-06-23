from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='people_index'),
    path('data/', views.people_data, name='people_data'),
    path('search/', views.search, name='people_search'),
    path('<int:event_id>/recommended/', views.recommended_guests, name='people_recommended_guests'),
    path('create/', views.create, name='people_create'),
    path('<int:person_id>/detail/', views.detail, name='people_detail'),
    path('<int:person_id>/update/', views.update, name='people_update'),
    path('<int:person_id>/delete/', views.delete, name='people_delete'),
]
