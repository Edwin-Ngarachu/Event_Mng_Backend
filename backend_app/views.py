from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserRegisterSerializer, UserLoginSerializer, EventSerializer 
from django.contrib.auth import authenticate
from .models import Event, TicketType, Booking
from rest_framework.generics import RetrieveAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
import json
from django.conf import settings
import stripe
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.contrib.auth import get_user_model



stripe.api_key = settings.STRIPE_SECRET_KEY

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
    

# backend_app/views.py

class CreateCheckoutSessionView(APIView):
    def post(self, request):
        event_id = request.data.get("event_id")
        ticket_id = request.data.get("ticket_id")
        quantity = int(request.data.get("quantity", 1))

        try:
            ticket = TicketType.objects.get(id=ticket_id)
            event = Event.objects.get(id=event_id)
        except (TicketType.DoesNotExist, Event.DoesNotExist):
            return Response({"error": "Invalid ticket or event."}, status=400)

        # Stripe expects amount in cents (KES: multiply by 100)
        price = int(float(ticket.price) * 100)

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'kes',
                    'product_data': {
                        'name': f"{event.title} - {ticket.name}",
                    },
                    'unit_amount': price,
                },
                'quantity': quantity,
            }],
            mode='payment',
            success_url='http://localhost:5173/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='http://localhost:5173/cancel',
            metadata={
                'event_id': str(event_id),
                'ticket_id': str(ticket_id),
                'quantity': str(quantity),
            },
            customer_creation='always',  # Ensures customer details are collected
        )
        return Response({'sessionId': session.id})



class ConfirmPaymentView(APIView):
    def post(self, request):
        session_id = request.data.get("session_id")
        session = stripe.checkout.Session.retrieve(session_id)
        print("Session:", session)
        if session.payment_status == "paid":
            ticket_id = session.metadata.get("ticket_id")
            quantity = int(session.metadata.get("quantity", 1))
            print("Ticket ID:", ticket_id, "Quantity:", quantity)
            try:
                ticket = TicketType.objects.get(id=ticket_id)
                event = ticket.event
                print("Before:", ticket.quantity)
                ticket.quantity = max(ticket.quantity - quantity, 0)
                ticket.save()
                print("After:", ticket.quantity)
                # Get name and email from Stripe customer details
                customer_details = session.get("customer_details", {})
                name = customer_details.get("name", "") or "Guest"
                email = customer_details.get("email", "")
                ticket_number = f"{ticket.id}-{str(session_id)[-6:]}"  # Example ticket number

                # Try to get user by email (if not authenticated)
                User = get_user_model()
                user = User.objects.filter(email=email).first()

                # Create a booking if user exists and booking for this session doesn't exist
                if user:
                    Booking.objects.get_or_create(
                        user=user,
                        event=event,
                        ticket_type=ticket,
                        quantity=quantity,
                        ticket_number=ticket_number,
                    )


                return Response({
                    "success": True,
                    "name": name,
                    "ticket_name": ticket.name,
                    "quantity": quantity,
                    "ticket_number": ticket_number,
                    "event_title": event.title,
                    "price": float(ticket.price),
                    "date": event.date.isoformat() if hasattr(event, "date") else "",
                    "location": getattr(event, "location", ""),
                })
            except TicketType.DoesNotExist:
                print("Ticket not found")
                return Response({"error": "Ticket not found"}, status=400)
        print("Payment not verified")
        return Response({"error": "Payment not verified"}, status=400)
class MyBookingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        bookings = Booking.objects.filter(user=request.user).select_related('event', 'ticket_type')
        data = [
            {
                "event_title": b.event.title,
                "ticket_type": b.ticket_type.name,
                "quantity": b.quantity,
                "ticket_number": b.ticket_number,
                "booked_at": b.booked_at,
            }
            for b in bookings
        ]
        return Response(data)
    
class MyEventBookingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get events posted by this user
        events = Event.objects.filter(poster=request.user)
        # Get bookings for these events
        bookings = Booking.objects.filter(event__in=events).select_related('event', 'user', 'ticket_type')
        data = []
        for b in bookings:
            data.append({
                "event_title": b.event.title,
                "ticket_type": b.ticket_type.name,
                "quantity": b.quantity,
                "ticket_number": b.ticket_number,
                "booked_at": b.booked_at,
                "booker_name": b.user.get_full_name() or b.user.username,
                "booker_email": b.user.email,
                "price": float(b.ticket_type.price),
            })
        return Response(data)