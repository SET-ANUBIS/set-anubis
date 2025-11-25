from SetAnubis.core.DataBase.domain.UFOManager import UFOManager


if __name__ == "__main__":
    ufo_manager = UFOManager("Assets/UFO/UFO_HNL")
    
    print("get_all_particles :\n", ufo_manager.get_all_particles())
    print("\n-----------------------------------------------------------------------------------\n")
    
    print("get_new_particles :\n", ufo_manager.get_new_particles())
    print("\n-----------------------------------------------------------------------------------\n")
    
    print("get_sm_particles :\n", ufo_manager.get_sm_particles())
    print("\n-----------------------------------------------------------------------------------\n")
    
    print("get_params :\n", ufo_manager.get_params())
    print("\n-----------------------------------------------------------------------------------\n")
    
    print("get_decay :\n", ufo_manager.get_decays())
    print("\n-----------------------------------------------------------------------------------\n")
    
    print("get_decay_from_new_particles :\n", ufo_manager.get_decays_from_new_particles())
    print("\n-----------------------------------------------------------------------------------\n")
    
    print("get_decay_to_new_particles :\n", ufo_manager.get_decays_to_new_particles())
    print("\n-----------------------------------------------------------------------------------\n")
    
    print("get_sm_params :\n", ufo_manager.get_sm_params())
    print("\n-----------------------------------------------------------------------------------\n")
    
    print("get_param_with_sm_evaluation :\n", ufo_manager.get_param_with_sm_evaluation())
    print("\n-----------------------------------------------------------------------------------\n")
    