# backend_app/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Event
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

class EventSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'description', 'date', 'poster', 'image', 'created_at',
            'location', 'duration'  
        ]
        read_only_fields = ['poster', 'created_at']

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        request = self.context.get('request')
        if instance.image and request:
            rep['image'] = request.build_absolute_uri(instance.image.url)
        elif instance.image:
            rep['image'] = instance.image.url
        return rep