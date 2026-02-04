from django.apps import apps
from django.db.models import Sum
from import_export import resources
from import_export.fields import Field

from .models import Ingredient


class IngredientImportCSV(resources.ModelResource):

    name = Field(attribute='name', column_name='name')
    measurement_unit = Field(
        attribute='measurement_unit',
        column_name='measurement_unit')

    class Meta:
        model = Ingredient
        fields = ('name', 'measurement_unit')
        import_id_fields = ('name', 'measurement_unit')
        skip_unchanged = False
        report_skipped = False

    def import_data(self, dataset, dry_run=False,
                    raise_errors=False, use_transactions=None, **kwargs):
        if not dataset.headers or len(dataset.headers) == 0:
            dataset.headers = ['name', 'measurement_unit']

        elif len(dataset.headers) == 2:
            first_header = str(
                dataset.headers[0]).strip() if dataset.headers[0] else ''
            if first_header and any(
                    '\u0400' <= char <= '\u04FF' for char in first_header):
                first_row_data = [dataset.headers[0], dataset.headers[1]]
                dataset.headers = ['name', 'measurement_unit']
                dataset.insert(0, first_row_data)

        return super().import_data(
            dataset, dry_run,
            raise_errors,
            use_transactions,
            **kwargs
            )


def generate_shopping_cart_file(shopping_cart):
    IngredientInRecipe = apps.get_model('recipes', 'IngredientInRecipe')

    recipe_ids = [item.recipe_id for item in shopping_cart]

    ingredients = (
        IngredientInRecipe.objects
        .filter(recipe_id__in=recipe_ids)
        .values('ingredient__name', 'ingredient__measurement_unit')
        .annotate(total_amount=Sum('amount'))
        .order_by('ingredient__name', 'ingredient__measurement_unit')
    )

    lines = ['Список покупок:\r\n']

    for ing in ingredients:
        name = ing['ingredient__name']
        unit = ing['ingredient__measurement_unit']
        amount = ing['total_amount']
        lines.append(f'{name} - {amount} {unit}\r\n')

    return ''.join(lines)
