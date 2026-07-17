from SetAnubis.core.DataBase.domain.UFOTree import ExpressionTree

if __name__ == "__main__":
    tree = ExpressionTree([])
    tree.add_leaf("m", 2.0)
    tree.add_leaf("n", 3.0)
    tree.add_expression("p", "m*n + sin(m)")
    val_p = tree.evaluate(tree.nodes["p"], set())

    # 2) Create a node whose dependencies are not defined yet
    tree.add_expression("x", "y + z", create_missing=True)  # create y and z as empty leaf nodes
    tree.set_leaf_value("y", 1.5)
    tree.set_leaf_value("z", 2.0)
    val_x = tree.evaluate(tree.nodes["x"], set())

    # 3) Add nodes in bulk using the constructor input format
    tree.add_nodes([
        {"name": "a", "value": 1},
        {"name": "b", "expression": "2*a + 1"},
    ], overwrite=True)
    
    tree.visualize().save("truc")
    
    graph = tree.visualize()

    graph.render("graph_test.png", format="png", view=False)