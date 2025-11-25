from SetAnubis.core.Pythia.infrastructure.enums import HardProductionQCDList

PROD_TO_HARDQCD = {
    "B_meson": [HardProductionQCDList.HARDQCD_HARDB_B_BAR],
    "D_meson": [HardProductionQCDList.HARDQCD_HARD_C_CBAR],
    "bosonic": [HardProductionQCDList.W_L_HEAVY_NEUTRINO, HardProductionQCDList.Z_HEAVY_NEUTRINO],
    "Lambda_c": [HardProductionQCDList.HARDQCD_HARD_C_CBAR]
}
