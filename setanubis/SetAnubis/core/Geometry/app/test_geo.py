import matplotlib
matplotlib.use("tkagg")
import matplotlib.pyplot as plt
from SetAnubis.core.Geometry.domain.builder import GeometryBuilder, GeometryBuildConfig
from SetAnubis.core.Geometry.adapters.geometry_builder import CavernGeometryBuilder
from SetAnubis.core.Geometry.adapters.geometry_query import CavernQuery
from SetAnubis.core.Geometry.adapters.selection_adapter import GeometrySelectionAdapter
from SetAnubis.core.Selection.adapters.input.SelectionGeometryAdapter import SelectionGeometryAdapter
from SetAnubis.core.Geometry.adapters.plot_adapter import MatplotlibPlotter


if __name__ == "__main__":
    gcfg = GeometryBuildConfig(
        geo_cache_file="atlas_cavern.pkl",
        origin="IP",
        RPCeff=1.0,
        nRPCsPerLayer=1,
        geometryType=""  # "", "ceiling", "shaft", "shaft+cone", ...
    )
    builder = GeometryBuilder(CavernGeometryBuilder(gcfg))
    geom: CavernQuery = builder.build()

    geom_row = GeometrySelectionAdapter(geom)

    sel_geo = SelectionGeometryAdapter(geom_row)
    
    
    ax = plt.subplot()
    geom.cavern.plotCavern3D(ax)
    # plotter = MatplotlibPlotter()
    # plotter.plot(geom.cavern, show=True, savepath="geom_new.png")
    plt.show()
    print("Plot enregistré -> geom_new.png")