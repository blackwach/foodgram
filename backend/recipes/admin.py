from django.contrib import admin

from .models import (
    CSVUpload,
    Favorite,
    Ingredient,
    IngredientInRecipe,
    Recipe,
    ShoppingCart,
    Tag,
)


@admin.register(CSVUpload)
class CSVUploadAdmin(admin.ModelAdmin):
    """Импорты в БД для ингридиентов из CSV."""
    list_display = ['id', 'user', 'file', 'completed']
    list_filter = ['completed']

    def save_model(self, request, obj, form, change):
        if not change:
            obj.user = request.user
        super().save_model(request, obj, form, change)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'id')
    search_fields = ('name', 'slug')
    list_per_page = 50


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit', 'recipes_count', 'id')
    search_fields = ('name',)
    list_filter = ('measurement_unit',)
    ordering = ('name',)

    def recipes_count(self, obj):
        return obj.recipes.count()
    recipes_count.short_description = 'Рецептов'


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
    list_per_page = 25
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
    list_per_page = 30


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', 'id')
    search_fields = ('user__username', 'recipe__name')
    raw_id_fields = ('user', 'recipe')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'recipe')
