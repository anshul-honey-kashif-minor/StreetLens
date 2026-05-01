from .cat_tree import CategoryNode
from database.models import Shop

def build_category_tree():
    nodes = {}

    def create(name):
        node = CategoryNode(name)
        nodes[name] = node
        return node

    # Root
    restaurant = create("Restaurant")

    fast_food = create("Fast Food")
    bhojnalaya = create("Bhojanalaya")
    cafe = create("Cafe")

    restaurant.add_child(fast_food)
    restaurant.add_child(bhojnalaya)
    restaurant.add_child(cafe)

    pizza = create("Pizza Shop")
    burger = create("Burger Joint")

    fast_food.add_child(pizza)
    fast_food.add_child(burger)

    return nodes 


def search_with_fallback(node, session):
    current = node

    while current:
        categories = current.get_subtree_categories()
        shops = get_shops_by_categories(session, categories)

        if shops:
            return shops

        current = current.parent

    return []

def get_shops_by_categories(session, categories):
    return session.query(Shop).filter(Shop.category.in_(categories)).all()