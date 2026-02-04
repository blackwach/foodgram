from constants import (LIST_PER_PAGE_FAVORITE, LIST_PER_PAGE_RECIPE,
                       LIST_PER_PAGE_TAG)
from django.contrib import admin
from import_export.admin import ImportMixin

from .models import (Favorite, Ingredient, IngredientInRecipe, Recipe,
                     ShoppingCart, Tag)
from .utils import IngredientImportCSV


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'id')
    search_fields = ('name', 'slug')
    list_per_page = LIST_PER_PAGE_TAG


@admin.register(Ingredient)
class IngredientAdmin(ImportMixin, admin.ModelAdmin):
    resource_class = IngredientImportCSV
    list_display = ('name', 'measurement_unit', 'id')
    search_fields = ('name',)
    list_filter = ('measurement_unit',)
    ordering = ('name',)


class IngredientInRecipeInline(admin.TabularInline):
    model = IngredientInRecipe
    extra = 0
    fields = ('ingredient', 'amount')
    autocomplete_fields = ('ingredient',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'author', 'cooking_time', 'ingredients_count', 'created_at'
    )
    list_filter = ('tags', 'created_at', 'author')
    search_fields = ('name', 'author__username', 'text')
    inlines = [IngredientInRecipeInline]
    filter_horizontal = ('tags',)
    readonly_fields = ('created_at', 'updated_at', 'favorites_count_display')
    list_per_page = LIST_PER_PAGE_RECIPE
    actions = ['duplicate_recipe']

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'author', 'text', 'image', 'cooking_time')
        }),
        ('Классификация', {
            'fields': ('tags',)
        }),
        ('Статистика', {
            'fields': ('favorites_count_display',)
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def ingredients_count(self, obj):
        cnt = obj.ingredient_amounts.count()
        return cnt
    ingredients_count.short_description = 'Ингредиентов'

    def favorites_count_display(self, obj):
        return obj.favorites_count

    favorites_count_display.short_description = 'Добавлений в избранное'

    def duplicate_recipe(self, request, queryset):
        count = 0
        for recipe in queryset:
            recipe.pk = None
            recipe.name = f'{recipe.name} (копия)'
            recipe.save()
            count += 1
        self.message_user(request, f'Скопировано рецептов: {count}')
    duplicate_recipe.short_description = 'Дублировать выбранные рецепты'


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', 'id')
    list_filter = ('user',)
    search_fields = ('user__username', 'recipe__name')
    raw_id_fields = ('user', 'recipe')
    list_per_page = LIST_PER_PAGE_FAVORITE


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', 'id')
    search_fields = ('user__username', 'recipe__name')
    raw_id_fields = ('user', 'recipe')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'recipe')
