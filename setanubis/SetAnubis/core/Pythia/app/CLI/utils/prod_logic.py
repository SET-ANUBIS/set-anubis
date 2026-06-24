from SetAnubis.core.Pythia.infrastructure.enums import HardProductionElectroweakList, HardProductionQCDList

PROD_TO_HARDQCD = {
    "B_meson": [HardProductionQCDList.HARDQCD_HARDB_B_BAR],
    "D_meson": [HardProductionQCDList.HARDQCD_HARD_C_CBAR],
    "Lambda_c": [HardProductionQCDList.HARDQCD_HARD_C_CBAR],
    "bosonic": [HardProductionElectroweakList.WEAKSINGLEBOSON_ALL],
}
