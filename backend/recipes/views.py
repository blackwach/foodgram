from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Favorite, Ingredient, Recipe, ShoppingCart, Tag
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    IngredientSerializer,
    RecipeCreateSerializer,
    RecipeListSerializer,
    RecipeMinifiedSerializer,
    TagSerializer,
)
from .utils import generate_shopping_cart_file


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def list(self, request, *args, **kwargs):
        """Возвращаем список ингредиентов"""
        queryset = Ingredient.objects.all()
        name = request.query_params.get('name', '')
        if name:
            queryset = queryset.filter(name__istartswith=name)
        queryset = queryset.order_by('name')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.select_related('author').prefetch_related('tags')
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['author']

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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def get_queryset(self):
        qs = self.queryset
        user = self.request.user

        is_favorited = self.request.query_params.get('is_favorited')
        if is_favorited == '1':
            if not user.is_authenticated:
                return qs.none()
            fav_ids = list(
                Favorite.objects.filter(user=user).values_list(
                    'recipe_id', flat=True
                )
            )
            qs = qs.filter(id__in=fav_ids) if fav_ids else qs.none()

        is_in_shopping_cart = self.request.query_params.get(
            'is_in_shopping_cart'
        )
        if is_in_shopping_cart == '1':
            if not user.is_authenticated:
                return qs.none()
            cart_ids = ShoppingCart.objects.filter(
                user=user
            ).values_list('recipe_id', flat=True)
            if cart_ids:
                qs = qs.filter(id__in=cart_ids)
            else:
                qs = qs.none()

        author_id = self.request.query_params.get('author')
        if author_id:
            try:
                author_id = int(author_id)
                qs = qs.filter(author_id=author_id)
            except (ValueError, TypeError):
                pass

        tags = self.request.query_params.getlist('tags')
        if tags:
            tag_objs = Tag.objects.filter(slug__in=tags)
            if tag_objs.exists():
                qs = qs.filter(tags__in=tag_objs).distinct()
            else:
                qs = qs.none()

        return qs

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == 'POST':
            if Favorite.objects.filter(
                user=request.user, recipe=recipe
            ).exists():
                return Response(
                    {'detail': 'Рецепт уже в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Favorite.objects.create(user=request.user, recipe=recipe)
            serializer = RecipeMinifiedSerializer(
                recipe, context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == 'DELETE':
            fav = Favorite.objects.filter(
                user=request.user,
                recipe=recipe
            )
            if not fav.exists():
                return Response(
                    {'detail': 'Рецепт не найден в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            fav.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='shopping_cart'
    )
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == 'POST':
            cart, created = ShoppingCart.objects.get_or_create(
                user=request.user,
                recipe=recipe
            )
            if not created:
                return Response(
                    {'message': 'Рецепт уже в списке покупок'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer = RecipeMinifiedSerializer(
                recipe, context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == 'DELETE':
            cart_item = ShoppingCart.objects.filter(
                user=request.user,
                recipe=recipe
            ).first()
            if not cart_item:
                return Response(
                    {'message': 'Рецепт отсутствует в списке покупок'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            cart_item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

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

        filename = f'shopping_cart_{request.user.id}.txt'
        response = HttpResponse(
            content, content_type='text/plain; charset=utf-8'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
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
