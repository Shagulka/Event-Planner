from django.contrib import admin
from django.urls import include, path

from login.views import logout_view, my_events

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', include('login.urls')),
    path('events/', include('events.urls')),
    path('people/', include('people.urls')),
    path('clients/', include('clients.urls')),
    path('', include('events.urls')),
    path('logout/', logout_view, name='logout'),
    path('my-events/', my_events, name='my_events'),
    path(
        "microsoft_sso/", include(
            "django_microsoft_sso.urls",
            namespace="django_microsoft_sso"
        )
    ),
]
