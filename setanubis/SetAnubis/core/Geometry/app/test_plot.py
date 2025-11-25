import pickle, os
from SetAnubis.core.Geometry.domain.defineGeometry import ATLASCavern
from SetAnubis.core.Geometry.adapters.plot_matplotlib import MatplotlibGeometryPlotter

PKL = "atlas_cavern.pkl"

def load_or_make():
    if os.path.isfile(PKL):
        with open(PKL, "rb") as f:
            cav = pickle.load(f)
    else:
        cav = ATLASCavern()

        cav.createSimpleRPCs([cav.archRadius-0.2, cav.archRadius-1.2], RPCthickness=0.06)
        cav.RPCMaxRadius = cav.archRadius-1.2-0.5
        cav.posOrigin = [cav.IP["x"], cav.IP["y"], cav.IP["z"]]
        with open(PKL, "wb") as f:
            pickle.dump(cav, f)
    return cav

if __name__ == "__main__":
    cav = load_or_make()
    plotter = MatplotlibGeometryPlotter(cav)

    fig, _ = plotter.plot_xy(plot_atlas=True, plot_acceptance=True)
    fig.savefig("geom_new_xy.png", dpi=150, bbox_inches="tight")

    fig, _ = plotter.plot_xz(plot_atlas=True)
    fig.savefig("geom_new_xz.png", dpi=150, bbox_inches="tight")

    fig, _ = plotter.plot_zy(plot_atlas=True, plot_acceptance=True)
    fig.savefig("geom_new_zy.png", dpi=150, bbox_inches="tight")

    try:
        fig, _ = plotter.plot_3d(plot_atlas=True, plot_acceptance=True)
        fig.savefig("geom_new_3d.png", dpi=150, bbox_inches="tight")
    except Exception as e:
        print("plot_3d indisponible:", e)

    print("Plots générés: geom_new_xy/xz/zy(.png) (+ 3d si dispo)")