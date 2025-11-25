import json
import os, sys
from particle import PDGID
from particle import Particle

sys.path.append(os.getcwd())

def is_int(string : str) -> bool:
    """
    Check if a given string can be converted to an integer.

    :param string: The input string to check.
    :return: True if the string can be converted to an integer, False otherwise.
    """
    try:
        int(string)
        return True
    except ValueError:
        return False
    
class SimulationParameters:
    """
    Singleton class to handle simulation parameters (particles and SM informations), including loading and saving particle properties.
    """
    _instance = None

    def __new__(cls, db_file='db/db.json'):
        """
        Ensure a single instance of the SimulationParameters class (Singleton pattern).

        :param db_file: Path to the JSON database file containing simulation parameters.
        """
        if cls._instance is None:
            cls._instance = super(SimulationParameters, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_file='db/db.json'):
        """
        Initialize the SimulationParameters instance.

        :param db_file: Path to the JSON database file containing simulation parameters.
        """
        if self._initialized:
            return
        self._initialized = True
        self.params = {}
        self.constants = {"pi" : 3.141592654, "G_F" : 1.16637e-5, "sw2" : 0.233610, "c" : 299792458.0, "eV" : 1.602176634e-19, "e" : 1.602176634e-19, "kg_to_GeV" : 5.609588603e+26, "hev" : 6.58211928*pow(10.,-16)}
        self.CKM_matrix = [
            [ 0.97373, 0.22500, 0.00369 ],
            [ 0.22486, 0.97349, 0.04182 ],
            [ 0.00857, 0.04110, 0.999118 ]
        ]
        
        self.leplist = [11,13,15]
        self.nulist = [12,14,16]
        self.quarklist = [1,2,3,4,5,6]
        self.PseMesList = [211,321,411,431,521,541]
        self.PseMes0List = [111,221,331,441]
        self.VecMesList = [213,413,433]
        self.VecMes0List = [113,223,333,443]
        
        self.db_file = db_file
        self.load_parameters()

    def load_parameters(self) -> None:
        """
        Load simulation parameters from a file if it exists; otherwise, create a new one from the Particle librairy.
        """
        if os.path.exists(self.db_file):
            self.load_from_file()
        else:
            print(f"No db file, creating one now in {self.db_file}")
            self.load_from_particle_package()
            self.add_decay_const()
            self.save_to_file()
        

    def load_from_particle_package(self) -> None:
        """
        Load particle data from the Particle package and populate the parameters dictionary.
        """
        for particle in Particle.findall(lambda x: x.pdgid < 6000 and x.pdgid > -6000):
            if particle.pdgid == 213 or particle.pdgid == 413 or particle.pdgid == 433:
                a = 1

            pdgid = int(particle.pdgid)
            if particle.mass is not None:
                self.params[pdgid] = {"mass" : particle.mass* 10**(-3), "charge" : particle.charge, "width" : particle.width}
            else:
                self.params[pdgid] = {"mass" : particle.mass, "charge" : particle.charge, "width" : particle.width}

    def load_from_file(self) -> None:
        """
        Load simulation parameters from a JSON file.
        """
        with open(self.db_file, 'r') as f:
            self.params = json.load(f)
        for category in self.params:
            self.params[category] = {int(key) if is_int(key) else key: value for key, value in self.params[category].items()}

    def save_to_file(self) -> None:
        """
        Save simulation parameters to a JSON file.
        """
        os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
        with open(self.db_file, 'w') as f:
            json.dump(self.params, f, indent = 4)

    def get_parameter(self, code : int , category : str):
        """
        Retrieve a specific parameter for a given particle.

        :param code: Particle ID.
        :param category: Parameter category (e.g., "mass", "charge").
        :return: The value of the requested parameter or None if not found.
        """
        if code not in self.params.keys():
            if str(code) not in self.params.keys():
                raise KeyError(f'Particle {code} does not exist.')
            else:
               return self.params.get(str(code), {}).get(category, None) 
        else:
            return self.params.get(code, {}).get(category, None)

    def set_parameter(self, code : int, category : str, value) -> None:
        """
        Set a parameter value for a given particle and save changes to file.

        :param code: Particle ID.
        :param category: Parameter category (e.g., "mass", "charge").
        :param value: New value to set.
        """
        if code not in self.params:
            self.params[code] = {}
        self.params[code][category] = value
        self.save_to_file()

    def add_decay_const(self):
        """
        Add decay constants and other specific parameters to the simulation database.
        """
        self.params[211]["mDecays"] = 130.2*10**(-3)
        self.params[321]["mDecays"] = 155.7*10**(-3)
        self.params[411]["mDecays"] = 212.0*10**(-3)
        self.params[431]["mDecays"] = 249.9*10**(-3)
        self.params[521]["mDecays"] = 190.0*10**(-3)
        self.params[541]["mDecays"] = 434*10**(-3)
        self.params[111]["mDecays"] = 130.2*10**(-3)
        self.params[221]["mDecays"] = 81.7*10**(-3)
        self.params[331]["mDecays"] = -94.7*10**(-3)
        self.params[441]["mDecays"] = 237*10**(-3)
        
        self.params[113]["Kappah"] = 1-2*self.constants["sw2"]
        self.params[223]["Kappah"] = 4/3 * self.constants["sw2"]
        self.params[333]["Kappah"] = 4/3 * self.constants["sw2"]-1
        self.params[443]["Kappah"] =1- 8/3 * self.constants["sw2"]
        
        self.params[213]["gh"] = 0.162
        self.params[413]["gh"] = 0.535
        self.params[433]["gh"] = 0.650
        self.params[113]["gh"] = 0.162
        self.params[223]["gh"] = 0.153
        self.params[333]["gh"] = 0.234
        self.params[443]["gh"] = 1.29

        self.params[211]["CKM"] = self.CKM_matrix[0][0]
        self.params[321]["CKM"] = self.CKM_matrix[0][1]
        self.params[411]["CKM"] = self.CKM_matrix[1][0]
        self.params[431]["CKM"] = self.CKM_matrix[1][1]
        self.params[521]["CKM"] = self.CKM_matrix[0][2]
        self.params[541]["CKM"] = self.CKM_matrix[1][2]
        self.params[213]["CKM"] = self.CKM_matrix[0][0]
        self.params[413]["CKM"] = self.CKM_matrix[1][0]
        self.params[433]["CKM"] = self.CKM_matrix[1][1]
        
    def add_parameter(self, category, code, value):
        """
        Add a new parameter to the database.

        :param category: Category name.
        :param code: Parameter identifier.
        :param value: Parameter value.
        """
        if category not in self.params:
            self.params[category] = {}
        if code in self.params[category]:
            raise KeyError(f'Parameter {code} already exists in category {category}.')
        self.params[category][code] = value
        self.save_to_file()

    def update_parameter(self, category, code, value):
        """
        Update an existing parameter in the database.

        :param category: Category name.
        :param code: Parameter identifier.
        :param value: New value.
        """
        if category not in self.params or code not in self.params[category]:
            raise KeyError(f'Parameter {code} does not exist in category {category}.')
        self.params[category][code] = value
        self.save_to_file()


if __name__ == "__main__":
    test = SimulationParameters()
    
    print(test.get_parameter(1, "mass"))
    
    
    
    


