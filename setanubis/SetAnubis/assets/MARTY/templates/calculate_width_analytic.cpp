#include <iostream>
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

    model.getParticle("W")->setGaugeChoice(gauge::Type::Feynman);
    model.getParticle("Z")->setGaugeChoice(gauge::Type::Feynman);
    undefineNumericalValues();
    
    FeynOptions opts;

    auto ampli = model.computeWilsonCoefficients(mty::Order::OneLoop,
        {Incoming("b"), Outgoing("s"),
         Outgoing("c"), Outgoing(AntiPart("c"))},
        opts);
    
    Expr decay_width = model.computeSquaredAmplitude(ampli);

    [[maybe_unused]] int sysres = system("rm -rf libs/decay_widths");
    mty::Library decayLib("decay_widths", "libs");
    decayLib.cleanExistingSources();
    decayLib.addFunction("decay_width", decay_width);
    defineLibPath(decayLib);
    decayLib.print();

    return 0;
}