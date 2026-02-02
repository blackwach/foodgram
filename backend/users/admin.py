from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Subscription, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'recipes_count', 'id')
    list_filter = ('email',)
    search_fields = ('username', 'email', 'first_name', 'last_name')
    readonly_fields = ('date_joined', 'last_login')

    def recipes_count(self, obj):
        return obj.recipes.count()
    recipes_count.short_description = 'Рецептов'


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'author', 'id')
    list_filter = ('user',)
    search_fields = ('user__username', 'author__username')
    raw_id_fields = ('user', 'author')
