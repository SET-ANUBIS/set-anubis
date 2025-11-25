from SetAnubis.core.DataBase.domain.UFOTree import ExpressionTree

if __name__ == "__main__":
    tree = ExpressionTree([])
    tree.add_leaf("m", 2.0)
    tree.add_leaf("n", 3.0)
    tree.add_expression("p", "m*n + sin(m)")
    val_p = tree.evaluate(tree.nodes["p"], set())

    # 2) Créer un nœud avec des dépendances pas encore définies
    tree.add_expression("x", "y + z", create_missing=True)  # crée y et z comme feuilles vides
    tree.set_leaf_value("y", 1.5)
    tree.set_leaf_value("z", 2.0)
    val_x = tree.evaluate(tree.nodes["x"], set())

    # 3) Ajout en lot (même format que __init__)
    tree.add_nodes([
        {"name": "a", "value": 1},
        {"name": "b", "expression": "2*a + 1"},
    ], overwrite=True)
    
    tree.visualize().save("truc")
    
    graph = tree.visualize()

    graph.render("graph_test.png", format="png", view=False)