"""
All the interfaces for each parts (ModelCore, MadGraph, Selection, Geometry, etc.) will be situated in the adapters.input part.
In order to get a simpler importation, every interfaces can be found in the NeoSetAnubis.core.interfaces part.

The Enums will also be available in the NeoSetAnubis.core.enums part.
"""
from SetAnubis.core.interfaces import SetAnubisInterface

if __name__ == "__main__":
    
    """
    NeoSetAnubisInterface is the main interface of the neo-set-anubis pipeline. Its contain all the informations on a Given model.
    The only paramters it need is the path to the UFO.
    
    Inside the ModelCore (core of the NeoSetAnubisInterface) parameters will be stored as a tree, based on the UFO parameter's calculations. One can then modify a leaf parameters 
    and all the dependant parameters will be updated.
    
    Multiples API calls are available to check the parsing of the UFO, like the get_all_parameters() and get_all_particles() to check if all the parameters and the particles have the right attributes (charge, spin, etc.).
    """
    man = SetAnubisInterface("db/HNL/UFO_HNL")
    
    """
    The get_all_parameters API return a dictionnary with all the parameters and their attributes : value, lhablock (if given) and lhacode (if given)
    """
    print(man.get_all_parameters())
    
    print("-----------------------------------------------------------------")
    """
    The get_all_particles API return a dictionnary with all the particles and their attributes : name, pdg_code, charge, color, spin and mass.
    """
    print(man.get_all_particles())
    
    """
    The get_particle_mass API need a pdg_code as input and return its mass (GeV) as a float.
    """
    print(man.get_particle_mass(23))
    
    """
    The get_leaf_parameters API returns all the leaf parameters of the parameter's tree. Useful to know which parameters can be modify by the set_leaf_param.
    """
    print(man.get_leaf_parameters())
    
    print("Setting mass of the Z to 100 GeV")
    man.set_leaf_param("MZ", 100)
    
    """
    Checking if the mass of the Z as indeed changed.
    """
    print(man.get_particle_mass(23)) 
    
    """
    The get_parameter_expr API allows to get the expression of a given parameters (expression that's used in the core to calculate the parameter value). Here the expression for the MW should be : sqrt(MZ**2/2. + sqrt(MZ**4/4. - (aEW*pi*MZ**2)/(Gf*sqrt(2))))
    """
    print(man.get_parameter_expr("MW"))
    
    """
    The get_particle_info API need a pdg_code as an input and return all the informations about a given particle (name, pdg_code, antiname, charge, color, spin, mass).
    """
    print(man.get_particle_info(25))