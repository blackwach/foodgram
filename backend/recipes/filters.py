import django_filters

from .models import Favorite, Recipe, ShoppingCart, Tag


class RecipeFilter(django_filters.FilterSet):
    tags = django_filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
        conjoined=False,
    )
    author = django_filters.NumberFilter(
        field_name='author_id',
        lookup_expr='exact'
    )
    is_favorited = django_filters.NumberFilter(
        method='filter_is_favorited'
    )
    is_in_shopping_cart = django_filters.NumberFilter(
        method='filter_is_in_shopping_cart'
    )

    def filter_is_favorited(self, queryset, name, value):
        if value and hasattr(self, 'request') and self.request.user.is_authenticated:
            favorites = Favorite.objects.filter(user=self.request.user).values_list('recipe_id', flat=True)
            return queryset.filter(id__in=favorites)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        if value and hasattr(self, 'request') and self.request.user.is_authenticated:
            cart = ShoppingCart.objects.filter(user=self.request.user).values_list('recipe_id', flat=True)
            return queryset.filter(id__in=cart)
        return queryset

    class Meta:
        model = Recipe
        fields = ['tags', 'author']
