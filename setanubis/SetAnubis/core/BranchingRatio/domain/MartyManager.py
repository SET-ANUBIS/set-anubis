from SetAnubis.core.Common.MultiSet import MultiSet
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
from SetAnubis.core.BranchingRatio.domain.MartyTemplateManager import MartyTemplateManager, TemplateType
from SetAnubis.core.BranchingRatio.domain.MartyUtil import decay_name, load_ufo_mappings
from SetAnubis.core.BranchingRatio.domain.MartyCopyManager import CopyManager
from SetAnubis.core.BranchingRatio.domain.MartyCompiler import MartyCompiler, CompilerType
from SetAnubis.core.BranchingRatio.domain.MartyParamManager import ParamManager
from SetAnubis.core.BranchingRatio.adapters.output.MartyFileCopyBuilder import MartyFileCopyBuilder
from pathlib import Path

class MartyManager:
    def __init__(self, model_name):
        self._model_name = model_name
        
        self.root = Path(__file__).resolve()
        for _ in range(6):
            self.root = self.root.parent
            
    def calculate_process(self, mothers_id : MultiSet, daugthers_id : MultiSet, neo : SetAnubisInterface, builder_marty : MartyFileCopyBuilder):
        
        self.build_analytic(mothers_id, daugthers_id, neo, builder_marty)
        self.launch_analytic(mothers_id, daugthers_id)
        self.build_numeric(mothers_id, daugthers_id, neo, builder_marty)
        return self.launch_numeric(mothers_id, daugthers_id, neo)
    
    def build_analytic(self, mothers_id : MultiSet, daugthers_id : MultiSet, neo : SetAnubisInterface, builder_marty : MartyFileCopyBuilder):
        mtm = MartyTemplateManager(self._model_name, mothers_id, daugthers_id, TemplateType.ANALYTIC, neo)
        mtm._change_model()
        mtm._change_particles()
        mtm._update_marty_include_path()
        analytic_part = mtm._temp
        
        decay = decay_name(mothers_id, daugthers_id, neo, load_ufo_mappings(True))
        cpp_filename = f"{decay}.cpp"
        binary_filename = decay

        cpp_path = self.root / "Assets" / "MARTY" / "MartyTemp" / cpp_filename
        bin_path = self.root / "Assets" / "MARTY" / "MartyTemp" / binary_filename
        
        copy_manager = CopyManager("decay_widths_"+decay, builder_marty)
        copy_manager.write_file(analytic_part, cpp_path)
        
        pass
    
    def launch_analytic(self, mothers_id, daugthers_id):
        decay = decay_name(mothers_id, daugthers_id, neo, load_ufo_mappings(True))
        cpp_filename = f"{decay}.cpp"
            
        output_path = self.root / "Assets" / "MARTY" / "MartyTemp"
        cpp_path = output_path / cpp_filename
        bin_path = output_path / decay
        
        mc = MartyCompiler(CompilerType.GCC, "decay_widths_"+decay)
    
        mc.compile_run(cpp_path, bin_path, output_path)
        pass
    
    def build_numeric(self, mothers_id, daugthers_id, neo : SetAnubisInterface, builder_marty : MartyFileCopyBuilder):
        decay = decay_name(mothers_id, daugthers_id, neo, load_ufo_mappings(True))
        copy_manager = CopyManager("decay_widths_"+decay, builder_marty)
        copy_manager.execute()

        mtm = MartyTemplateManager(self._model_name, mothers_id, daugthers_id, TemplateType.NUMERIC, neo)        
        mtm._change_particles()
        mtm._change_paramlist()
        numeric_part = mtm._temp
        
        cpp_filename = f"example_decay_widths_{decay}.cpp"
        output_path = self.root / "Assets" / "MARTY" / "MartyTemp" / "libs" / ("decay_widths_" + decay)
        cpp_path = output_path / "script" / cpp_filename

        copy_manager.write_file(numeric_part, cpp_path, True)
        
        pm = ParamManager(output_path / "include" / "params.h", neo)
        csv_params = pm.create_csv()
        
        csv_particles = pm.create_particle_csv(mothers_id, daugthers_id)
        
        copy_manager.write_file(csv_params, output_path / "bin" / "paramlist.csv", force=True)
        copy_manager.write_file(csv_particles, output_path / "bin" / "partlist.csv", force=True)
        
        pass
    
    def launch_numeric(self, mothers_id, daugthers_id, neo):
        decay = decay_name(mothers_id, daugthers_id, neo, load_ufo_mappings(True))
        
        mc = MartyCompiler(CompilerType.MAKE, "decay_widths_"+decay)
        return float(mc.compile_run(mc.libs_path, "example_decay_widths_" + decay + ".x", pattern = r"Value\s*:\s*([+-]?(?:\d+(?:\.\d*)?)(?:[eE][+-]?\d+)?)"))
    
    
if __name__ == "__main__":
    # neo = NeoSetAnubisInterface("Assets/UFO/UFO_HNL")
    
    # # mm = MartyManager("HNL")
    
    # # mm.build_analytic([2,-2], [9900012,14], neo)
    
    # # mm.launch_analytic([2,-2], [9900012,14])

    # mm = MartyManager("SM")
    
    builder_marty = MartyFileCopyBuilder()
    
    # result = mm.calculate_process([23], [2,-2], neo, builder_marty)
    
    # print("final : ", result)
    
    # # result_sec = mm.calculate_process([13, -13], [11, -11], neo, builder_marty)
    
    # # print("final : ", result_sec)
    # result = []
    # result2 = []
    # result3 = []
    # x = []
    
    # aa = 0
    # for i in range(81,110):
    #     neo.set_leaf_param("MZ", i)
    #     print(neo.get_particle_mass(24))
    #     result2.append(mm.calculate_process([6], [5, 24], neo, builder_marty))
    #     result3.append(mm.calculate_process([5], [4, -4,3], neo, builder_marty))
    #     result.append(mm.calculate_process([13], [14, 11,-12], neo, builder_marty))
    #     print(result[aa])
    #     aa+=1
    #     x.append(i)
        
    # import matplotlib
    # matplotlib.use("tkagg")
    # import matplotlib.pyplot as plt
    
    # plt.scatter(x, result)
    # plt.scatter(x, result2)
    # plt.savefig("wow_paper.png")
    # mm.build_analytic([13,-13], [11,-11], neo)
    
    # mm.launch_analytic([13,-13], [11,-11])
    
    # mm.build_numeric([13,-13], [11,-11], neo)
    # result = mm.launch_numeric([13,-13], [11,-11], neo)
    
    # print("final : ", result, type(result))
    
    neo = SetAnubisInterface("Assets/UFO/UFO_HNL")
    
    # mm = MartyManager("HNL")
    
    # mm.build_analytic([2,-2], [9900012,14], neo)
    
    # mm.launch_analytic([2,-2], [9900012,14])

    mm = MartyManager("HNL")
    neo.set_leaf_param("mN2", 10)
    neo.set_leaf_param("VmuN1", 1)
    # result = mm.calculate_process([23], [9900014,-14], neo, builder_marty)
    # print("23 -> N1+nu_mu", result)
    # result = mm.calculate_process([24], [9900014,-13], neo, builder_marty)
    # print("24 -> N1 + mu : ", result)
    
    # result = mm.calculate_process([-9900014], [-13,11, -12], neo, builder_marty)
    # print("N1 -> mu + e + nu_e : ", result)
    result = mm.calculate_process([9900014], [-11,+11, 14], neo, builder_marty)
    print("N1 -> nu_mu + e + e : ", result)
    res = []
    for i in range(10, 110, 5):
        neo.set_leaf_param("mN2", i)
        res.append(mm.calculate_process([9900014], [-11,+11, 14], neo, builder_marty))
        # result = mm.calculate_process([9900014], [-11,+11, 14], neo, builder_marty)
    
    import matplotlib
    matplotlib.use("tkagg")
    import matplotlib.pyplot as plt
    plt.scatter(range(10, 110, 5), res)
    
    plt.savefig("niels.png")