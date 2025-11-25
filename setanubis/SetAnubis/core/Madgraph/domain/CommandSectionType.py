from enum import Enum

class CommandSectionType(Enum):
    HEADER = "header"
    BASE_MODEL = "base_model"
    MODEL_IMPORT = "model_import"
    DEFINITIONS = "definitions"
    PROCESS = "process"
    OUTPUT = "output"
    LAUNCH = "launch"
    SETTINGS = "settings"
    CARDS = "cards"
    PARAMETERS = "parameters"
    SHOWER = "shower"
    MADSPIN = "madspin"
    FOOTER = "footer"