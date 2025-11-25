# from const_utils import Particle
# from particle import ParticleConfig
import math
import os, sys
# import shipunit as u
import yaml
import numpy as np
from scipy.integrate import quad, dblquad

pi0mass    = 0.1349770
etamass    = 0.547862
omegamass  = 0.78265
eta1mass   = 0.95778
# proton mass
mProton = 0.938272081 # GeV/c - PDG2016
protonEnergy = 13000. # GeV/c
protonMomentum = math.sqrt(protonEnergy*protonEnergy - mProton*mProton)


# class DarkPhotonConfig(ParticleConfig):
#     def __init__(self, params):
#         self.params = params
#         self.config_lines =  []
#         self.pdg = ROOT.TDatabasePDG.Instance()
#         self.particle = Particle()
#         if self.params['process_selection'] == 'qcd':
#             self.DPid = 4900023
#         else:
#             self.DPid = 9900015
#         self.particle = Particle()
#     def generate_config(self):
#         mass, couplings, process_selection= self.params['mass'], self.params['couplings'], self.params['process_selection']
#         epsilon, motherMode = self.params['epsilon'], self.params['mothermode']
        
        
#         if process_selection=="meson":
            
#         #     # Configuring production
#             self.config_lines.append("SoftQCD:nonDiffractive = on\n")

#         if process_selection=="qcd":
#             ##Set fy to Ktrue
#             # P8gen.SetDY()
#             # P8gen.SetMinDPMass(0.7)
#             MinDPMass = 0.7
#             if (mass<MinDPMass): 
#                 print("WARNING! Mass is too small, minimum is set to %3.3f GeV."%MinDPMass)
#                 return 0

#             self.config_lines.append("HiddenValley:ffbar2Zv = on\n")
#             self.config_lines.append("HiddenValley:Ngauge = 1\n")

#         elif process_selection=="pbrem":
#             self.config_lines.append("ProcessLevel:all = off\n")
#             #Also allow resonance decays, with showers in them
#             #P8gen.SetParameters("Standalone:allowResDec = on")

#             #Optionally switch off decays.
#             #P8gen.SetParameters("HadronLevel:Decay = off")

#             #Switch off automatic event listing in favour of manual.
#             self.config_lines.append("Next:numberShowInfo = 0\n")
#             self.config_lines.append("Next:numberShowProcess = 0\n")
#             self.config_lines.append("Next:numberShowEvent = 0\n")
#             # proton_bremsstrahlung.protonEnergy=13000
#             norm=prodRate(mass, epsilon)
#             print("A' production rate per p.o.t: \t %.8g"%norm)
            
#             #SetPbrem was doing this in https://snd-lhc.github.io/sndsw/DPPythia8Generator_8h_source.html
#             # fpbrem = kTRUE;
#             # fpbremPDF = pdf;
#             # P8gen.SetPbrem(proton_bremsstrahlung.hProdPDF(mass, epsilon, norm, 350, 1500))

#         #Define dark photon
#         DP_instance = DarkPhoton(mass,epsilon)
#         ctau = DP_instance.cTau()
#         print('ctau p8dpconf file =%3.6f cm'%ctau)
#         print('Initial particle parameters for PDGID %d :'%self.DPid)
#         # P8gen.List(self.DPid)
#         if process_selection=="qcd":
#             dpid = self.DPid
#             self.config_lines.append("{}:m0 = {:.12}\n".format(dpid, mass))
#             self.config_lines.append("{}:mWidth = {:.12}\n".format(dpid, u.hbarc/ctau))
#             self.config_lines.append("{}:mMin = 0.001\n".format(dpid))
#             self.config_lines.append("{}:tau0 = {:.12}\n".format(dpid, ctau/u.mm))

#             self.config_lines.append("{}:onMode = off\n".format(dpid))
#         else:
#             self.config_lines.append("{}:new = A A 3 0 0 {:.12} 0.0 0.0 0.0 {:.12}  0   1   0   1   0\n"\
#                                 .format(self.DPid, mass, ctau/u.mm))

        
#         self.config_lines.append("Next:numberCount    =  0\n")

#         # Configuring decay modes...
#         self.addDarkPhotondecayChannels(mass, DP_instance, conffile=os.path.expandvars('darkphotonDecaySelection.conf'), verbose=True)
#         # Finish DP setup...
#         self.config_lines.append("{}:mayDecay = on\n".format(self.DPid))
#         #P8gen.SetDPId(P8gen.GetDPId())
#         # also add to PDG
#         gamma = u.hbarc / float(ctau) #197.3269631e-16 / float(ctau) # hbar*c = 197 MeV*fm = 197e-16 GeV*cm
#         print('gamma=%e'%gamma)
        
#         if process_selection=="meson":
#             #change meson decay to dark photon depending on mass
#             selectedMum = self.manipulatePhysics(motherMode, mass)
#             print('selected mum is : %d'%selectedMum)
#             if (selectedMum == -1): return 0

#         #P8gen.SetParameters("Check:particleData = on")

#         return self.config_lines
    
#     def manipulatePhysics(self,motherMode, mass):
#         #changes of the table, now it is deleted and we have each meson mother for each meson production
#         #print motherMode
#         if motherMode=='pi0' and pi0mass-mass>=0.0000001:
#             # use pi0 -> gamma A'
#             selectedMum = 111
#             self.config_lines.append("111:oneChannel = 1 1 0 22 9900015\n")
            
#         elif motherMode == 'eta' and etamass-mass>=0.000001:
#             # use eta -> gamma A'
#             #print "eta"
#             selectedMum = 221
#             self.config_lines.append("221:oneChannel = 1 1 0 22 9900015\n")
            
#         elif motherMode=="omega" and omegamass-mass>=0.00001:
#             # use omega -> pi0 A'
#             #print "omega"
#             selectedMum = 223
#             self.config_lines.append("223:oneChannel = 1 1 0 111 9900015\n")
            
#         elif motherMode=='eta1' and eta1mass-mass>=0.00001:
#             # use eta' -> gamma A'
#             selectedMum = 331
#             self.config_lines.append("331:oneChannel = 1 1 0 22 9900015\n")
#             #should be considered also for mass < 0.188 GeV....
            
#         elif motherMode=='eta11' and eta1mass-mass>=0.00001:
#             # use eta' -> gamma A'
#             selectedMum = 331
#             self.config_lines.append("331:oneChannel = 1 1 0 113 9900015\n")
#             #should be considered also for mass < 0.188 GeV....

            
#         else:
#             #print "ERROR: please enter a nicer mass, for meson production it needs to be between %3.3f and %3.3f."%(pi0Start,eta1Stop)
#             return -1
#         return selectedMum
    
#     def addDarkPhotondecayChannels(self, mDP, DP,conffile=os.path.expandvars('darkphotonDecaySelection.conf'), verbose=True):
#         """
#         Configures the DP decay table in Pythia8
        
#         Inputs:
#         - P8gen: an instance of ROOT.HNLPythia8Generator()
#         - conffile: a file listing the channels one wishes to activate
#         """
#         isResonant = (self.DPid==4900023)# or P8gen.IsPbrem())
#         # First fetch the list of kinematically allowed decays
#         allowed = DP.allowedChannels()
#         # Then fetch the list of desired channels to activate
#         wanted = self.load(conffile=conffile, verbose=verbose)
#         # Add decay channels
#         for dec in allowed:
#             print('channel allowed:',dec)
#             if dec not in wanted:
#                 print('addDarkPhotondecayChannels WARNING: channel not configured! Please add also in conf file.\t', dec)
#                 quit()
#             print('channel wanted:',dec)

#             if allowed[dec] == 'yes' and wanted[dec] == 'yes':
                
#                 BR = DP.findBranchingRatio(dec)
                
#                 meMode = 0
#                 if isResonant: meMode = 103
#                 if 'hadrons' in dec:
#                     #P8gen.SetDecayToHadrons()
#                     print("debug readdecay table hadrons BR ",BR)
#                     #Taking decays from pythia8 Z->qqbar
#                     dpid = self.DPid
#                     if mDP<3.0:
#                         self.config_lines.append("{}:addChannel =  1 {:.12} {} 1 -1\n"\
#                                             .format(dpid, 0.167*BR, meMode))
#                         self.config_lines.append("{}:addChannel =  1 {:.12} {} 2 -2\n"\
#                                             .format(dpid, 0.666*BR, meMode))
#                         self.config_lines.append("{}:addChannel =  1 {:.12} {} 3 -3\n"\
#                                             .format(dpid, 0.167*BR, meMode))
#                     if mDP>=3.0:
#                         self.config_lines.append("{}:addChannel =  1 {:.12} {} 1 -1\n"\
#                                             .format(dpid, 0.1*BR, meMode))
#                         self.config_lines.append("{}:addChannel =  1 {:.12} {} 2 -2\n"\
#                                             .format(dpid, 0.4*BR, meMode))
#                         self.config_lines.append("{}:addChannel =  1 {:.12} {} 3 -3\n"\
#                                             .format(dpid, 0.1*BR, meMode))
#                         self.config_lines.append("{}:addChannel =  1 {:.12} {} 4 -4\n"\
#                                             .format(dpid, 0.4*BR, meMode))
#                 else:
#                     particles = [p for p in dec.replace('->',' ').split()]
#                     children = particles[1:]
#                     childrenCodes = [self.PDGcode(p) for p in children]
#                     codes = ' '.join(str(code) for code in childrenCodes)
#                     self.config_lines.append("{}:addChannel =  1 {:.12} {} {}\n"\
#                                         .format(self.DPid, BR, meMode, codes))
#                     print("debug readdecay table ",particles,children,BR)


# constants
alphaQED = 1./137.
ccm = 2.99792458e+10
hGeV = 6.58211928*pow(10.,-16)* pow(10.,-9) # no units or it messes up!!

class Particle:
    def mass(self, string):
        if string == 'e-':
            return 0.000501
        elif string == 'mu-':
            return 0.105
        else:
            return 1.777
        
    # mass = {'e-' : 0.000501, 'mu-': 0.105,'ta-' : 1.777}
    
class DarkPhoton:
    "dark photon setup"
    
    def __init__(self, mass, eps):
        self.mDarkPhoton = mass
        self.epsilon = eps
        # self.dataEcm,self.dataR = self.readPDGtable()
        # self.PdgR = self.interpolatePDGtable()

        self.particle = Particle()
    # def readPDGtable(self):
    #     """ Returns R data from PDG in a easy to use format """
    #     ecm=ROOT.vector('double')()
    #     ratio=ROOT.vector('double')()
    #     """ecm,ratio = [],[]"""
    #     with open(os.path.expandvars('rpp2012-hadronicrpp_page1001.dat'),'r') as f:
    #         for line in f:
    #             line = line.split()
    #             try:
    #                 numEcm = float(line[0])
    #                 numR = float(line[3])
    #                 strType = line[7]
    #                 strBis = line[8]
    #                 #if numEcm<2:
    #                 #   print numEcm,numR,strType
    #                 if (('EXCLSUM' in strType) or ('EDWARDS' in strType) or ('BLINOV' in strType)):
    #                     ecm.push_back(numEcm)
    #                     ratio.push_back(numR)
    #                     #print numEcm,numR,strType
    #                 if 'BAI' in strType and '01' in strBis:
    #                     ecm.push_back(numEcm)
    #                     ratio.push_back(numR)
    #                     #print numEcm,numR,strType
    #             except:
    #                 continue
    #     return ecm,ratio


    # def interpolatePDGtable(self):
    #     """ Find the best value for R for the given center-of-mass energy """
    #     fun = ROOT.Math.Interpolator(self.dataEcm.size(),ROOT.Math.Interpolation.kLINEAR)
    #     fun.SetData(self.dataEcm,self.dataR)
    #     return fun

    # def Ree_interp(self,s): # s in GeV
    #     """ Using PDG values for sigma(e+e- -> hadrons) / sigma(e+e- -> mu+mu-) """
    #     # Da http://pdg.lbl.gov/2012/hadronic-xsections/hadron.html#miscplots
    #     #ecm = math.sqrt(s)
    #     ecm = s
    #     if ecm>=10.29:
    #         print('Warning! Asking for interpolation beyond 10.29 GeV: not implemented, needs extending! Taking value at 10.29 GeV')
    #         result=float(self.PdgR.Eval(10.29))
    #     elif ecm>=self.dataEcm[0]:
    #         result = float(self.PdgR.Eval(ecm))
    #     else:
    #         result=0
    #     #print 'Ree_interp for mass %3.3f is %.3e'%(s,result)
    #     return result

    def leptonicDecayWidth(self,lepton): # mDarkPhoton in GeV
        """ Dark photon decay width into leptons, in GeV (input short name of lepton family) """
        ml = self.particle.mass(lepton)
        #print 'lepton %s mass %.3e'%(lepton,ml)
        
        constant = (1./3.) * alphaQED * self.mDarkPhoton * pow(self.epsilon, 2.)
        if 2.*ml < self.mDarkPhoton:
            rad = math.sqrt( 1. - (4.*ml*ml)/(self.mDarkPhoton*self.mDarkPhoton) )
        else:
            rad = 0.
            
        par = 1. + (2.*ml*ml)/(self.mDarkPhoton*self.mDarkPhoton)
        tdw=math.fabs(constant*rad*par)
        #print 'Leptonic decay width to %s is %.3e'%(lepton,tdw)
        return tdw
    
    def leptonicBranchingRatio(self,lepton):
        return self.leptonicDecayWidth(lepton) / self.totalDecayWidth()
        
    # def hadronicDecayWidth(self):
    #     """ Dark photon decay into hadrons """
    #     """(mumu)*R"""
    #     gmumu=self.leptonicDecayWidth('mu-')
    #     tdw=gmumu*self.Ree_interp(self.mDarkPhoton)
    #     #print 'Hadronic decay width is %.3e'%(tdw)
    #     return tdw
    
    # def hadronicBranchingRatio(self):
    #     return self.hadronicDecayWidth() / self.totalDecayWidth()
    
    def totalDecayWidth(self): # mDarkPhoton in GeV
        """ Total decay width in GeV """
        #return hGeV*c / cTau(mDarkPhoton, epsilon)
        tdw = (self.leptonicDecayWidth('e-')
               + self.leptonicDecayWidth('mu-')
               + self.leptonicDecayWidth('tau-'))
            #    + self.hadronicDecayWidth())
        
        #print 'Total decay width %e'%(tdw)
        
        return tdw

    def cTau(self): # decay length in meters, dark photon mass in GeV
        """ Dark Photon lifetime in cm"""
        ctau=hGeV*ccm/self.totalDecayWidth()
        #print "ctau dp.py %.3e"%(ctau) 
        return ctau #GeV/MeV conversion
    
    def lifetime(self):
        return self.cTau()/ccm

    def findBranchingRatio(self,decayString):
        br = 0.
        if   decayString == 'A -> e- e+': br = self.leptonicBranchingRatio('e-')
        elif   decayString == 'A -> mu- mu+': br = self.leptonicBranchingRatio('mu-')
        elif   decayString == 'A -> tau- tau+': br = self.leptonicBranchingRatio('tau-')
        # elif   decayString == 'A -> hadrons': br = self.hadronicBranchingRatio()
        else:
            print('findBranchingRatio ERROR: unknown decay %s'%decayString)
            quit()
            
        return br

    def allowedChannels(self):
        print("Allowed channels for dark photon mass = %3.3f"%self.mDarkPhoton)
        allowedDecays = {'A -> hadrons':'yes'}
        if self.mDarkPhoton > 2.*self.particle.mass('e-'):
            allowedDecays.update({'A -> e- e+':'yes'})
            print("allowing decay to e")
        if self.mDarkPhoton > 2.*self.particle.mass('mu-'):
            allowedDecays.update({'A -> mu- mu+':'yes'})
            print("allowing decay to mu")
        if self.mDarkPhoton > 2.*self.particle.mass('tau-'):
            allowedDecays.update({'A -> tau- tau+':'yes'})
            print("allowing decay to tau")
                        
        return allowedDecays
                    
                            
    # def scaleNEventsIncludingHadrons(self,n):
    #     """ Very simple patch to take into account A' -> hadrons """
    #     brh = self.hadronicBranchingRatio()
    #     #print brh
    #     # if M > m(c cbar):
    #     if self.mDarkPhoton > 2.*self.particle.mass('c'):
    #         visible_frac = 1.
    #     else:
    #         visible_frac = 2./3.
    
    #     increase = brh*visible_frac
    #     #print increase
    #     return n*(1. + increase)
    
    

#VDM FORM FACTOR
def rhoFormFactor(m):
     """ From https://arxiv.org/abs/0910.5589 """
     #constants from the code from Inar: https://github.com/pgdeniverville/BdNMC/blob/master/src/Proton_Brem_Distribution.cpp
     f1ra = 0.6165340033101271
     f1rb = 0.22320420111672623
     f1rc = -0.33973820442685326
     f1wa = 1.0117544786579074
     f1wb = -0.8816565944110686
     f1wc = 0.3699021157531611
     f1prho = f1ra*0.77**2/(0.77**2-m**2-0.77*0.15j)
     f1prhop = f1rb*1.25**2/(1.25**2-m**2-1.25*0.3j)
     f1prhopp = f1rc*1.45**2/(1.45**2-m**2-1.45*0.5j)
     f1pomega = f1wa*0.77**2/(0.77**2-m**2-0.77*0.0085j)
     f1pomegap = f1wb*1.25**2/(1.25**2-m**2-1.25*0.3j)
     f1pomegapp = f1wc*1.45**2/(1.45**2-m**2-1.45*0.5j)
     return abs(f1prho+f1prhop+f1prhopp+f1pomega+f1pomegap+f1pomegapp)

# useful functions
def energy(p,m):
    """ Compute energy from momentum and mass """
    return math.sqrt(p*p + m*m)

def penaltyFactor(m):
    """ Penalty factor for high masses - dipole form factor in the proton-A' vertex """
    """ m in GeV """
    if m*m>0.71:
        return math.pow(m*m/0.71,-4)
    else:
        return 1

def zeta(p, theta):
    """ Fraction of the proton momentum carried away by the paraphoton in the beam direction """
    return p / (protonMomentum * math.sqrt(theta*theta + 1.))


def pTransverse(p, theta):
    """ Paraphoton transverse momentum in the lab frame """
    return protonMomentum*theta*zeta(p,theta)


def ptSquare(p, theta):
    """ Square paraphoton transverse momentum in the lab frame """
    return pow(pTransverse(p,theta), 2.)


def H(p, theta, mDarkPhoton):
    """ A kinematic term """
    return ptSquare(p,theta) + (1.-zeta(p,theta))*mDarkPhoton*mDarkPhoton + pow(zeta(p,theta),2.)*mProton*mProton


def wba(p, theta, mDarkPhoton, epsilon):
    """ Cross section weighting function in the Fermi-Weizsaeker-Williams approximation """
    const = epsilon*epsilon*alphaQED / (2.*math.pi*H(p,theta,mDarkPhoton))

    h2 = pow(H(p,theta,mDarkPhoton),2.)
    oneMinusZSquare = pow(1.-zeta(p,theta),2.)
    mp2 = mProton*mProton
    mA2 = mDarkPhoton*mDarkPhoton

    p1 = (1. + oneMinusZSquare) / zeta(p,theta)
    p2 = ( 2. * zeta(p,theta) * (1.-zeta(p,theta)) * ( (2.*mp2 + mA2)/ H(p,theta,mDarkPhoton) 
            - pow(zeta(p,theta),2.)*2.*mp2*mp2/h2 ) )
    #p3 = 2.*zeta(p,theta)*(1.-zeta(p,theta))*(zeta(p,theta)+oneMinusZSquare)*mp2*mA2/h2
    p3 = 2.*zeta(p,theta)*(1.-zeta(p,theta))*(1+oneMinusZSquare)*mp2*mA2/h2
    p4 = 2.*zeta(p,theta)*oneMinusZSquare*mA2*mA2/h2
    return const*(p1-p2+p3+p4)


def sigma(s): # s in GeV^2 ---> sigma in mb
    """ Parametrisation of sigma(s) """
    a1 = 35.45
    a2 = 0.308
    a3 = 28.94
    a4 = 33.34
    a5 = 0.545
    a6 = 0.458
    a7 = 42.53
    p1 = a2*pow(math.log(s/a3),2.) 
    p2 = a4*pow((1./s),a5)
    p3 = a7*pow((1./s),a6)
    return a1 + p1 - p2 + p3


def es(p, mDarkPhoton):
    """ s(p,mA) """
    return 2.*mProton*(energy(protonMomentum,mProton)-energy(p,mDarkPhoton))


def sigmaRatio(p, mDarkPhoton):
    """ sigma(s') / sigma(s) """
    return sigma(es(p,mDarkPhoton)) / sigma(2.*mProton*energy(protonMomentum,mProton))


def dNdZdPtSquare(p, mDarkPhoton, theta, epsilon):
    """ Differential A' rate per p.o.t. as a function of Z and Pt^2 """
    return sigmaRatio(p,mDarkPhoton)*wba(p,theta,mDarkPhoton,epsilon)


def dPt2dTheta(p, theta):
    """ Jacobian Pt^2->theta """
    z2 = pow(zeta(p,theta),2.)
    return 2.*theta*z2*protonMomentum*protonMomentum


def dZdP(p, theta):
    """ Jacobian z->p """
    return 1./( protonMomentum* math.sqrt(theta*theta+1.) )


def dNdPdTheta(p, theta, mDarkPhoton, epsilon):
    """ Differential A' rate per p.o.t. as a function of P and theta """
    diffRate = dNdZdPtSquare(p,mDarkPhoton,theta,epsilon) * dPt2dTheta(p,theta) * dZdP(p,theta)
    return math.fabs(diffRate) # integrating in (-pi, pi)...


def pMin(mDarkPhoton):
    return max(0.14*protonMomentum, mDarkPhoton)


def pMax(mDarkPhoton):
    #return min(0.86*protonMomentum, math.sqrt( (energy(protonMomentum,mProton)**2. - mDarkPhoton**2.) - mDarkPhoton**2.))
    return math.sqrt( (energy(protonMomentum,mProton)**2. - mDarkPhoton**2.) - mDarkPhoton**2.)


def prodRate(mDarkPhoton, epsilon, tmin = -0.5 * math.pi, tmax = 0.5 * math.pi):
    """ dNdPdTheta integrated over p and theta """
    integral = dblquad( dNdPdTheta, # integrand
                        tmin, tmax, # theta boundaries (2nd argument of integrand)
                        lambda x: pMin(mDarkPhoton), lambda x: pMax(mDarkPhoton), # p boundaries (1st argument of integrand)
                        args=(mDarkPhoton, epsilon) ) # extra parameters to pass to integrand
    return integral[0]



def normalisedProductionPDF(p, theta, mDarkPhoton, epsilon, norm):
    """ Probability density function for A' production in SHIP """
    return (1. / norm) * dNdPdTheta(p, theta, mDarkPhoton, epsilon)


# def hProdPDF(mDarkPhoton, epsilon, norm, binsp, binstheta, tmin = -0.5 * math.pi, tmax = 0.5 * math.pi, suffix=""):
#     """ Histogram of the PDF for A' production in SHIP """
#     angles = np.linspace(tmin,tmax,binstheta).tolist()
#     anglestep = 2.*(tmax - tmin)/binstheta
#     momentumStep = (pMax(mDarkPhoton)-pMin(mDarkPhoton))/(binsp-1)
#     momenta = np.linspace(pMin(mDarkPhoton),pMax(mDarkPhoton),binsp,endpoint=False).tolist()
#     hPDF = ROOT.TH2F("hPDF_eps%s_m%s"%(epsilon,mDarkPhoton) ,"hPDF_eps%s_m%s"%(epsilon,mDarkPhoton),
#         binsp,pMin(mDarkPhoton)-0.5*momentumStep,pMax(mDarkPhoton)-0.5*momentumStep,
#         binstheta,tmin-0.5*anglestep,tmax-0.5*anglestep)
#     hPDF.SetTitle("PDF for A' production (m_{A'}=%s GeV, #epsilon =%s)"%(mDarkPhoton,epsilon))
#     hPDF.GetXaxis().SetTitle("P_{A'} [GeV]")
#     hPDF.GetYaxis().SetTitle("#theta_{A'} [rad]")
#     hPDFtheta = rhoFormFactor.TH1F("hPDFtheta_eps%s_m%s"%(epsilon,mDarkPhoton),
#         "hPDFtheta_eps%s_m%s"%(epsilon,mDarkPhoton),
#         binstheta,tmin-0.5*anglestep,tmax-0.5*anglestep)
#     hPDFp = ROOT.TH1F("hPDFp_eps%s_m%s"%(epsilon,mDarkPhoton),
#         "hPDFp_eps%s_m%s"%(epsilon,mDarkPhoton),
#         binsp,pMin(mDarkPhoton)-0.5*momentumStep,pMax(mDarkPhoton)-0.5*momentumStep)
#     hPDFp.GetXaxis().SetTitle("P_{A'} [GeV]")
#     hPDFtheta.GetXaxis().SetTitle("#theta_{A'} [rad]")
#     for theta in angles:
#         for p in momenta:
#             w = normalisedProductionPDF(p,theta,mDarkPhoton,epsilon,norm)
#             hPDF.Fill(p,theta,w)
#             hPDFtheta.Fill(theta,w)
#             hPDFp.Fill(p,w)
#     hPdfFilename = sys.modules['__main__'].outputDir+"/ParaPhoton_eps%s_m%s%s.root"%(epsilon,mDarkPhoton,suffix)
#     outfile = ROOT.TFile(hPdfFilename,"recreate")

#     hPDF.Write()
#     hPDFp.Write()
#     hPDFtheta.Write()
#     outfile.Close()
#     del angles
#     del momenta
#     return hPDF

if __name__ == "__main__":
    dp = DarkPhoton(1, 0.0001)
    print(dp.findBranchingRatio('A -> e- e+'))
    print(dp.findBranchingRatio('A -> mu- mu+'))
    print(dp.findBranchingRatio('A -> tau- tau+'))