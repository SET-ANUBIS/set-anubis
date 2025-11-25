from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface

import os

UFO_HNL_DIR = os.path.abspath(os.path.join(__file__, "..", "..", "..", "..", "..", "..", "Assets", "UFO", "UFO_HNL"))

if __name__ == "__main__":
    params = [
        {"name": "alpha_em", "value": 1/137.0},
        {"name": "mZ", "value": "alpha_em"},
        {"name": "mH", "value": 125.0},
        {"name": "my_expr", "expression": "mH * alpha_em", "value" : "mH * alpha_em"},
        # ...
    ]
    # model_manager = SetAnubisManager("db/HNL/UFO_HNL")
    model_interface = SetAnubisInterface(UFO_HNL_DIR)
    print("--------------------------------------------------------------------------------------------------------------------------------------")
    print("all parameters are : ", model_interface.get_all_parameters())
    print("--------------------------------------------------------------------------------------------------------------------------------------")
    model_interface.set_leaf_param("VeN1", 0.1)
    
    print("all parameters after setting VeN1 to 126 are : ", model_interface.get_all_parameters())
    print("--------------------------------------------------------------------------------------------------------------------------------------")
    print("leaf parameters are : ", model_interface.get_leaf_parameters())
    print("--------------------------------------------------------------------------------------------------------------------------------------")
    print(model_interface.get_all_particles())
    print("--------------------------------------------------------------------------------------------------------------------------------------")
    