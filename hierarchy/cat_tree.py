class CategoryNode:
    def __init__(self, name):
        self.name = name
        self.children = []
        self.parent = None

    def add_child(self, child):
        child.parent = self
        self.children.append(child)

    def get_subtree_categories(self):
        result = [self.name]
        for child in self.children:
            result.extend(child.get_subtree_categories())
        return result