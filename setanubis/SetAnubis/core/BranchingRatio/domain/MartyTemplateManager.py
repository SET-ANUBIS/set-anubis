"""Render analytic and numerical C++ sources for MARTY workflows."""

from SetAnubis.core.Common.MultiSet import MultiSet
from SetAnubis.core.ModelCore.adapters.input.SetAnubisInteface import SetAnubisInterface
from SetAnubis.core.BranchingRatio.domain.MartyUtil import (
    decay_name,
    load_ufo_mappings,
    load_particle_mappings,
)
from SetAnubis.core.BranchingRatio.domain.MartyRuntimeConfig import MartyPathConfig
from SetAnubis.core.BranchingRatio.domain.MartyAmplitudeConfig import (
    MartyAmplitudeComponent,
    amplitude_config_suffix,
)

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
        path_config: MartyPathConfig | None = None,
        amplitude_components: tuple[MartyAmplitudeComponent, ...] = (),
    ):
        """Initialize a source template for one process and model."""
        self.model_name = model_name
        self.mothers = mothers
        self.daugthers = daugthers
        self.template_type = template_type
        self.nsa = nsa
        self.path_config = path_config or MartyPathConfig.resolve(model_name)
        self.amplitude_components = tuple(amplitude_components)

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
            self._change_partlist()
        return self._temp

    def render(self) -> str:
        """Return the current generated source text."""
        return self._temp

    def _decay_name(self) -> str:
        """Return the process name including the amplitude-config cache key."""
        base = decay_name(
            self.mothers,
            self.daugthers,
            self.nsa,
            load_ufo_mappings(True, self.path_config.mapping_dir),
        )
        return base + amplitude_config_suffix(self.amplitude_components)

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

#include <iostream>
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
    if (!ParamFile.is_open()) {
        std::cerr << "[Error] Cannot open parameter file: " << ParamFilePath << std::endl;
        return 123;
    }
    readParams(ParamFile, param.realParams, param.complexParams);

    std::string PartFilePath = "partlist.csv";
    std::ifstream PartFile(PartFilePath);
    if (!PartFile.is_open()) {
        std::cerr << "[Error] Cannot open particle file: " << PartFilePath << std::endl;
        return 123;
    }
    auto [outgoing_masses, incoming_masses] = readParts(PartFile);

    Kinematics kin{{1000}, {0.106, 0.106}, 400, &param};

    Integrator integ{"decay_width", kin};

    integ.integrate();

    std::cout << "Value : " << integ.get_integral_value() << std::endl;

    return 0;
}
        """

    def _change_namespace(self):
        """Update the decay-width namespace for the generated filename."""
        # MARTY lowercases the generated C++ namespace even when the library
        # name contains uppercase characters. Match that convention here.
        namespace_name = f"decay_widths_{self._decay_name()}".lower()
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
        if self.path_config.model_path is not None:
            header_path = self.path_config.model_path
            new_include = f'#include "{header_path.as_posix()}"'
        elif self.model_name.upper() == "SM":
            new_include = '#include "marty/models/sm.h"'
        else:  # defensive: non-SM configs resolve a concrete model header
            raise FileNotFoundError(
                f"No MARTY model header configured for {self.model_name!r}"
            )

        model_pattern = r"\b\w+_Model\s+model\s*;"
        new_model_decl = f"{self.model_name}_Model model;"

        self._temp = re.sub(include_pattern, new_include, self._temp)
        self._temp = re.sub(model_pattern, new_model_decl, self._temp)

    def _change_paramlist(self):

        decay = self._decay_name()

        paramlist_path = (
            self.path_config.workspace_dir
            / "libs"
            / ("decay_widths_" + decay)
            / "bin"
            / "paramlist.csv"
        ).as_posix()

        self._temp = re.sub(
            r'std::string ParamFilePath = ".*?";',
            f'std::string ParamFilePath = "{paramlist_path}";',
            self._temp,
        )

    def _change_partlist(self):
        """Point the numeric executable to the runtime particle-mass table."""
        decay = self._decay_name()
        partlist_path = (
            self.path_config.workspace_dir
            / "libs"
            / ("decay_widths_" + decay)
            / "bin"
            / "partlist.csv"
        ).as_posix()

        self._temp = re.sub(
            r'std::string PartFilePath = ".*?";',
            f'std::string PartFilePath = "{partlist_path}";',
            self._temp,
        )

    def _render_component_amplitudes(self, particle_list: str) -> str:
        """Render mediator-resolved MARTY amplitudes and their full square."""
        blocks: list[str] = []
        amplitude_names: list[str] = []

        for index, component in enumerate(self.amplitude_components):
            opts_name = f"opts_component_{index}"
            ampli_name = f"ampli_component_{index}"
            amplitude_names.append(ampli_name)

            blocks.append(f"FeynOptions {opts_name};")
            if component.fermion_order is not None:
                order = ", ".join(str(value) for value in component.fermion_order)
                blocks.append(f"{opts_name}.setFermionOrder({{{order}}});")

            mediator_tests = " || ".join(
                f'diag.isMediator("{name}")' for name in component.mediators
            )
            blocks.extend(
                [
                    f"{opts_name}.addFilter([&](mty::FeynmanDiagram const &diag) {{",
                    f"    return {mediator_tests};",
                    "});",
                    f"auto {ampli_name} = model.computeAmplitude(mty::Order::TreeLevel, {{",
                    f"    {particle_list}",
                    f"}}, {opts_name});",
                    f'std::cout << "[SET-ANUBIS] mediator component: {component.label}" << std::endl;',
                    f"Show({ampli_name});",
                    "",
                ]
            )

        blocks.append("Expr decay_width = CSL_0;")
        for ampli_name in amplitude_names:
            blocks.append(
                f"decay_width += model.computeSquaredAmplitude({ampli_name});"
            )

        # For Ai + Aj, |M|^2 contains Ai Aj^dagger + Aj Ai^dagger.  MARTY's
        # two-amplitude overload keeps the FeynOptions/fermion order attached
        # to each amplitude, which is exactly what is required here.
        for left in range(len(amplitude_names)):
            for right in range(left + 1, len(amplitude_names)):
                a_left = amplitude_names[left]
                a_right = amplitude_names[right]
                blocks.append(
                    f"decay_width += model.computeSquaredAmplitude({a_left}, {a_right});"
                )
                blocks.append(
                    f"decay_width += model.computeSquaredAmplitude({a_right}, {a_left});"
                )

        return "\n    ".join(blocks)

    def _change_particles(self):
        if self.template_type == TemplateType.ANALYTIC:
            # Analytic template path.
            # 1. Replace particles in computeAmplitude.
            mapping = load_particle_mappings(mapping_dir=self.path_config.mapping_dir)
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
            # 2. Replace the amplitude/squaring block.  With no explicit
            # mediator configuration this is byte-for-byte the historical
            # single-amplitude behaviour.  With components, each mediator
            # family gets its own FeynOptions (and therefore its own fermion
            # order), while the final square includes all diagonal and
            # pairwise interference terms.
            if self.amplitude_components:
                replacement = self._render_component_amplitudes(particle_list)
                pattern = (
                    r"FeynOptions\s+opts;.*?"
                    r"Expr\s+decay_width\s*=\s*model\.computeSquaredAmplitude\(ampli\);"
                )
                self._temp = re.sub(
                    pattern, replacement, self._temp, flags=re.DOTALL
                )
            else:
                pattern = r"auto\s+ampli\s*=\s*model\.computeAmplitude\([^;]+?\);\s*"
                replacement = f"""auto ampli = model.computeAmplitude(mty::Order::TreeLevel, {{
                {particle_list}
            }}, opts);
    """
                self._temp = re.sub(
                    pattern, replacement, self._temp, flags=re.DOTALL
                )

            # 3. Update decayLib paths.
            decay = self._decay_name()
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
            decay = self._decay_name()

            self._temp = re.sub(
                r'#include\s+"decay_widths\.h"',
                f'#include "decay_widths_{decay}.h"',
                self._temp,
            )

            self._change_namespace()
            is_list_mothers = isinstance(self.mothers, (list, MultiSet)) and len(self.mothers) > 1
            expected_incoming = len(self.mothers) if isinstance(self.mothers, (list, MultiSet)) else 1
            expected_outgoing = len(self.daugthers)

            def replace_kinematics_block(match):
                # Mass values are intentionally NOT embedded in generated C++.
                # They are refreshed in partlist.csv by build_numeric() on every
                # call, allowing parameter/mass scans to reuse the executable.
                indent = re.match(r"\s*", match.group(0)).group(0)
                checks = (
                    f'{indent}if (incoming_masses.size() != {expected_incoming} || '
                    f'outgoing_masses.size() != {expected_outgoing}) {{\n'
                    f'{indent}    std::cerr << "[Error] partlist.csv contains " '
                    f'<< incoming_masses.size() << " incoming and " '
                    f'<< outgoing_masses.size() << " outgoing masses; expected '
                    f'{expected_incoming} and {expected_outgoing}." << std::endl;\n'
                    f'{indent}    return 123;\n'
                    f'{indent}}}\n'
                )

                if is_list_mothers:
                    # Keep the historical configurable CoM energy for 2->N
                    # processes, but validate thresholds using runtime masses.
                    return (
                        checks
                        + f"{indent}double s = 400; // can be modified\n"
                        + f"{indent}double sum_mothers = 0.0;\n"
                        + f"{indent}for (double mass : incoming_masses) sum_mothers += mass;\n"
                        + f"{indent}if (sum_mothers >= s) {{\n"
                        + f'{indent}    std::cerr << "[Error] Sum of mothers masses (= " '
                          f'<< sum_mothers << ") >= s=" << s << std::endl;\n'
                        + f"{indent}    return 1;\n"
                        + f"{indent}}}\n"
                        + f"{indent}Kinematics kin{{incoming_masses, outgoing_masses, s, &param}};"
                    )

                return (
                    checks
                    + f"{indent}Kinematics kin{{incoming_masses.at(0), outgoing_masses, &param}};"
                )

            self._temp = re.sub(
                r"^\s*Kinematics\s+kin\s*\{[^;]*\};",
                replace_kinematics_block,
                self._temp,
                flags=re.MULTILINE,
            )

    def _update_marty_include_path(self):
        """Embed the resolved MARTY header when an installation is configured.

        ``MartyCompiler`` also supplies the corresponding include directory via
        ``-I``.  Embedding the concrete ``marty.h`` path keeps generated source
        self-describing and preserves the historical
        ``SETANUBIS_MARTY_INCLUDE_DIR`` override as a fallback.
        """
        install = self.path_config.marty_install
        if install is not None:
            header = install.header.as_posix()
        else:
            include_dir = os.environ.get("SETANUBIS_MARTY_INCLUDE_DIR")
            if not include_dir:
                return
            header = (Path(include_dir).expanduser().resolve() / "marty.h").as_posix()

        self._temp = re.sub(
            r'#include\s+["<](?:.*?/)?marty\.h[">]',
            f'#include "{header}"',
            self._temp,
        )
