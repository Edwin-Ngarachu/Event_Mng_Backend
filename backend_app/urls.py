# backend_app/urls.py
from django.urls import path
from .views import RegisterView, LoginView, EventCreateView, MyEventsView, EventDetailView,  EventListView, EventDeleteView, EventUpdateView

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('events/create/', EventCreateView.as_view(), name='event-create'),
    path('events/mine/', MyEventsView.as_view(), name='my-events'),
     path('events/<int:id>/', EventDetailView.as_view(), name='event-detail'),
     path('events/', EventListView.as_view(), name='event-list'),
     path('events/<int:id>/delete/', EventDeleteView.as_view(), name='event-delete'),
     path('events/<int:id>/edit/', EventUpdateView.as_view(), name='event-edit'),
]