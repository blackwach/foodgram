import django_filters

from .models import Recipe, Tag


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

    class Meta:
        model = Recipe
        fields = ['tags', 'author']
