import django_filters

from .models import Favorite, Recipe, ShoppingCart, Tag


class RecipeFilter(django_filters.FilterSet):
    tags = django_filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
        conjoined=False,
    )
    is_favorited = django_filters.BooleanFilter(
        method='filter_is_favorited',
        label='В избранном'
    )
    is_in_shopping_cart = django_filters.BooleanFilter(
        method='filter_is_in_shopping_cart',
        label='В корзине'
    )
    author = django_filters.NumberFilter(
        field_name='author_id',
        lookup_expr='exact'
    )

    class Meta:
        model = Recipe
        fields = ['tags', 'author']

    def filter_is_favorited(self, queryset, name, value):
        if not value or value == 0:
            return queryset

        request = self.request
        if not request or not request.user.is_authenticated:
            return queryset.none()

        fav_ids = Favorite.objects.filter(
            user=request.user
        ).values_list('recipe_id', flat=True)

        return queryset.filter(id__in=fav_ids) if fav_ids else queryset.none()

    def filter_is_in_shopping_cart(self, queryset, name, value):
        if not value or value == 0:
            return queryset

        request = self.request
        if not request or not request.user.is_authenticated:
            return queryset.none()

        cart_ids = ShoppingCart.objects.filter(
            user=request.user
        ).values_list('recipe_id', flat=True)

        return queryset.filter(id__in=cart_ids) if cart_ids else queryset.none()
