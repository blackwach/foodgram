from collections import defaultdict


def generate_shopping_cart_file(shopping_cart):
    ing_dict = defaultdict(int)

    for item in shopping_cart:
        recipe = item.recipe
        for ing_amount in recipe.ingredient_amounts.all():
            ing = ing_amount.ingredient
            key = (ing.name, ing.measurement_unit)
            ing_dict[key] += ing_amount.amount

    lines = ['Список покупок:\r\n']
    
    for (name, unit), amount in sorted(ing_dict.items()):
        lines.append(f'{name} - {amount} {unit}\r\n')

    return ''.join(lines)
