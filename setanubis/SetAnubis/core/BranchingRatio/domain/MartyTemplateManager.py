from SetAnubis.core.Common.MultiSet import MultiSet
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
from SetAnubis.core.BranchingRatio.domain.MartyUtil import decay_name, load_ufo_mappings, load_particle_mappings

from enum import Enum
import os
import re

class TemplateType(Enum):
    ANALYTIC = "ANALYTIC"
    NUMERIC = "NUMERIC"
    

class MartyTemplateManager:
    def __init__(self, model_name : str, mothers : MultiSet, daugthers : MultiSet, template_type : TemplateType, nsa : SetAnubisInterface):
        self.model_name = model_name
        self.mothers = mothers
        self.daugthers = daugthers
        self.template_type = template_type
        self.nsa = nsa
        
        self._temp : str = ""
        if self.template_type == TemplateType.ANALYTIC:
            self._set_base_analytic()
        else:
            self._set_base_numeric()
        
    def _set_base_analytic(self):
        self._temp = """#include <iostream>
#include "/home/theo/hyperiso/Third_party/MARTY/src/MARTY/src/marty/models/sm.h"
#include "/home/theo/hyperiso/Third_party/MARTY/MARTY_INSTALL/include/marty.h"
//42

using namespace csl;
using namespace mty;
using namespace std;
using namespace sm_input;

void defineLibPath(Library &lib) {
#ifdef MARTY_LIBRARY_PATH
    lib.addLPath(MARTY_LIBRARY_PATH);
    lib.addLPath(MARTY_LIBRARY_PATH "/..");
    lib.addLPath(MARTY_LIBRARY_PATH "/marty");
    lib.addLPath(MARTY_LIBRARY_PATH "/marty/lha");
#endif
#ifdef MARTY_INCLUDE_PATH
    lib.addIPath(MARTY_INCLUDE_PATH);
#endif
}

int main() {
    
    SM_Model model;
    
    //model.getParticle("W")->setWidth(csl::constant_s("G_W"));
    //model.getParticle("Z")->setWidth(csl::constant_s("G_Z"));
    model.getParticle("W")->setGaugeChoice(gauge::Type::Unitary);
    model.getParticle("Z")->setGaugeChoice(gauge::Type::Unitary);
    undefineNumericalValues();
    
    
    
    FeynOptions opts;

    auto ampli = model.computeAmplitude(mty::Order::OneLoop,
        {Incoming("b"), Outgoing("s"),
         Outgoing("c"), Outgoing(AntiPart("c"))},
        opts);
        
    Show(ampli);
    Expr decay_width = model.computeSquaredAmplitude(ampli);

    [[maybe_unused]] int sysres = system("rm -rf libs/decay_widths");
    mty::Library decayLib("decay_widths", "libs");
    decayLib.cleanExistingSources();
    decayLib.addFunction("decay_width", decay_width);
    defineLibPath(decayLib);
    decayLib.print();

    return 0;
}"""

    def _set_base_numeric(self):
        self._temp = """#include "decay_widths.h"

#include <fstream>
#include <vector>
#include <complex>
#include <fstream>
#include "csv_helper.h"
#include "kinematics.h"
#include "integration.h"

using namespace decay_widths;

int main() {

    param_t param;

    std::string ParamFilePath = "/home/theo/hyperiso/Assets/MartyTemp/libs/C10_SM/bin/paramlist.csv";
	std::ifstream ParamFile(ParamFilePath);
    readParams(ParamFile, param.realParams, param.complexParams);
    
    Kinematics kin{{1000}, {0.106, 0.106}, 400, &param};

    Integrator integ{"decay_width", kin};

    integ.integrate();

    std::cout << "Value : " << integ.get_integral_value() << std::endl;

    return 0;
}
        """
        
    def _change_namespace(self):
        """Change 'using namespace decay_widths;' selon le nom du fichier généré"""
        namespace_name = f'decay_widths_{decay_name(self.mothers, self.daugthers, self.nsa, load_ufo_mappings(True))}'
        self._temp = re.sub(r'using namespace decay_widths;', f'using namespace {namespace_name};', self._temp)

    # def _decay_name(self):
    #     """Génère un nom de fichier basé sur la mère et les filles (ex: b_c_cbar)"""
    #     names = [convert_particle(self.mother)] + [convert_particle(d) for d in self.daugthers]
    #     return "_".join(names)
    
    def _change_model(self):
        if self.template_type == TemplateType.NUMERIC:
            return
        base_path = os.path.abspath(__file__)
        root_path = os.path.abspath(os.path.join(base_path, *(['..'] * 6)))
        header_path = os.path.join(root_path, 'Assets', 'MARTY', 'model', self.model_name.lower() + '.h')

        include_pattern = r'#include\s+".*/models/.*?\.h"'
        new_include = f'#include "{header_path}"'

        model_pattern = r'\b\w+_Model\s+model\s*;'
        new_model_decl = f'{self.model_name}_Model model;'

        self._temp = re.sub(include_pattern, new_include, self._temp)
        self._temp = re.sub(model_pattern, new_model_decl, self._temp)
    
    def _change_paramlist(self):
        
        decay = decay_name(self.mothers, self.daugthers, self.nsa, load_ufo_mappings(True))
        
        base_path = os.path.abspath(__file__)
        root_path = os.path.abspath(os.path.join(base_path, *(['..'] * 6)))
        
        paramlist_path = os.path.join(root_path, 'Assets', 'MARTY', 'MartyTemp', "libs", "decay_widths_" + decay, "bin", "paramlist.csv")

        self._temp = re.sub(
            r'std::string ParamFilePath = ".*?";',
            f'std::string ParamFilePath = "{paramlist_path}";',
            self._temp
        )

        
    def _change_particles(self):
        if self.template_type == TemplateType.ANALYTIC:
            # --------- Partie ANALYTIC ----------
            # === 1. Remplacer les particules dans computeAmplitude ===
            mapping = load_particle_mappings()
            # mother_name = mapping.get(str(self.mother), "")
            # if mother_name == "":
            #     raise ValueError("Invalid mother name : " + self.mother)
            
            # incoming = f'Incoming("{mother_name}")'
            
            incomings = []
            if isinstance(self.mothers, list):
                for m in self.mothers:
                    name = mapping.get(str(abs(m)), "")
                    if name == "":
                        raise ValueError("Invalid mother name : " + str(m))
                    if m < 0:
                        incomings.append(f'Incoming(AntiPart("{name}"))')
                    else:
                        incomings.append(f'Incoming("{name}")')
            else:
                name = mapping.get(str(abs(self.mothers)), "")
                if name == "":
                    raise ValueError("Invalid mother name : " + str(self.mothers))
                if self.mothers < 0:
                    incomings.append(f'Incoming(AntiPart("{name}"))')
                else:
                    incomings.append(f'Incoming("{name}")')
        
            outgoings = []
            for d in self.daugthers:
                name = mapping.get(str(abs(d)), "")
                if name == "":
                    raise ValueError("Invalid daugther name : " + str(d))
                if d < 0:
                    outgoings.append(f'Outgoing(AntiPart("{name}"))')
                else:
                    outgoings.append(f'Outgoing("{name}")')
            # particle_list = ",\n             ".join([incoming] + outgoings)
            particle_list = ",\n             ".join(incomings + outgoings)
            # === 2. Nettoyer et remplacer le bloc computeAmplitude(...) ===
            pattern = r'auto\s+ampli\s*=\s*model\.computeAmplitude\([^;]+?\);\s*'
            replacement = f'''auto ampli = model.computeAmplitude(mty::Order::TreeLevel, {{
                {particle_list}
            }}, opts);
    '''
            self._temp = re.sub(pattern, replacement, self._temp, flags=re.DOTALL)

            # === 2. Modifier les chemins pour decayLib ===
            decay = decay_name(self.mothers, self.daugthers, self.nsa, load_ufo_mappings(True))
            print(incomings, outgoings)
            self._temp = re.sub(
                r'system\("rm -rf libs/decay_widths"\);',
                f'system("rm -rf libs/decay_widths_{decay}");',
                self._temp
            )
            self._temp = re.sub(
                r'mty::Library\s+decayLib\("decay_widths",\s*"libs"\);',
                f'mty::Library decayLib("decay_widths_{decay}", "libs");',
                self._temp
            )

        elif self.template_type == TemplateType.NUMERIC:
            decay = decay_name(self.mothers, self.daugthers, self.nsa, load_ufo_mappings(True))

            self._temp = re.sub(
                r'#include\s+"decay_widths\.h"',
                f'#include "decay_widths_{decay}.h"',
                self._temp
            )

            self._change_namespace()
            is_list_mothers = isinstance(self.mothers, list)
            mothers = self.mothers
            if isinstance(self.mothers, list) and len(self.mothers) <=1:
                is_list_mothers = False
                mothers = self.mothers[0]
                
            if is_list_mothers:
                mother_masses = [self.nsa.get_particle_mass(m) for m in mothers]
            else:
                mother_masses = [self.nsa.get_particle_mass(mothers)]

            sum_mothers = sum(mother_masses)
            
            daughter_masses = [self.nsa.get_particle_mass(d) for d in self.daugthers]

            mothers_block   = '{' + ', '.join(map(str, mother_masses)) + '}'
            daughters_block = '{' + ', '.join(map(str, daughter_masses)) + '}'

            # def replace_kinematics_masses(match):
            #     return f"{{{{{', '.join(map(str, mother_masses))}}}, {{{', '.join(map(str, daugther_masses))}}},"

            # self._temp = re.sub(
            #     r'\{\{[^\}]*\},\s*\{[^\}]*\},',  # match juste les deux listes
            #     replace_kinematics_masses,
            #     self._temp
            # )
            
            def replace_kinematics_block(match):
                # garder l'indentation originale
                indent = re.match(r'\s*', match.group(0)).group(0)

                if is_list_mothers:
                    # avec s paramétrable + vérification ∑m < s
                    return (
                        f"{indent}double s = 400; // librement modifiable\n"
                        f"{indent}if ({sum_mothers} >= s) {{\n"
                        f"{indent}    std::cerr << \"[Erreur] Somme des masses des mères (={sum_mothers}) >= s=\" << s << std::endl;\n"
                        f"{indent}    return 1;\n"
                        f"{indent}}}\n"
                        f"{indent}Kinematics kin{{{mothers_block}, {daughters_block}, s, &param}};"
                    )
                else:
                    # sans s quand mothers n'est pas une liste
                    return f"{indent}Kinematics kin{{{mothers_block}, {daughters_block}, &param}};"

            self._temp = re.sub(
                r'^\s*Kinematics\s+kin\s*\{[^;]*\};',
                replace_kinematics_block,
                self._temp,
                flags=re.MULTILINE
            )
            
    def _update_marty_include_path(self):
        """Met à jour le chemin absolu de l'include marty.h dans le template"""
        base_path = os.path.abspath(__file__)
        root_path = os.path.abspath(os.path.join(base_path, *(['..'] * 6)))
        marty_header_path = os.path.join(
            root_path, "External_Integration", "Marty", "MARTY_INSTALL", "include", "marty.h"
        )
        marty_header_path = marty_header_path.replace("\\", "/")  # Pour Windows si besoin

        self._temp = re.sub(
            r'#include\s+"?.*?/MARTY_INSTALL/include/marty\.h"?',
            f'#include "{marty_header_path}"',
            self._temp
        )
    
if __name__ == "__main__":
    nsa = SetAnubisInterface("Assets/UFO/UFO_HNL")
    mtm = MartyTemplateManager("SM", 23, [2,-2], TemplateType.ANALYTIC, nsa)
    mtm._change_model()
    mtm._change_particles()
    mtm._update_marty_include_path()
    
    from SetAnubis.core.BranchingRatio.domain.MartyCompiler import MartyCompiler, CompilerType
    from pathlib import Path
    
    def build_and_run(m : MartyTemplateManager, nsa):
        """Génère le fichier C++, compile et exécute avec MartyCompiler (GCC)"""

        decay = decay_name(m.mother, m.daugthers, nsa, load_ufo_mappings(True))
        cpp_filename = f"{decay}.cpp"
        binary_filename = decay

        # === Détermination des chemins ===
        base_path = Path(__file__).resolve()
        root_path = base_path.parents[5]
        output_dir = root_path / "Assets" / "MARTY" / "MartyTemp"
        # print(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        cpp_path = output_dir / cpp_filename
        bin_path = output_dir / binary_filename

        # === Écriture du fichier C++ ===
        with open(cpp_path, "w") as f:
            f.write(m._temp)
        print(f"✅ C++ file written: {cpp_path}")

        # === Compilation & exécution avec MartyCompiler ===
        compiler = MartyCompiler(CompilerType.GCC)
        compiler.compile_run(
            source_file=str(cpp_path),
            output_binary=str(bin_path),
            output_dir=str(output_dir)
        )
    
    build_and_run(mtm, nsa)
    
    mtm_2 = MartyTemplateManager("SM", 23, [2,-2], TemplateType.NUMERIC, nsa)
    
    mtm_2._change_paramlist()
    mtm_2._change_particles()
    
    from SetAnubis.core.BranchingRatio.domain.MartyParamManager import ParamManager
    header_file = Path("Assets/MARTY/MartyTemp/libs/decay_widths_23_s_2_2/include/params.h")
    param_manager = ParamManager(header_file, nsa)
    
    print("parameters : ", param_manager.get_parameters())
    csv = param_manager.create_csv()
    
    base_path = Path(__file__).resolve()
    root_path = base_path.parents[5]
    output_dir = root_path / "Assets" / "MARTY" / "MartyTemp"
        
    csv_path = output_dir / "libs" / "decay_widths_23_s_2_2" / "bin" / "paramlist.csv"
    cpp_path = output_dir / "libs" / "decay_widths_23_s_2_2" / "script" / "example_decay_widths_23_s_2_2.cpp"
    
    print("output dir : ", output_dir)
    
    with open(csv_path, "w") as f:
            f.write(csv)
            print(f"csv file written: {csv_path}")
        
    with open(cpp_path, "w") as f:
            f.write(mtm_2._temp)
            print(f"cpp file written: {cpp_path}")
            
    
    from SetAnubis.core.BranchingRatio.adapters.output.MartyFileCopyBuilder import MartyFileCopyBuilder
    
    mfcb = MartyFileCopyBuilder()
    
    mfcb.execute()
    
    compiler = MartyCompiler(CompilerType.MAKE, "decay_widths_23_s_2_2")
    
    compiler.compile_run("decay_widths_23_s_2_2")