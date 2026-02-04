from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .filters import RecipeFilter
from .models import Favorite, Ingredient, Recipe, ShoppingCart, Tag
from .permissions import IsAuthorOrReadOnly
from .serializers import (IngredientSerializer, RecipeCreateSerializer,
                          RecipeListSerializer, RecipeMinifiedSerializer,
                          TagSerializer)
from .utils import generate_shopping_cart_file


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AllowAny]
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all().order_by('name')
    serializer_class = IngredientSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    filter_backends = [SearchFilter]
    search_fields = ['^name']


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.select_related('author').prefetch_related('tags')
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RecipeCreateSerializer
        return RecipeListSerializer

    def get_permissions(self):
        if self.action in ['create', 'favorite', 'shopping_cart']:
            return [IsAuthenticated()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthorOrReadOnly()]
        return [AllowAny()]

    @staticmethod
    def _add_relation(request, pk, model, filter_kwargs, response_serializer,
                      response_object, error_message):
        obj = get_object_or_404(response_object, pk=pk)

        if model.objects.filter(**filter_kwargs).exists():
            return Response(
                {'detail': error_message},
                status=status.HTTP_400_BAD_REQUEST
            )

        model.objects.create(**filter_kwargs)
        serializer = response_serializer(obj, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @staticmethod
    def _remove_relation(request, pk, model, filter_kwargs, error_message):
        relation = model.objects.filter(**filter_kwargs)

        if not relation.exists():
            return Response(
                {'detail': error_message},
                status=status.HTTP_400_BAD_REQUEST
            )

        relation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated]
    )
    @transaction.atomic
    def favorite(self, request, pk):
        return self._add_relation(
            request=request,
            pk=pk,
            model=Favorite,
            filter_kwargs={'user': request.user, 'recipe_id': pk},
            response_serializer=RecipeMinifiedSerializer,
            response_object=Recipe,
            error_message='Рецепт уже в избранном'
        )

    @favorite.mapping.delete
    @transaction.atomic
    def delete_favorite(self, request, pk):
        return self._remove_relation(
            request=request,
            pk=pk,
            model=Favorite,
            filter_kwargs={'user': request.user, 'recipe_id': pk},
            error_message='Рецепт не найден в избранном'
        )

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated],
        url_path='shopping_cart'
    )
    @transaction.atomic
    def shopping_cart(self, request, pk):
        return self._add_relation(
            request=request,
            pk=pk,
            model=ShoppingCart,
            filter_kwargs={'user': request.user, 'recipe_id': pk},
            response_serializer=RecipeMinifiedSerializer,
            response_object=Recipe,
            error_message='Рецепт уже в списке покупок'
        )

    @shopping_cart.mapping.delete
    @transaction.atomic
    def delete_shopping_cart(self, request, pk):
        return self._remove_relation(
            request=request,
            pk=pk,
            model=ShoppingCart,
            filter_kwargs={'user': request.user, 'recipe_id': pk},
            error_message='Рецепт отсутствует в списке покупок'
        )

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
        url_path='download_shopping_cart'
    )
    def download_shopping_cart(self, request):
        cart = ShoppingCart.objects.filter(
            user=request.user
        ).select_related('recipe').prefetch_related(
            'recipe__ingredient_amounts__ingredient'
        )

        if not cart.exists():
            return Response(
                {'detail': 'Список покупок пуст'},
                status=status.HTTP_400_BAD_REQUEST
            )

        content = generate_shopping_cart_file(cart)

        filename = 'shopping_cart_{}.txt'.format(request.user.id)
        content_type = 'text/plain'
        response = HttpResponse(content, content_type=content_type)
        response.charset = 'utf-8'
        response['Content-Disposition'] = (
            'attachment' + '; ' + 'filename="{}"'.format(filename)
        )
        return response

    @action(
        detail=True,
        methods=['get'],
        url_path='get-link'
    )
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        short_link = request.build_absolute_uri(f'/recipes/{recipe.id}')
        return Response({'short-link': short_link})
