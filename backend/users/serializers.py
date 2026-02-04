from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from djoser.serializers import TokenCreateSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from .models import Subscription, User


class UserSerializer(serializers.ModelSerializer):

    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar'
        )
        read_only_fields = ('id',)

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return Subscription.objects.filter(
            user=request.user,
            author=obj
        ).exists()

    def get_avatar(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None


class CustomUserCreateSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'password'
        )
        read_only_fields = ('id',)

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = super().create(validated_data)
        user.set_password(password)
        user.save()
        return user


class SetPasswordSerializer(serializers.Serializer):

    new_password = serializers.CharField(
        required=True,
        validators=[validate_password]
    )
    current_password = serializers.CharField(required=True)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Неправильный текущий пароль')
        return value

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class SetAvatarSerializer(serializers.ModelSerializer):

    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ('avatar',)

    def validate(self, attrs):
        if 'avatar' not in self.initial_data:
            raise serializers.ValidationError({
                'avatar': 'Это поле обязательно.'
            })
        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.avatar:
            request = self.context.get('request')
            if request:
                representation['avatar'] = request.build_absolute_uri(
                    instance.avatar.url
                )
            else:
                representation['avatar'] = instance.avatar.url
        else:
            representation['avatar'] = None

        return representation


class UserWithRecipesSerializer(UserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ('recipes', 'recipes_count')

    def get_recipes(self, obj):
        from recipes.serializers import RecipeMinifiedSerializer
        request = self.context.get('request')
        limit = request.query_params.get('recipes_limit') if request else None
        recipes = obj.recipes.all()
        if limit:
            try:
                recipes = recipes[:int(limit)]
            except ValueError:
                pass
        return RecipeMinifiedSerializer(
            recipes,
            many=True,
            context=self.context
        ).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class CustomTokenCreateSerializer(TokenCreateSerializer):

    password = serializers.CharField(
        required=False, style={'input_type': 'password'}
    )
    email = serializers.EmailField(required=False)

    @property
    def user(self):

        if (hasattr(self, 'validated_data') and self.validated_data
                and 'user' in self.validated_data):
            return self.validated_data['user']

        if hasattr(self, '_user'):
            return self._user
        try:
            return super().user
        except (AttributeError, KeyError):
            return None

    @user.setter
    def user(self, value):
        self._user = value

    def validate_email(self, value):
        if not value:
            raise serializers.ValidationError('Необходимо указать почту.')
        return value

    def validate_password(self, value):
        if not value:
            raise serializers.ValidationError('Необходимо указать пароль.')
        return value

    def validate(self, attrs):
        email = attrs['email']
        password = attrs['password']

        user = authenticate(
            request=self.context.get('request'),
            username=email,
            password=password,
        )

        if not user:
            raise serializers.ValidationError(
                'Невозможно войти с предоставленными учетными данными.'
            )

        if not user.is_active:
            raise serializers.ValidationError(
                'Учетная запись пользователя отключена.'
            )

        attrs["user"] = user
        self._user = user
        return attrs
