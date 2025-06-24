from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserRegisterSerializer, UserLoginSerializer, EventSerializer 
from django.contrib.auth import authenticate
from .models import Event
from rest_framework.generics import RetrieveAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
import json


class RegisterView(APIView):
    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            user_data = UserRegisterSerializer(user).data  # Ensure fresh data
            return Response({
                'user': user_data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = authenticate(
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password']
            )
            if user:
                refresh = RefreshToken.for_user(user)
                user_data = UserRegisterSerializer(user).data
                return Response({
                    'user': user_data,
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                })
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
class EventCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        if request.user.role != 'poster':
            return Response({'error': 'Only posters can create events.'}, status=status.HTTP_403_FORBIDDEN)
        data = request.data.copy()
        tickets_json = data.get('tickets')
        if tickets_json:
            try:
                data['tickets'] = json.loads(tickets_json)
            except Exception:
                data['tickets'] = []
        print("TICKETS FIELD:", data.get('tickets'))  # <-- Add this line here
        serializer = EventSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save(poster=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class MyEventsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'poster':
            return Response({'error': 'Only posters can view their events.'}, status=403)
        events = Event.objects.filter(poster=request.user)
        serializer = EventSerializer(events, many=True, context={'request': request})
        return Response(serializer.data)

class EventDetailView(RetrieveAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    lookup_field = 'id'
class EventListView(ListAPIView):
    queryset = Event.objects.all().order_by('-created_at')
    serializer_class = EventSerializer
class EventDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, id):
        try:
            event = Event.objects.get(id=id)
        except Event.DoesNotExist:
            return Response({'error': 'Event not found.'}, status=status.HTTP_404_NOT_FOUND)
        if event.poster != request.user:
            return Response({'error': 'You can only delete your own events.'}, status=status.HTTP_403_FORBIDDEN)
        event.delete()
        return Response({'message': 'Event deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)





class EventUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def put(self, request, id):
        try:
            event = Event.objects.get(id=id)
        except Event.DoesNotExist:
            return Response({'error': 'Event not found.'}, status=status.HTTP_404_NOT_FOUND)
        if event.poster != request.user:
            return Response({'error': 'You can only edit your own events.'}, status=status.HTTP_403_FORBIDDEN)
        data = request.data.copy()
        tickets_json = data.get('tickets')
        if tickets_json:
            try:
                data['tickets'] = json.loads(tickets_json)
            except Exception:
                data['tickets'] = []
        serializer = EventSerializer(event, data=data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)