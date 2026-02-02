import io
import os
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

User = get_user_model()


class Tag(models.Model):
    name = models.CharField(
        'Название',
        max_length=32,
        unique=True
    )
    slug = models.SlugField(
        'Слаг',
        max_length=32,
        unique=True
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ('name',)

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(
        'Название',
        max_length=128
    )
    measurement_unit = models.CharField(
        'Единица измерения',
        max_length=64
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ('name',)
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'],
                name='unique_ingredient'
            )
        ]

    def __str__(self):
        return f'{self.name}, {self.measurement_unit}'


class Recipe(models.Model):
    name = models.CharField(
        'Название',
        max_length=256
    )
    text = models.TextField('Описание')
    image = models.ImageField(
        'Изображение',
        upload_to='recipes/images/'
    )
    cooking_time = models.PositiveIntegerField(
        'Время приготовления (в минутах)',
        validators=[MinValueValidator(1)]
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор'
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        verbose_name='Теги'
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientInRecipe',
        related_name='recipes',
        verbose_name='Ингредиенты'
    )
    created_at = models.DateTimeField(
        'Дата создания',
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        'Дата обновления',
        auto_now=True
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-created_at',)

    def __str__(self):
        return self.name
    
    @property
    def favorites_count(self):
        return self.favorites.count()


class IngredientInRecipe(models.Model):
    """
    Вспомогательный класс, для колличества 
    ингредиентов в рецепте.
    """
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='ingredient_amounts',
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='ingredient_amounts',
        verbose_name='Ингредиент'
    )
    amount = models.PositiveIntegerField(
        'Количество',
        validators=[MinValueValidator(1)]
    )

    class Meta:
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецептах'
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_ingredient_in_recipe'
            )
        ]

    def __str__(self):
        return (f'{self.ingredient.name} - '
        f'{self.amount} {self.ingredient.measurement_unit}'
        )


class Favorite(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Рецепт'
    )
    created_at = models.DateTimeField(
        'Дата добавления',
        auto_now_add=True
    )

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        ordering = ('-created_at',)
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_favorite'
            )
        ]

    def __str__(self):
        return f'{self.user} добавил в избранное {self.recipe}'


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shopping_cart',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='shopping_cart',
        verbose_name='Рецепт'
    )
    added_at = models.DateTimeField(
        'Дата добавления',
        auto_now_add=True
    )

    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'
        ordering = ('-added_at',)
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_shopping_cart'
            )
        ]

    def __str__(self):
        return f'{self.user} добавил в корзину {self.recipe}'


def upload_csv_file(instance, filename):
    return f'csv_uploads/ingredients/{filename}'


def csv_file_validator(value):
    filename, ext = os.path.splitext(value.name)
    if str(ext).lower() != '.csv':
        raise ValidationError(
            "Файл должен быть в формате .CSV"
            )
    return True


class CSVUpload(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    file = models.FileField(
        upload_to=upload_csv_file,
        validators=[csv_file_validator],
        verbose_name='CSV файл'
    )
    completed = models.BooleanField(
        default=False,
        verbose_name='Завершено'
    )

    class Meta:
        verbose_name = 'Загрузка CSV'
        verbose_name_plural = 'Загрузки CSV'

    def __str__(self):
        return f"Загрузка CSV {self.id}"


@receiver(post_save, sender=CSVUpload)
def csv_upload_post_save(sender, instance, created, **kwargs):
    if not instance.completed:
        csv_file = instance.file

        decoded_file = csv_file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)

        for line in io_string:
            line = line.strip()
            if not line:
                continue

            parts = line.split(',')

            if len(parts) >= 2:
                name = parts[0].strip()
                measurement_unit = parts[1].strip()

                Ingredient.objects.update_or_create(
                    name=name,
                    measurement_unit=measurement_unit,
                    defaults={
                        'name': name,
                        'measurement_unit': measurement_unit
                    }
                )

        instance.completed = True
        instance.save()
