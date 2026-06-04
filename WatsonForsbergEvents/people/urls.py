from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='people_index'),
    path('search/', views.search, name='people_search'),
    path('create/', views.create, name='people_create'),
    path('<int:person_id>/update/', views.update, name='people_update'),
    path('<int:person_id>/delete/', views.delete, name='people_delete'),
]
