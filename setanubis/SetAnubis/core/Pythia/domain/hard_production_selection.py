from enum import Enum

class AbstractEnumProduction(Enum):
    """Base abstract enumeration class for production processes."""
    pass

class HardProductionElectroweakList(AbstractEnumProduction):
    """Enumeration for hard electroweak production processes.

    Attributes:
        WEAKSINGLEBOSON_ALL (str): All weak single boson production processes.
        WEAKSINGLEBOSON_FFBAR_2_GMZ (str): Process involving fermion-antifermion to gamma/Z boson.
        WEAKSINGLEBOSON_FFBAR_2_W (str): Process involving fermion-antifermion to W boson.
        WEAKBOSONANDPARTON_QQBAR_2_GMZG (str): Process involving quark-antiquark to gamma/Z boson and gluon.
    """
    WEAKSINGLEBOSON_ALL = "WeakSingleBoson:all"
    WEAKSINGLEBOSON_FFBAR_2_GMZ = "WeakSingleBoson:ffbar2gmZ"
    WEAKSINGLEBOSON_FFBAR_2_W = "WeakSingleBoson:ffbar2W"
    WEAKBOSONANDPARTON_QQBAR_2_GMZG = "WeakBosonAndParton:qqbar2gmZg"  

class HardProductionQCDList(AbstractEnumProduction):
    """Enumeration for hard QCD production processes.

    Attributes:
        HARDQCD_HARD_C_CBAR (str): Hard charm quark-antiquark pair production.
        HARDQCD_HARDB_B_BAR (str): Hard bottom quark-antiquark pair production.
    """
    HARDQCD_HARD_C_CBAR = "HardQCD::hardccbar"
    HARDQCD_HARDB_B_BAR = "HardQCD::hardbbbar"