// This file is part of MARTY.
//
// MARTY is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// MARTY is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with MARTY. If not, see <https://www.gnu.org/licenses/>.

/*! \file SM.h
 * \author Gregoire Uhlrich
 * \version 1.3
 * \brief File containing the Standard Model itself as a mty::Model object.
 * \details It contains also all input parameters for the standard model,
 * including all values of SMINPUTS block of slha conventions and other
 * paralemers (CKM, masses, couplings etc). Values come from the august 2018
 * edition of the PDG.
 */
#ifndef HNL_H_INCLUDED
#define HNL_H_INCLUDED

#include "sm.h"
#include "../../../External_Integration/Marty/MARTY_INSTALL/include/marty.h"
#include <vector>

using namespace mty::sm_input;
using namespace csl;
using namespace std;

namespace mty {

/**
 * @brief Standard Model of particle physics.
 */
class HNL_Model : public SM_Model {

protected:
    csl::Expr mN1;
    csl::Expr VmuN1;

  public:
    HNL_Model(bool initialize = true) : SM_Model(false) {
        if (initialize)
            init();
            refresh();
    }
    ~HNL_Model() override {}

    void init() {
        initContent();
        std::cout << "1" << std::endl;
        getToLowEnergyLagrangian();
        std::cout << "2" << std::endl;
    }


    void initContent() {
        SM_Model::initGauge();
        HNL_Model::initFermions();
        SM_Model::initHiggsPotential();
        SM_Model::initYukawas();
    }

    void initGauge();
    void initFermions() {
        Particle Q = weylfermion_s("Q", *this, Chirality::Left);
        Q->setGroupRep("C", {1, 0});
        Q->setGroupRep("L", 1);
        Q->setGroupRep("Y", {1, 6});
        Q->setFundamentalFlavorRep("SM_flavor");

        Particle U = weylfermion_s("U_R", *this, Chirality::Right);
        U->setGroupRep("C", {1, 0});
        U->setGroupRep("Y", {2, 3});
        U->setFundamentalFlavorRep("SM_flavor");

        Particle D = weylfermion_s("D_R", *this, Chirality::Right);
        D->setGroupRep("C", {1, 0});
        D->setGroupRep("Y", {-1, 3});
        D->setFundamentalFlavorRep("SM_flavor");

        Particle L = weylfermion_s("L", *this, Chirality::Left);
        L->setGroupRep("L", 1);
        L->setGroupRep("Y", {-1, 2});
        L->setFundamentalFlavorRep("SM_flavor");

        Particle E = weylfermion_s("E_R", *this, Chirality::Right);
        E->setGroupRep("Y", -1);
        E->setFundamentalFlavorRep("SM_flavor");
        
        Particle N = diracfermion_s("N", *this);
        N->setFundamentalFlavorRep("SM_flavor");

        addParticles({Q, U, D, L, E, N});
    }

    void getToLowEnergyLagrangian()
    {
        SM_Model::gaugeSymmetryBreaking();
        SM_Model::HiggsVEVExpansion();
        SM_Model::diagonalizeSMMassMatrices();

        SM_Model::replaceLeptonYukawa();
        SM_Model::replaceUpYukawa();
        SM_Model::replaceDownYukawa();
        SM_Model::flavorSymmetryBreaking();
        HNL_Model::add_interaction_N1();
        SM_Model::adjust();
    }

    void add_interaction_N1() {

        auto dirac =DiracIndices(2);
        csl::Tensor gamma = DiracGamma();
        csl::Index nu = MinkowskiIndex();
        auto mu_L = getParticle("mu_L");
        auto mu_R = getParticle("mu_R");
        auto N = getParticle("N_2");
        auto W = getParticle("W");
        auto Z = getParticle("Z");
        auto nu_mu = getParticle("nu_mu");
        auto s2 = sm_input::s2_theta_W;
        auto sW = csl::sqrt_s(s2);
        auto cW = csl::sqrt_s(1 - s2);
        
        std::cout << N->getFullSetOfIndices()[0].getName() << std::endl;
        VmuN1 = constant_s("VmuN1");
        // addLagrangianTerm( VmuN1 * sm_input::e_em / (csl::sqrt_s(2) * csl::sqrt_s(1-sm_input::s2_theta_W )) * W({nu}) * GetComplexConjugate(mu_L({dirac[0]})) * gamma({+nu, dirac[0], dirac[1]}) * N({dirac[1]}), true);

        // addLagrangianTerm( -VmuN1 * sm_input::e_em / (2 *csl::sqrt_s(sm_input::s2_theta_W)* csl::sqrt_s((1-sm_input::s2_theta_W ))) * Z({nu}) * (GetComplexConjugate(nu_mu({dirac[0]})) * gamma({+nu, dirac[0], dirac[1]}) * N({dirac[1]})+  GetComplexConjugate(N({dirac[0]})) * gamma({+nu, dirac[0], dirac[1]}) * GetComplexConjugate(nu_mu({dirac[1]}))));

        addLagrangianTerm(
            VmuN1 * sm_input::e_em / (csl::sqrt_s(2) * sW) *
            W({nu}) *
            GetComplexConjugate(mu_L({dirac[0]})) *
            gamma({+nu, dirac[0], dirac[1]}) *
            N({dirac[1]}),
            true
        );

        // Z – ν_μ – N
        addLagrangianTerm(
            - VmuN1 * sm_input::e_em / (2 * sW * cW) *
            Z({nu}) *
            GetComplexConjugate(nu_mu({dirac[0]})) *
            gamma({+nu, dirac[0], dirac[1]}) *
            N({dirac[1]}),
            true
        );

        mN1 = constant_s("mN1");

        addFermionicMass(N, mN1);
    }   
};


std::ostream &operator<<(std::ostream &out, HNL_Model const &model)
{
    return out << *static_cast<Model const *>(&model);
}


} // End of namespace mty


#endif
