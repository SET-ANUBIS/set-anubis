"""Render analytic and numerical C++ sources for MARTY workflows."""

from SetAnubis.core.Common.MultiSet import MultiSet
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
from SetAnubis.core.BranchingRatio.domain.MartyUtil import (
    decay_name,
    load_ufo_mappings,
    load_particle_mappings,
)
from SetAnubis.resources import asset_path

from enum import Enum
import os
from pathlib import Path
import re


class TemplateType(Enum):
    """Available generated MARTY source stages."""

    ANALYTIC = "ANALYTIC"
    NUMERIC = "NUMERIC"


class MartyTemplateManager:
    """Apply process and environment substitutions to MARTY C++ templates."""

    def __init__(
        self,
        model_name: str,
        mothers: MultiSet,
        daugthers: MultiSet,
        template_type: TemplateType,
        nsa: SetAnubisInterface,
    ):
        """Initialize a source template for one process and model."""
        self.model_name = model_name
        self.mothers = mothers
        self.daugthers = daugthers
        self.template_type = template_type
        self.nsa = nsa

        self._temp: str = ""
        if self.template_type == TemplateType.ANALYTIC:
            self._set_base_analytic()
        else:
            self._set_base_numeric()

    def prepare(self) -> str:
        """Render the configured MARTY source without compiling or executing it."""
        if self.template_type == TemplateType.ANALYTIC:
            self._change_model()
            self._change_particles()
            self._update_marty_include_path()
        else:
            self._change_particles()
            self._change_paramlist()
        return self._temp

    def render(self) -> str:
        """Return the current generated source text."""
        return self._temp

    def _set_base_analytic(self):
        self._temp = """#include <iostream>
#include "marty/models/sm.h"
#include "marty.h"
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
    
    model.getParticle("W")->setWidth(csl::constant_s("G_W"));
    model.getParticle("Z")->setWidth(csl::constant_s("G_Z"));
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

    std::string ParamFilePath = "paramlist.csv";
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
        """Update the decay-width namespace for the generated filename."""
        namespace_name = f"decay_widths_{decay_name(self.mothers, self.daugthers, self.nsa, load_ufo_mappings(True))}"
        self._temp = re.sub(
            r"using namespace decay_widths;",
            f"using namespace {namespace_name};",
            self._temp,
        )

    # def _decay_name(self):
    #     Build a filename from the mother and daughter particles.
    #     names = [convert_particle(self.mother)] + [convert_particle(d) for d in self.daugthers]
    #     return "_".join(names)

    def _change_model(self):
        """Select the standard MARTY model or a bundled custom model header."""
        if self.template_type == TemplateType.NUMERIC:
            return

        include_pattern = r'#include\s+".*/models/.*?\.h"'
        if self.model_name.upper() == "SM":
            new_include = '#include "marty/models/sm.h"'
        else:
            header_path = asset_path("MARTY", "model", self.model_name.lower() + ".h")
            new_include = f'#include "{header_path.as_posix()}"'

        model_pattern = r"\b\w+_Model\s+model\s*;"
        new_model_decl = f"{self.model_name}_Model model;"

        self._temp = re.sub(include_pattern, new_include, self._temp)
        self._temp = re.sub(model_pattern, new_model_decl, self._temp)

    def _change_paramlist(self):

        decay = decay_name(
            self.mothers, self.daugthers, self.nsa, load_ufo_mappings(True)
        )

        base_path = os.path.abspath(__file__)
        root_path = os.path.abspath(os.path.join(base_path, *([".."] * 6)))

        paramlist_path = os.path.join(
            root_path,
            "Assets",
            "MARTY",
            "MartyTemp",
            "libs",
            "decay_widths_" + decay,
            "bin",
            "paramlist.csv",
        )

        self._temp = re.sub(
            r'std::string ParamFilePath = ".*?";',
            f'std::string ParamFilePath = "{paramlist_path}";',
            self._temp,
        )

    def _change_particles(self):
        if self.template_type == TemplateType.ANALYTIC:
            # Analytic template path.
            # 1. Replace particles in computeAmplitude.
            mapping = load_particle_mappings()
            # mother_name = mapping.get(str(self.mother), "")
            # if mother_name == "":
            #     raise ValueError("Invalid mother name : " + self.mother)

            # incoming = f'Incoming("{mother_name}")'

            incomings = []
            if isinstance(self.mothers, list) or isinstance(self.mothers, MultiSet):
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
            # 2. Normalize and replace the computeAmplitude block.
            pattern = r"auto\s+ampli\s*=\s*model\.computeAmplitude\([^;]+?\);\s*"
            replacement = f"""auto ampli = model.computeAmplitude(mty::Order::TreeLevel, {{
                {particle_list}
            }}, opts);
    """
            self._temp = re.sub(pattern, replacement, self._temp, flags=re.DOTALL)

            # 3. Update decayLib paths.
            decay = decay_name(
                self.mothers, self.daugthers, self.nsa, load_ufo_mappings(True)
            )
            self._temp = re.sub(
                r'system\("rm -rf libs/decay_widths"\);',
                f'system("rm -rf libs/decay_widths_{decay}");',
                self._temp,
            )
            self._temp = re.sub(
                r'mty::Library\s+decayLib\("decay_widths",\s*"libs"\);',
                f'mty::Library decayLib("decay_widths_{decay}", "libs");',
                self._temp,
            )

        elif self.template_type == TemplateType.NUMERIC:
            decay = decay_name(
                self.mothers, self.daugthers, self.nsa, load_ufo_mappings(True)
            )

            self._temp = re.sub(
                r'#include\s+"decay_widths\.h"',
                f'#include "decay_widths_{decay}.h"',
                self._temp,
            )

            self._change_namespace()
            is_list_mothers = isinstance(self.mothers, list)
            if not is_list_mothers:
                is_list_mothers = isinstance(self.mothers, MultiSet)
            mothers = self.mothers
            if (
                isinstance(self.mothers, list) or isinstance(self.mothers, MultiSet)
            ) and len(self.mothers) <= 1:
                is_list_mothers = False
                if isinstance(self.mothers, list):
                    mothers = self.mothers[0]
                elif isinstance(self.mothers, MultiSet):
                    mothers = self.mothers.items[0]

            if is_list_mothers:
                mother_masses = [self.nsa.get_particle_mass(m) for m in mothers]
            else:
                mother_masses = [self.nsa.get_particle_mass(mothers)]

            sum_mothers = sum(mother_masses)

            daughter_masses = [self.nsa.get_particle_mass(d) for d in self.daugthers]

            mothers_block = "{" + ", ".join(map(str, mother_masses)) + "}"
            daughters_block = "{" + ", ".join(map(str, daughter_masses)) + "}"

            # def replace_kinematics_masses(match):
            #     return f"{{{{{', '.join(map(str, mother_masses))}}}, {{{', '.join(map(str, daugther_masses))}}},"

            # self._temp = re.sub(
            #     r'\{\{[^\}]*\},\s*\{[^\}]*\},',  # match only the two lists
            #     replace_kinematics_masses,
            #     self._temp
            # )

            def replace_kinematics_block(match):
                # Preserve the original indentation.
                indent = re.match(r"\s*", match.group(0)).group(0)

                if is_list_mothers:
                    # Use configurable centre-of-mass energy and validate the threshold.
                    return (
                        f"{indent}double s = 400; // can be modified\n"
                        f"{indent}if ({sum_mothers} >= s) {{\n"
                        f'{indent}    std::cerr << "[Error] Sum of mothers masses (={sum_mothers}) >= s=" << s << std::endl;\n'
                        f"{indent}    return 1;\n"
                        f"{indent}}}\n"
                        f"{indent}Kinematics kin{{{mothers_block}, {daughters_block}, s, &param}};"
                    )
                else:
                    # Omit the centre-of-mass energy for a one-particle decay.
                    return f"{indent}Kinematics kin{{{mothers_block}, {daughters_block}, &param}};"

            self._temp = re.sub(
                r"^\s*Kinematics\s+kin\s*\{[^;]*\};",
                replace_kinematics_block,
                self._temp,
                flags=re.MULTILINE,
            )

    def _update_marty_include_path(self):
        """Use an explicit MARTY include directory when one is configured.

        By default the portable ``#include "marty.h"`` form is preserved so a
        system or user installation can provide its normal compiler include
        flags. Set ``SETANUBIS_MARTY_INCLUDE_DIR`` to embed a concrete header
        path in generated source.
        """
        include_dir = os.environ.get("SETANUBIS_MARTY_INCLUDE_DIR")
        if not include_dir:
            return
        header = (Path(include_dir).expanduser().resolve() / "marty.h").as_posix()
        self._temp = re.sub(
            r'#include\s+["<](?:.*?/)?marty\.h[">]',
            f'#include "{header}"',
            self._temp,
        )
