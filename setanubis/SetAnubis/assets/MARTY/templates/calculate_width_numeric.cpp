#include "decay_widths.h"

#include <fstream>
#include <vector>
#include <complex>

#include "kinematics.h"
#include "integration.h"

using namespace decay_widths;

int main() {

    param_t param_ZX;



    Kinematics kin_mumu{{1000}, {0.106, 0.106}, 400, &param_ZX};

    Integrator integ_mumu{"decay_width", kin_mumu};

    integ_mumu.integrate();

    std::cout << "Value : " << integ_mumu.get_integral_value() << std::endl;

    return 0;
}