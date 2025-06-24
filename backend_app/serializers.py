# backend_app/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Event, TicketType
User = get_user_model()

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES, default='booker')

    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name', 'role']
        extra_kwargs = {
            'email': {'required': True}
        }

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            role=validated_data.get('role', 'booker')
        )
        return user

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()



class TicketTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketType
        fields = ['id', 'name', 'price', 'quantity']

class EventSerializer(serializers.ModelSerializer):
    tickets = TicketTypeSerializer(many=True, required=False)

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'description', 'date', 'poster', 'image', 'created_at',
            'location', 'duration', 'tickets'
        ]
        read_only_fields = ['poster', 'created_at']

    def create(self, validated_data):
      tickets_data = self.initial_data.get('tickets', [])
      if isinstance(tickets_data, str):
        import json
        tickets_data = json.loads(tickets_data)
      print("SERIALIZER tickets_data:", tickets_data)
      event = Event.objects.create(**validated_data)
      for ticket_data in tickets_data:
        print("Creating ticket:", ticket_data)
        TicketType.objects.create(event=event, **ticket_data)
      return event

    def update(self, instance, validated_data):
        tickets_data = self.initial_data.get('tickets', None)
        if isinstance(tickets_data, str):
            import json
            tickets_data = json.loads(tickets_data)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tickets_data is not None:
            instance.tickets.all().delete()
            for ticket_data in tickets_data:
                TicketType.objects.create(event=instance, **ticket_data)
        return instance

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        request = self.context.get('request')
        if instance.image and request:
            rep['image'] = request.build_absolute_uri(instance.image.url)
        elif instance.image:
            rep['image'] = instance.image.url
        return rep