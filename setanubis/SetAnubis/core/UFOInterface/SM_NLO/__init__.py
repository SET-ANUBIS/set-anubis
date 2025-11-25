
import sys, os
# import UFOInterface.SM_NLO.particles
# import UFOInterface.SM_NLO.couplings
# import UFOInterface.SM_NLO.lorentz
# import UFOInterface.SM_NLO.parameters
# import UFOInterface.SM_NLO.vertices
# import UFOInterface.SM_NLO.coupling_orders
# import UFOInterface.SM_NLO.write_param_card
# import UFOInterface.SM_NLO.propagators

# import UFOInterface.SM_NLO.function_library
# import UFOInterface

# all_particles = UFOInterface.SM_NLO.particles.all_particles
# all_vertices = UFOInterface.SM_NLO.vertices.all_vertices
# all_couplings = UFOInterface.SM_NLO.couplings.all_couplings
# all_lorentz = UFOInterface.SM_NLO.lorentz.all_lorentz
# all_parameters = UFOInterface.SM_NLO.parameters.all_parameters
# all_orders = UFOInterface.SM_NLO.coupling_orders.all_orders
# all_functions = UFOInterface.SM_NLO.function_library.all_functions
# all_propagators = UFOInterface.SM_NLO.propagators.all_propagators

# try:
#    import UFOInterface.SM_NLO.decays
# except ImportError:
#    pass
# else:
#    all_decays = UFOInterface.SM_NLO.decays.all_decays

try:
   import UFOInterface.SM_NLO.form_factors
except ImportError:
   pass
else:
   all_form_factors = UFOInterface.SM_NLO.form_factors.all_form_factors

try:
   import CT_vertices
except ImportError:
   pass
else:
   all_CTvertices = CT_vertices.all_CTvertices


gauge = [0, 1]


__author__ = "N. Christensen, C. Duhr, B. Fuks"
__date__ = "15. 04. 2014"
__version__= "1.4.6"
