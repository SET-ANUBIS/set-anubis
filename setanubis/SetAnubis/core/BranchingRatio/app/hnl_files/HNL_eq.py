import numpy as np
import scipy.integrate as integrate
import sys, os

sys.path.append(os.getcwd())
# from Pipeline.HNL.Equations.common_funcs import *
# from Pipeline.HNL.Equations.const_params import *
from setanubis.SetAnubis.core.BranchingRatio.app.hnl_files.Parameters import SimulationParameters
from SetAnubis.core.ModelCore.domain.QCDRunner import QCDRunner
from SetAnubis.core.BranchingRatio.domain.IDecayCalculation import IDecayCalculation

# ------- Functions

def xSqrt(x):
    return np.sqrt(1 - 4*x**2)

def lambda_func(a, b, c):
    # Kallen Function
    return a**2 + b**2 + c**2 - 2*(a*b + a*c + b*c)

def IFunc(x,xu,xd,xl):
    return (1/x)*(x-xl**2-xd**2)*(1+xu**2-x)*np.sqrt(lambda_func(x,xl**2,xd**2)*lambda_func(1,x,xu**2))

def Int_func(xu,xd,xl):
    return 12*integrate.quad(IFunc, (xd + xl)**2, (1- xu)**2, args=(xu,xd,xl))[0]

# For calculation of decay widths
def Lfunc(x):
    N1 = 1 - 3*x**2 - (1 - x**2) * xSqrt(x)
    D1 = x**2 * (1 + xSqrt(x))

    if (D1 == 0 or N1 <= 0):
        return 0
    else:
        return np.log(N1/D1)
    
# ------- Parameters



class DecayFunctions(IDecayCalculation):
    def __init__(self, MX=1, Ve=1, Vmu=1, Vtau=1):
        """
        Initialize the DecayFunctions class with given parameters.
        
        Parameters
        ----------
        MX : float
            Mass of the HNL.
        Ve : float
            Coupling constant for the electron.
        Vmu : float
            Coupling constant for the muon.
        Vtau : float
            Coupling constant for the tau.
        """
        self.params = SimulationParameters()
        self.qcd_runner = QCDRunner(1.184e-1, 91.1876, 172.9, 4.18, 2.01*10**-3, 4.79*10**-3, 110*10**-3, 1.2)
        
        self.C1fList = [ (1/4)*(1 - (8/3)*self.params.constants["sw2"] + (32/9)*self.params.constants["sw2"]**2), (1/4)*(1 - (4/3)*self.params.constants["sw2"] + (8/9)*self.params.constants["sw2"]**2), (1/4)*(1 - 4*self.params.constants["sw2"] +8*self.params.constants["sw2"]**2), (1/4)*(1 + 4*self.params.constants["sw2"] + 8*self.params.constants["sw2"]**2) ]
        self.C2fList = [ (1/3)*self.params.constants["sw2"]*((4/3)*self.params.constants["sw2"] - 1), (1/6)*self.params.constants["sw2"]*((2/3)*self.params.constants["sw2"] - 1), (1/2)*self.params.constants["sw2"]*(2*self.params.constants["sw2"] - 1), (1/2)*self.params.constants["sw2"]*(2*self.params.constants["sw2"] + 1) ]

        self.couplings = {11 : Ve, 13 : Vmu, 15 : Vtau}
        self.MX = MX
        self.hnl_type = 2
        self.first = [11, 12]
        self.second = [13,14]
        self.third = [15,16]

        self.quark_u = {2:self.params.get_parameter(2, "mass"), 4:self.params.get_parameter(4, "mass"), 6:self.params.get_parameter(6, "mass")}
        self.quark_d = {1:self.params.get_parameter(1, "mass"), 3:self.params.get_parameter(3, "mass"), 5:self.params.get_parameter(5, "mass")}
        self.lep = {2:self.params.get_parameter(11, "mass"), 4:self.params.get_parameter(13, "mass"), 6:self.params.get_parameter(15, "mass")}
        
    def set_MX(self, MX):
        """
        Set the mass of the HNL.
        
        Parameters
        ----------
        MX : float
            Mass of the HNL.
        """
        self.MX = MX
        
    def set_couplings(self, Ve, Vmu, Vtau):
        """
        Set the coupling constants for the HNL.
        
        Parameters
        ----------
        Ve : float
            Coupling constant for the electron.
        Vmu : float
            Coupling constant for the muon.
        Vtau : float
            Coupling constant for the tau.
        """
        self.couplings = {11 : Ve, 13 : Vmu, 15 : Vtau}
        
    def set_one_coupling(self, param, value):
        if param == "Ve":
            self.couplings[11] = value
        elif param == "Vmu":
            self.couplings[13] = value
        elif param == "Vta":
            self.couplings[15] = value
        else:
            raise "Not a coupling that exist"
        
    def set_hnl_type(self, hnl_type):
        """
        Set the type of the HNL.
        
        Parameters
        ----------
        hnl_type : int
            Type of the HNL (Dirac, Majorama).
        """
        self.hnl_type = hnl_type
        
    def get_MX(self):
        """
        Get the mass of the HNL.
        
        Returns
        -------
        float
            Mass of the HNL.
        """
        return self.MX
    
    def get_couplings(self):
        """
        Get the coupling constants of the HNL.
        
        Returns
        -------
        dict
            Coupling constants for the electron, muon, and tau.
        """
        return self.couplings
    
    def get_hnl_type(self):
        """
        Get the type of the HNL.
        
        Returns
        -------
        int
            Type of the HNL (Majorama, Dirac).
        """
        return self.hnl_type
    
    def is_approximately_equal(self, val1, val2, tolerance):
        """
        Check if two values are approximately equal within a given tolerance.
        
        Parameters
        ----------
        val1 : float
            First value.
        val2 : float
            Second value.
        tolerance : float
            Tolerance for comparison.
        
        Returns
        -------
        bool
            True if values are approximately equal, False otherwise.
        """
        return abs(val1-val2) <= tolerance * val1
    
    def Get_Channel_Type(self, particles):
        """
        Determine the channel type based on the provided particles.

        Parameters
        ----------
        particles : list
            List of particle IDs.

        Returns
        -------
        str
            Channel type ('leptonic', 'meson_v', 'meson_lep', 'hadronic', 'invisible', 'three_body', or 'unknown').
        """
        return_particles = {}
        if len(particles) == 3:
            # Check for leptonic decays lAUD
            leptons = [p for p in particles if abs(p) in self.params.leplist]
            neutrinos = [p for p in particles if abs(p) in self.params.nulist]
            quarks = [p for p in particles if abs(p) in self.params.quarklist]
            nus = [p for p in particles if abs(p) in self.params.nulist]
            if len(leptons) == 1 and len(quarks) == 2:
                quarks_u = [p for p in quarks if abs(p) in [2,4,6]]
                quarks_d = [p for p in quarks if abs(p) in [1,3,5]]
                return_particles["quarks_u"] = quarks_u
                return_particles["quarks_d"] = quarks_d
                return_particles["leptons"] = leptons
                if abs(quarks[0]) != abs(quarks[1]):
                    return 'lAUD_q', return_particles
                else:
                    return "vAff_q", return_particles
            elif len(leptons) == 2 and len(neutrinos) == 1 and abs(leptons[0]) != abs(leptons[1]):
                if abs(leptons[0])+1 == neutrinos[0]:
                    return_particles["leptons"] = [leptons[1], leptons[0]]
                    return_particles["nus"] = nus
                elif abs(leptons[1])+1 == neutrinos[0]:
                    return_particles["leptons"] = leptons
                    return_particles["nus"] = nus
                return 'lAUD_l', return_particles
            if len(leptons) == 2 and len(neutrinos) == 1 and abs(leptons[0]) == abs(leptons[1]):
                return 'vAff', return_particles
            if abs(particles[0]) in self.params.nulist and abs(particles[1]) in self.params.nulist and abs(particles[2]) in self.params.nulist:
                return 'invisible', return_particles
        elif len(particles) == 2:
            leptons = [p for p in particles if abs(p) in self.params.leplist]
            PseMes = [p for p in particles if abs(p) in self.params.PseMesList]
            VecMes = [p for p in particles if abs(p) in self.params.VecMesList]
            PseMes0 = [p for p in particles if abs(p) in self.params.PseMes0List]
            VecMes0 = [p for p in particles if abs(p) in self.params.VecMes0List]
            nus = [p for p in particles if abs(p) in self.params.nulist]
            if len(leptons) == 1:
                return_particles["leptons"] = leptons
                if len(PseMes) == 1:
                    return_particles["PseMes"] = PseMes
                    return 'lAhP', return_particles
                elif len(VecMes) == 1:
                    return_particles["VecMes"] = VecMes
                    return 'lAhV', return_particles
            if len(nus) == 1:
                return_particles["nus"] = nus
                if len(PseMes0) ==1:
                    return_particles["PseMes0"] = PseMes0
                    return "vAhP", return_particles
                elif len(VecMes0) == 1:
                    return_particles["VecMes0"] = VecMes0
                    return "vAhV", return_particles
            # if abs(particles[0]) in self.params.VecMesList + self.params.VecMes0List and abs(particles[1]) in self.params.leplist:
            #     return 'lAhV' if abs(particles[0]) in self.params.VecMesList else 'vAhV'
            if abs(particles[0]) in self.params.leplist and abs(particles[1]) in self.params.leplist:
                return 'vff', return_particles
        elif len(particles) == 1:
            if abs(particles[0]) in self.params.PseMes0List:
                return 'vhP', return_particles
            if abs(particles[0]) in self.params.VecMes0List:
                return 'vhV', return_particles

        return 'unknown', return_particles

    def calculate(self, mother, particles, params):
        """
        Get the decay width for a given channel based on the particles provided.

        Parameters
        ----------
        particles : list
            List of particle IDs.

        Returns
        -------
        float
            Decay width for the specified channel.
        """
        self.MX = float(params["mN1"]["value"].real)
        self.couplings = {11 : float(params["VeN1"]["value"].real), 13 : float(params["VmuN1"]["value"].real), 15 : float(params["VtaN1"]["value"].real)}
        charge_sum = sum([1 if p > 0 else -1 for p in particles if abs(p) in self.params.leplist + self.params.quarklist+self.params.nulist])
        if charge_sum != 1:
            raise ValueError("The difference between the number of positive and negative charges must be one.")
        
        channel_type, particle_dict = self.Get_Channel_Type(particles)
        if channel_type == 'lAUD_l':
            return self.lAUD(self.params.get_parameter(particle_dict["leptons"][0], "mass"),self.couplings[abs(particle_dict["leptons"][0])], 0, self.params.get_parameter(abs(particle_dict["leptons"][1]), "mass"), 0)
        elif channel_type =="lAUD_q":
            quark_u_index = [2, 4, 6].index(abs(particle_dict["quarks_u"][0]))
            quark_d_index = [1, 3, 5].index(abs(particle_dict["quarks_d"][0]))
            return self.lAUD(self.params.get_parameter(particle_dict["leptons"][0], "mass"), self.couplings[abs(particle_dict["leptons"][0])], self.params.get_parameter(particle_dict["quarks_u"][0], "mass"), self.params.get_parameter(particle_dict["quarks_d"][0], "mass"), self.params.CKM_matrix[quark_u_index][quark_d_index])

        elif channel_type == "vAff":
            leptons = [p for p in particles if abs(p) in self.params.leplist]
            neutrino = [p for p in particles if abs(p) in self.params.nulist]
            if abs(neutrino[0]) == abs(leptons[0])+1:
                return self.couplings[neutrino[0]-1]**2*self.vAff(self.params.get_parameter(abs(leptons[0]), "mass"), 1)
            else:
                return self.couplings[neutrino[0]-1]**2*self.vAff(self.params.get_parameter(abs(leptons[0]), "mass"), 0)
        elif channel_type == 'lAhP':
            lep = next(p for p in particles if abs(p) in self.params.leplist)
            meson = next(p for p in particles if abs(p) in self.params.PseMesList)
            return self.lAhP(self.params.get_parameter(abs(lep), "mass"), self.params.get_parameter(abs(meson), "mass"), self.params.get_parameter(abs(meson), "mDecays"), self.params.get_parameter(abs(meson), "CKM"), self.couplings[abs(lep)])

        elif channel_type == 'vAhP':
            meson = [p for p in particles if abs(p) in self.params.PseMes0List]
            # print(meson, self.params.get_parameter(abs(meson[0]), "mass"), self.params.get_parameter(abs(meson[0]), "mDecays"))
            lep = [p for p in particles if abs(p) not in self.params.PseMes0List]
            if lep[0] in self.first:
                return self.couplings[11]**2*self.vAhP(self.params.get_parameter(abs(meson[0]), "mass"), self.params.get_parameter(abs(meson[0]), "mDecays"))
            elif lep[0] in self.second:
                return self.couplings[13]**2*self.vAhP(self.params.get_parameter(abs(meson[0]), "mass"), self.params.get_parameter(abs(meson[0]), "mDecays"))
            else:
                return self.couplings[15]**2*self.vAhP(self.params.get_parameter(abs(meson[0]), "mass"), self.params.get_parameter(abs(meson[0]), "mDecays"))
            
        elif channel_type == 'lAhV':
            lep = next(p for p in particles if abs(p) in self.params.leplist)
            meson = [p for p in particles if abs(p) in self.params.VecMesList][0]
            return self.lAhV(self.params.get_parameter(abs(lep), "mass"), self.params.get_parameter(abs(meson), "mass"), self.params.get_parameter(abs(meson), "gh"), self.params.get_parameter(abs(meson), "CKM"), self.couplings[abs(lep)])

        elif channel_type == 'vAhV':
            meson = [p for p in particles if abs(p) in self.params.VecMes0List][0]
            
            lep = [p for p in particles if abs(p) not in self.params.VecMes0List]
            if lep[0] in self.first:
                return self.couplings[11]**2*self.vAhV(self.params.get_parameter(abs(meson), "mass"), self.params.get_parameter(abs(meson), "Kappah"), self.params.get_parameter(abs(meson), "gh"))
            elif lep[0] in self.second:
                return self.couplings[13]**2*self.vAhV(self.params.get_parameter(abs(meson), "mass"), self.params.get_parameter(abs(meson), "Kappah"), self.params.get_parameter(abs(meson), "gh"))
            else:
                return self.couplings[15]**2*self.vAhV(self.params.get_parameter(abs(meson), "mass"), self.params.get_parameter(abs(meson), "Kappah"), self.params.get_parameter(abs(meson), "gh"))
            

        # elif channel_type == 'vff':
        #     lep1 = abs(particles[0])
        #     lep2 = abs(particles[1])
        #     if lep1 != lep2:
        #         raise ValueError("For vff decay, both particles must be the same fermion.")
        #     return self.vff(self.params.get_parameter(lep1, "mass"))

        # elif channel_type == 'vhP':
        #     meson = particles[0]
        #     return self.vhP(self.params.get_parameter(abs(meson), "mass"), self.params.get_parameter(abs(meson), "mDecays"))

        # elif channel_type == 'vhV':
        #     meson = particles[0]
        #     return self.vhV(self.params.get_parameter(abs(meson), "mass"), self.params.get_parameter(abs(meson), "Kappah"), self.params.get_parameter(abs(meson), "gh"))

        elif channel_type == 'invisible':
            return self.Nus()

        else:
            return 0   
    # ------- Leptonic
    def dec_lep(self):
        """
        Compute decay widths for HNL decaying into lepton pairs.
        
        Returns
        -------
        float
            Decay width for leptonic decays.
        """
        dec_out = 0
        for lep_i in self.params.leplist:
            
            Vl = self.couplings[lep_i]
            
            for lep_j in self.params.leplist:
                Vij = 0 # only for quarks

                MUp = 0 # for neutrino
                dec_out += self.lAUD(self.params.get_parameter(lep_i, "mass"),Vl,MUp,self.params.get_parameter(lep_j, "mass"),Vij)
            dec_out += self.vff(self.params.get_parameter(lep_i, "mass"))

        return dec_out
    
    # ------- Invisible
    def dec_invis(self):
        """
        Compute decay widths for HNL decaying into neutrinos.
        
        Returns
        -------
        float
            Decay width for invisible decays.
        """
        return self.Nus()

    # ------- Mesons
    # Sum over final states with neutrino
    def dec_meson_v(self):
        """
        Compute decay widths for HNL decaying into mesons with neutrino final states.
        
        Returns
        -------
        float
            Decay width for meson decays with neutrino final states.
        """
        dec_out = 0

        # Neutral Pseudo-Scalars
        for PseMes0 in self.params.PseMes0List:
            dec_out += self.vhP(self.params.get_parameter(PseMes0, "mass"), self.params.get_parameter(PseMes0, "mDecays"))
            
        for VecMes0 in self.params.VecMes0List:
            dec_out += self.vhV(self.params.get_parameter(VecMes0, "mass"), self.params.get_parameter(VecMes0, "Kappah"), self.params.get_parameter(VecMes0, "gh"))

        return dec_out


    # Sum over lepton final states
    def dec_meson_lep(self):
        """
        Compute decay widths for HNL decaying into mesons with lepton final states.
        
        Returns
        -------
        float
            Decay width for meson decays with lepton final states.
        """
        dec_out = 0

        for PseMes in self.params.PseMesList:
            for lep in self.params.leplist:
                VA = self.couplings[lep]          
                dec_out += self.lAhP(self.params.get_parameter(lep, "mass"), self.params.get_parameter(PseMes, "mass"), self.params.get_parameter(PseMes, "mDecays"), self.params.get_parameter(PseMes, "CKM"), VA)
                
        for VecMes in self.params.VecMesList:
            for lep in self.params.leplist:
                VA = self.couplings[lep]
                        
                dec_out += self.lAhV(self.params.get_parameter(lep, "mass"), self.params.get_parameter(VecMes, "mass"), self.params.get_parameter(VecMes, "gh"), self.params.get_parameter(VecMes, "CKM"), VA)
                
                
        return dec_out

    def QCDcorr(self):
        """
        Calculate QCD corrections.
        
        Returns
        -------
        float
            QCD correction factor.
        """
        # options: aSrun(MX), aSrun_1(MX), alpha_vals[ix]
        # ix = np.where(np.round(MX,1) == m_vals)[0][0]
        # aS_val = alpha_vals[ix]
        aS_val = self.qcd_runner.alpha_s(self.MX)
        return (aS_val/self.params.constants["pi"]) + 5.2*(aS_val/self.params.constants["pi"])**2 + 26.4*(aS_val/self.params.constants["pi"])**3

    def vTotHad(self):
        """
        Compute total hadronic decay widths considering QCD corrections.
        
        Returns
        -------
        float
            Total hadronic decay width.
        """
        dec_out = 0
        M_test = [321, 411, 521]
        for i, quark in enumerate(self.params.quarklist):
            if quark == 6:
                continue
            if quark == 1 or quark == 2:
                dec_out+= self.vff(self.params.get_parameter(quark, "mass"))
            else:
                if self.MX >= 2*self.params.get_parameter(M_test[i-2], "mass"):
                    dec_out += np.sqrt(1-4*(self.params.get_parameter(M_test[i-2], "mass")**2)/(self.MX**2))*self.vff(self.params.get_parameter(quark, "mass"))


        return (1+self.QCDcorr())*dec_out

    def vHad(self):
        """
        Compute hadronic decay widths excluding meson/neutrino decays.
        
        Returns
        -------
        float
            Hadronic decay width excluding meson decays.
        """
        if self.MX > 1:#2*mMasses["mPion"]:
            return (self.vTotHad() - self.dec_meson_v())
        else:
            return 0
    
    def lHad(self):
        """
        Compute leptonic decay widths excluding meson/lepton decays.
        
        Returns
        -------
        float
            Leptonic decay width excluding meson decays.
        """
        if self.MX > 1:#2*mMasses["mPion"]:
            return (self.lTotHad() - self.dec_meson_lep())
        else:
            return 0
    
    def lTotHad(self):
        """
        Compute total semi-leptonic decay widths considering QCD corrections.
        
        Returns
        -------
        float
            Total leptonic decay width.
        """
        dec_out = 0

        for lep in self.params.leplist:
            Vl = self.couplings[lep]
            for i,quark_u in enumerate(self.quark_u.keys()):
                for j,quark_d in enumerate(self.quark_d.keys()):
                    Vij = self.params.CKM_matrix[i][j]    
            
                    dec_out += self.lAUD(self.params.get_parameter(lep, "mass"), Vl, self.params.get_parameter(quark_u, "mass"), self.params.get_parameter(quark_d, "mass"), Vij)


        return (1+self.QCDcorr())*dec_out

    def dec_quark_l(self):
        dec_out = 0
        
        for lep in self.params.leplist:
            Vl = self.couplings[lep]
            for quark_u,quark_u_mass in self.quark_u.items():
                for quark_d, quark_d_mass in self.quark_d.items():
                    Vij = self.params.CKM_matrix[int(quark_u/2-1)][int((quark_d-1)/2)]
                    dec_out += self.lAUD(self.params.get_parameter(lep, "mass"), Vl, quark_u_mass, quark_d_mass, Vij)
                    
        return dec_out
    
    def dec_quark_v(self):
        dec_out = 0
        
        for quark in self.params.quarklist:
            dec_out += self.vff(self.params.get_parameter(quark, "mass"))
            
        return dec_out
    
    def dec_quark(self):
        return self.dec_quark_l() + self.dec_quark_v()
                    
    # Charged Current-Mediated Decays
    # lA nuB lB & lA U D-bar (neutrino and fermion pair, ferimons different)
    def lAUD(self,Ml,Vl,MUp,MDown,Vij):
        """
        Compute decay widths for HNL decaying into a lepton, up-type quark, and down-type quark.
        
        Parameters
        ----------
        Ml : float
            Mass of the lepton.
        Vl : float
            Coupling constant of the lepton.
        MUp : float
            Mass of the up-type quark.
        MDown : float
            Mass of the down-type quark.
        Vij : float
            CKM matrix element.
        
        Returns
        -------
        float
            Decay width for the specified decay channel.
        """ 
        if self.MX >= (Ml + MUp + MDown):
            P1 = (self.params.constants["G_F"]**2*self.MX**5)/(192*self.params.constants["pi"]**3) 
            P2 = Int_func(MUp/self.MX, MDown/self.MX, Ml/self.MX)
            if (MUp in self.quark_u.values()) and (MDown in self.quark_d.values()): # quarks
                NW = 3*np.abs(Vij)**2 #Nc = 3 for quarks
            elif (MUp ==0 ) and (MDown in self.lep.values()): # leptons
                NW = 1
            else: #otherwise
                NW = 0
            return self.hnl_type * (NW * P1 * np.abs(Vl)**2 * P2)
        else:
            return 0
        
    # Neutral Current-Mediates Decays
    # neutrino and fermion pair (same fermions)
    def vAff(self,Mf,Vi):
        """
        Compute decay widths for HNL decaying into a neutrino and a fermion pair (same fermions).
        
        Parameters
        ----------
        Mf : float
            Mass of the fermion.
        Vi : int
            Indicator for neutrino and lepton flavor match.
        
        Returns
        -------
        float
            Decay width for the specified decay channel.
        """
        if self.MX >= 2*Mf:
            xf = Mf/self.MX
            P1 = (self.params.constants["G_F"]**2*self.MX**5)/(192*self.params.constants["pi"]**3)

            ix = 10 # will cause error for wrong mass
            if (Mf in self.quark_u.values()):
                ix = 0
            elif (Mf in self.quark_d.values()):
                ix = 1
            elif (Mf in self.lep.values()):
                if ( Vi == 1 ): # same neutrino and lepton flavour
                    ix = 3
                    
                else:
                    ix = 2
                    

            if ix == 10:
                return 0
            else:
                C1f = self.C1fList[ix]
                C2f = self.C2fList[ix]

            P2 = (
                C1f * ( (1- 14*xf**2 - 2*xf**4 - 12*xf**6)*np.sqrt(1-4*xf**2)
                    + 12*xf**4 * (xf**4 - 1) *Lfunc(xf))
                + 4*C2f *(xf**2 * (2+ 10*xf**2 - 12*xf**4)*xSqrt(xf)
                        + 6*xf**4 * (1 - 2*xf**2 + 2*xf**4)*Lfunc(xf))       
                )

            if (Mf in (list(self.quark_d.values()) + list(self.quark_u.values()))): # quarks
                NZ = 3 #Nc = 3 for quarks
            elif (Mf in self.lep.values()): # leptons
                NZ = 1
            else: #otherwise
                NZ = 0
            return NZ * P1 * P2
        
        else:
            return 0

    def vff(self,Mf):
        """
        Compute decay widths for HNL decaying into a neutrino and fermion pairs (all lepton flavors).
        
        Parameters
        ----------
        Mf : float
            Mass of the fermion.
        
        Returns
        -------
        float
            Total decay width for neutrino and fermion pair decays.
        """
        outRes = 0

        for VA in self.couplings.keys():
            # VAval = VvalList[self.Vlist.index(VA)]
            Vi = 0
            # if lepton, difference to whether neutrino match the lepton flavour
            if (Mf in self.lep.values()):
                ix = np.where(np.round(list(self.lep.values()),6) == np.round(Mf,6))[0][0]
                VB = list(self.couplings)[ix]
                if VA == VB:
                    Vi = 1

            outRes += np.abs(self.couplings[VA])**2 *self.vAff(Mf,Vi)

        return outRes

    def lHad_indi(self,Ml,Vl):
        """
        Compute individual hadronic decay widths for a given lepton mass and coupling.
        
        Parameters
        ----------
        Ml : float
            Mass of the lepton.
        Vl : float
            Coupling constant of the lepton.
        
        Returns
        -------
        float
            Individual hadronic decay width.
        """
        if self.MX > 1: #2*mMasses["mPion"]:
            dec_out = 0

            for j, q_u in enumerate(self.quark_u.values()):
                for k, q_d in enumerate(self.quark_d.values()):
                    Vij = self.params.CKM_matrix[j][k]


                    dec_out += self.lAUD(Ml,Vl,q_u,q_d,Vij)

            for PseMes in self.params.PseMesList:
                dec_out -= self.lAhP(Ml, self.params.get_parameter(PseMes, "mass"), self.params.get_parameter(PseMes, "mDecays"), self.params(PseMes, "CKM"), Vl)
            for VecMes in self.params.VecMesList:
                dec_out-= self.lAhV(Ml, self.params.get_parameter(VecMes, "mass"), self.params.get_parameter(VecMes, "gh"), self.params.get_parameter(VecMes, "CKM"), Vl)


            return dec_out
        else:
            return 0
        
    # Three neutrinos
    def Nus(self):
        """
        Compute decay widths for HNL decaying into three neutrinos.
        
        Returns
        -------
        float
            Decay width for three neutrino decays.
        """
        # (1 + dirac_delta(A,B)) summed over 3, where one is 2 => 1 + 1 + 2 = 4
        P1 = (self.params.constants["G_F"]**2)/(192*self.params.constants["pi"]**3)
        P2 = self.MX**5

        return self.hnl_type * P1 * (np.abs(self.couplings[11])**2 + np.abs(self.couplings[13])**2 + np.abs(self.couplings[15])**2) * P2

    # ---- Two Body
    # Charged Pseudo-Scalar
    def lAhP(self, Ml, Mh, fh, Vud, VA):
        """
        Compute decay widths for HNL decaying into charged pseudoscalar mesons and leptons.
        
        Parameters
        ----------
        Ml : float
            Mass of the lepton.
        Mh : float
            Mass of the meson.
        fh : float
            Decay constant of the meson.
        Vud : float
            CKM matrix element.
        VA : float
            Coupling constant of the lepton.
        
        Returns
        -------
        float
            Decay width for the specified decay channel.
        """
        if self.MX >= Ml + Mh:
            xl = Ml/self.MX
            xh = Mh/self.MX

            P1 = (self.params.constants["G_F"]**2 *fh**2 * np.abs(Vud)**2)/(16*self.params.constants["pi"])
            P2 = self.MX**3 * ( (1-xl**2)**2 - xh**2*(1+xl**2) )*np.sqrt(lambda_func(1,xh**2,xl**2))

            return self.hnl_type * np.abs(VA)**2 * P1 * P2
        else:
            return 0

    # Neutral Pseudo-Scalar
    def vAhP(self, Mh, fh):
        """
        Compute decay widths for HNL decaying into neutral pseudoscalar mesons.
        
        Parameters
        ----------
        Mh : float
            Mass of the meson.
        fh : float
            Decay constant of the meson.
        
        Returns
        -------
        float
            Decay width for the specified decay channel.
        """
        xh = Mh/self.MX

        P1 = (self.params.constants["G_F"]**2 *fh**2)/(32*self.params.constants["pi"])
        P2 = self.MX**3 * (1- xh**2)**2

        return P1 * P2

    def vhP(self, Mh, fh):
        """
        Compute decay widths for HNL decaying into neutral pseudoscalar mesons considering all lepton flavors.
        
        Parameters
        ----------
        Mh : float
            Mass of the meson.
        fh : float
            Decay constant of the meson.
        
        Returns
        -------
        float
            Total decay width for neutral pseudoscalar meson decays.
        """
        if self.MX >= Mh:
            out_val = (np.abs(self.couplings[11])**2 * self.vAhP(Mh, fh) 
                + np.abs(self.couplings[13])**2 * self.vAhP(Mh, fh) 
                + np.abs(self.couplings[15])**2 * self.vAhP(Mh, fh))
            return out_val
        else:
            return 0

    # Charged Vector
    def lAhV(self, Ml, Mh, gh, Vud, VA):
        """
        Compute decay widths for HNL decaying into charged vector mesons and leptons.
        
        Parameters
        ----------
        Ml : float
            Mass of the lepton.
        Mh : float
            Mass of the meson.
        gh : float
            Decay constant of the meson.
        Vud : float
            CKM matrix element.
        VA : float
            Coupling constant of the lepton.
        
        Returns
        -------
        float
            Decay width for the specified decay channel.
        """

        if self.MX >= Ml + Mh:
            xl = Ml/self.MX
            xh = Mh/self.MX

            P1 = (self.params.constants["G_F"]**2 *gh**2 * np.abs(Vud)**2)/(16*self.params.constants["pi"] * Mh**2)
            P2 = self.MX**3 * ( (1-xl**2)**2 + xh**2*(1+xl**2) -2*xh**4 )*np.sqrt(lambda_func(1,xh**2,xl**2))

            return self.hnl_type * np.abs(VA)**2 * P1 * P2
        else:
            return 0

    # Neutral Vector
    def vAhV(self, Mh, kh, gh):
        """
        Compute decay widths for HNL decaying into neutral vector mesons.
        
        Parameters
        ----------
        Mh : float
            Mass of the meson.
        kh : float
            Decay constant of the meson.
        gh : float
            Coupling constant of the meson.
        
        Returns
        -------
        float
            Decay width for the specified decay channel.
        """
        xh = Mh/self.MX

        P1 = (self.params.constants["G_F"]**2 * kh**2 *gh**2)/(32*self.params.constants["pi"] + Mh**2)
        P2 = self.MX**3 * (1 + 2*xh**2) * (1- xh**2)**2

        return P1 * P2

    def vhV(self, Mh, kh, gh):
        """
        Compute decay widths for HNL decaying into neutral vector mesons considering all lepton flavors.
        
        Parameters
        ----------
        Mh : float
            Mass of the meson.
        kh : float
            Decay constant of the meson.
        gh : float
            Coupling constant of the meson.
        
        Returns
        -------
        float
            Total decay width for neutral vector meson decays.
        """
        if self.MX >= Mh:
            out_val = (np.abs(self.couplings[11])**2 * self.vAhV(Mh, kh, gh) 
                + np.abs(self.couplings[13])**2 * self.vAhV(Mh, kh, gh) 
                + np.abs(self.couplings[15])**2 * self.vAhV(Mh, kh, gh))
            return out_val
        else:
            return 0
        
    # ------- Total
    def dec_tot(self):
        """
        Compute the total decay width for the HNL by summing all possible decay channels.
        
        Returns
        -------
        float
            Total decay width of the HNL.
        """
        return ( 
            self.dec_invis()
            + self.dec_meson_v()
            + self.dec_meson_lep()
            + self.dec_lep()
            + self.vHad()
            + self.lHad()
        )
        
# ------- Pheno equations
# from 1805.08567

# np.heaviside(MX - Ml - Mh,1) make this into a function

# ---- Three Body


if __name__ == "__main__":
    # Example parameters
    MX = 1.0
    Ve = 1
    Vmu = 1
    Vtau = 1

    # Create an instance of the DecayFunctions class
    decay_functions = DecayFunctions(MX, Ve, Vmu, Vtau)

    # Test particles
    test_cases = [
        ([12, 11, -11], "vAff"),  # Lepton + Same lepton + neutrino,
        ([16, 11, -11], "vAff"),  # Lepton + Same lepton + neutrino,
        ([12, 13, -11], "lAUD_l"),  # Lepton + Same lepton + neutrino,
        ([11, 2, -1], "lAUD_q"),  # Lepton + Up quark + Down quark
        ([11, 1, -2], "lAUD_q"),  # Lepton + Up quark + Down quark
        ([13, 211], "lAhP"),   # Lepton + Charged pseudoscalar meson
        ([14, -14, 14], "invisible"),  # Neutrino + Neutrino (invisible decay)
        ([221, 12], "vAhP"),        # Neutral pseudoscalar meson
        ([213, 11], "lAhV"),   # Lepton + Charged vector meson
        ([223, 12], "vAhV"),        # Neutral vector meson
    ]

    for particles, expected in test_cases:
        try:
            channel_type, particle_dict = decay_functions.Get_Channel_Type(particles)
            decay_width = decay_functions.calculate(9900012,particles)
            print(f"Particles: {particles}, Expected Channel: {expected}, Detected Channel: {channel_type}, Decay Width: {decay_width}")
        except:
            print(particles)
            print(decay_functions.Get_Channel_Type(particles))



if __name__ == "__main__":
    liste_br = []
    liste_br_muon = []
    liste_br_elec = []
    liste_br_both = []
    liste_tot_br = []
    liste_invis = []
    typee = "meson"
    import numpy as np
    import matplotlib.pyplot as plt

    if typee == "tot":
        decay_functions.set_couplings(10**(-8), 0, 0)
        for mx in np.logspace(-1,1):
            decay_functions.set_MX(mx)
            liste_tot_br.append(1/decay_functions.dec_tot())

        plt.plot(np.logspace(-1,1), liste_tot_br)
        plt.xscale("log")
        plt.yscale("log")
        plt.legend()
        plt.show()

    if typee == "lepton":
        decay_functions.set_couplings(52,1,1)
        x_vals = np.arange(0.005, 2,0.01)
    
        for mx in x_vals:
            decay_functions.set_MX(mx)
            dec_muon = (decay_functions.calculate(9900012,[12,13,-13])+decay_functions.calculate(9900012,[14,13,-13])+decay_functions.calculate(9900012,[16,13,-13]))/(decay_functions.dec_invis()+decay_functions.dec_lep()+decay_functions.dec_quark())
            dec_elec = (decay_functions.calculate(9900012,[12,11,-11])+decay_functions.calculate(9900012,[14,11,-11])+decay_functions.calculate(9900012,[16,11,-11]))/(decay_functions.dec_invis()+decay_functions.dec_lep()+decay_functions.dec_quark())
            dec_both = decay_functions.calculate(9900012,[14,11,-13])/(decay_functions.dec_invis()+decay_functions.dec_lep()+decay_functions.dec_quark())
            liste_br_muon.append(dec_muon)
            liste_br_elec.append(dec_elec)
            liste_br_both.append(dec_both)
            liste_br.append(dec_muon)
        plt.plot(x_vals, liste_br)
        plt.plot(x_vals, liste_br_muon, label="muon")
        plt.plot(x_vals, liste_br_both, label = "both")
        plt.plot(x_vals, liste_br_elec, label = "elec")
        plt.yscale("log")
        plt.legend()
        plt.xticks([0,0.5,1,1.5,2])
        plt.ylim(0.00001,1)
        # plt.ylim([0.1,1])
        plt.show()
        
    if typee == "meson":
        decay_functions.set_couplings(0.0001,0,0)
        x_vals = np.arange(0.2, 2,0.01)
    
        for mx in x_vals:
            decay_functions.set_MX(mx)
            gamma = decay_functions.calculate(9900012,[333,12])
            decay_tot = decay_functions.dec_tot()
            dec_both = gamma/(decay_tot)
            print(dec_both, gamma, decay_tot)
            liste_br_both.append(dec_both)
            # liste_br.append(dec_muon)
        # plt.plot(x_vals, liste_br)
        # plt.plot(x_vals, liste_br_muon, label="muon")
        plt.plot(x_vals, liste_br_both, label = "both")
        # plt.plot(x_vals, liste_br_elec, label = "elec")
        plt.yscale("log")
        plt.legend()
        plt.xticks([0,0.5,1,1.5,2])
        plt.ylim(0.00001,1)
        # plt.ylim([0.1,1])
        plt.show()

    if typee == "invisible":
        decay_functions.set_couplings(1,0,0)
        x_vals = np.logspace(-1,1)
        
        for mx in x_vals:
            decay_functions.set_MX(mx)
            liste_invis.append(decay_functions.calculate(9900012,[12,12,-12])/decay_functions.dec_tot())
            
        plt.plot(x_vals, liste_invis)
        plt.ylim(10**(-2), 1)
        plt.xscale("log")
        plt.yscale("log")
        plt.show()
# ---- Total Hadronic
# MX > 2*mPion





# ------- Decay Widths ---------







# ---- Multi-Hadron Final States
# MX > 2*mPion


    

    


