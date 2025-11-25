#include "Pythia8/Pythia.h"
#include "Pythia8Plugins/HepMC3.h"
#include "OutputStrategy.h"
#include <string>
#include <memory>
#include <cmath>
#include <map>
#include <algorithm>

class EventGenerator {
public:
    virtual void generateEvents(const std::vector<int>& bsmIDs = {}) = 0;
    virtual ~EventGenerator() {}
};

class PythiaEventGenerator : public EventGenerator {
private:
    std::string inFile;
    std::string outFileNameLHE;
    std::string outFileNameHepMC;
    std::string suffix;
    std::string outFileNameTxt;
    int totalEvents;
    Pythia8::Pythia pythia;
    Pythia8::LHEF3FromPythia8 lhef3;
    HepMC3::WriterAscii hepMCWriter;
    std::shared_ptr<OutputStrategy> lheStrategy;
    std::shared_ptr<OutputStrategy> hepmcStrategy;
    std::shared_ptr<OutputStrategy> txtStrategy;

    void robustInitWithDecayFix(Pythia8::Pythia& pythia, const std::vector<int>& bsmIDs, const std::string& configFile) {
        pythia.readFile(configFile);
        pythia.init();

        std::map<int, double> originalMasses;
        for (int pid : bsmIDs)
            originalMasses[pid] = pythia.particleData.m0(pid);

        const double deltaMin = 1e-5;
        const double deltaMax = 1e-2;
        const int maxIterations = 20;

        for (int pid : bsmIDs) {
            double originalMass = originalMasses[pid];
            bool fixed = false;

            std::cout << "[INFO] Trying to fix decay for PID " << pid << "\n";

            auto& initialParticle = *pythia.particleData.particleDataEntryPtr(pid);
            double totalBR = 0.0;
            for (int i = 0; i < initialParticle.sizeChannels(); ++i)
                totalBR += initialParticle.channel(i).bRatio();

            if (totalBR > 0.0) {
                std::cout << "[INFO] No fix needed for PID " << pid << "\n";
                continue;
            }

            double directions[] = {+1, -1};
            for (int dir : directions) {
                double low = 0.0;
                double high = deltaMax;
                bool directionFixable = false;

                while (high >= deltaMin) {
                    double testMass = originalMass + dir * high;
                    pythia.particleData.particleDataEntryPtr(pid)->setM0(testMass);
                    if (!pythia.init()) {
                        high /= 2;
                        continue;
                    }

                    auto& testParticle = *pythia.particleData.particleDataEntryPtr(pid);
                    double br = 0.0;
                    for (int i = 0; i < testParticle.sizeChannels(); ++i)
                        br += testParticle.channel(i).bRatio();

                    if (br > 0.0) {
                        directionFixable = true;
                        break;
                    }

                    high /= 2;
                }

                if (!directionFixable) continue;

                for (int iter = 0; iter < maxIterations && (high - low > 1e-6); ++iter) {
                    double mid = (low + high) / 2.0;
                    double testMass = originalMass + dir * mid;
                    pythia.particleData.particleDataEntryPtr(pid)->setM0(testMass);
                    if (!pythia.init()) break;

                    auto& testParticle = *pythia.particleData.particleDataEntryPtr(pid);
                    double br = 0.0;
                    for (int i = 0; i < testParticle.sizeChannels(); ++i)
                        br += testParticle.channel(i).bRatio();

                    if (br > 0.0) {
                        high = mid;
                        fixed = true;
                    } else {
                        low = mid;
                    }
                }

                if (fixed) {
                    double finalMass = originalMass + dir * high;
                    pythia.particleData.particleDataEntryPtr(pid)->setM0(finalMass);
                    std::cout << "[FIXED] PID " << pid << ": mass changed from "
                            << originalMass << " to " << finalMass << " to enable decays.\n";
                    pythia.particleData.particleDataEntryPtr(pid)->setMayDecay(true);
                    break;
                }
            }

            if (!fixed) {
                std::cerr << "[ERROR] PID " << pid << ": could not enable decays, restoring original mass.\n";
                pythia.particleData.particleDataEntryPtr(pid)->setM0(originalMass);
            }
        }

        std::cout << "[INFO] Final Pythia initialization...\n";
        pythia.init();
    }




public:
    PythiaEventGenerator(
        const std::string& inFile_,
        const std::string& outFileNameLHE_,
        const std::string& outFileNameHepMC_,
        const std::string& suffix_,
        const std::string& outFileNameTxt_,
        int totalEvents_)
        : inFile(inFile_),
          outFileNameLHE(outFileNameLHE_),
          outFileNameHepMC(outFileNameHepMC_),
          suffix(suffix_),
          outFileNameTxt(outFileNameTxt_),
          totalEvents(totalEvents_),
          lhef3(&pythia.event, &pythia.info),
          hepMCWriter(outFileNameHepMC_),
          lheStrategy(std::make_shared<LHEOutputStrategy>()),
          hepmcStrategy(std::make_shared<HepMCOutputStrategy>()),
          txtStrategy(std::make_shared<DecaySummaryOutputStrategy>())
    {}

    void generateEvents(const std::vector<int>& bsmIDs = {}) override {
        lheStrategy->prepareOutput(outFileNameLHE, suffix);
        hepmcStrategy->prepareOutput(outFileNameHepMC, suffix);
        txtStrategy->prepareOutput(outFileNameTxt, suffix);
        std::cout << "WOUW" << std::endl;


        robustInitWithDecayFix(pythia, bsmIDs, inFile);

        lhef3.openLHEF(outFileNameLHE);
        lhef3.setInit();
        lhef3.initLHEF();

        HepMC3::Pythia8ToHepMC3 toHepMC;
        
        int iAbort = 0;
        int nAbort = pythia.mode("Main:timesAllowErrors");
        int nEvent = totalEvents;
        
        int iGenerated = 0;
        int iTried = 0;
        int hnl_passing_cuts = 0;
        int total_particle = 0;

        for (int iEvent = 0; iEvent < nEvent; ++iEvent) {
            if (!pythia.next()) {
                pythia.event.list();
                if (++iAbort < nAbort) continue;
                std::cout << "Event generation aborted prematurely, owing to error!\n";
                break;
            }
            
            bool keepEvent = false;
            int  num_bsm_particle = 0;
            ++total_particle;
            for (int i = 0; i < pythia.event.size(); ++i) {
                
                const auto& p = pythia.event[i];
                // if (!p.isFinal()) continue;
                if (std::find(bsmIDs.begin(), bsmIDs.end(), std::abs(p.id())) != bsmIDs.end()) {
                    ++num_bsm_particle;
                    // if (p.pT() > 30.0 && num_bsm_particle == 1) {
                    //     keepEvent = true;
                    // }
                    if (p.pT() > 30.0) {
                        keepEvent = true;
                    }
                }
                
            }
            // if (num_bsm_particle != 1) {
            //     keepEvent = false;
            // }
            // if (num_bsm_particle != 1 || !keepEvent) {
            //     --iEvent;
            //     continue;
            // }
            if (!keepEvent && total_particle < 1000000) {
                --iEvent;
                continue;
            }
            if (total_particle > 1000000) {
                std::cout << "Tried for a long time (1000000 events), didn't found particle passing the cuts." << std::endl;
            }
            ++hnl_passing_cuts;
            std::cout << hnl_passing_cuts << "/" << nEvent << " events done" << std::endl;

            lhef3.setEvent();

            HepMC3::GenEvent hepmcEvent;
            toHepMC.fill_next_event(pythia, hepmcEvent);
            hepMCWriter.write_event(hepmcEvent);

            ++iGenerated;
        }

        pythia.stat();

        lhef3.closeLHEF(true);

        std::ofstream summary(outFileNameTxt);
        summary << "# MGGenerationInfo-like summary\n";
        summary << "#  Number of Events        : " << nEvent << "\n";
        auto elem = pythia.particleData.findParticle(bsmIDs[0]);
        summary << "#  Integrated weight (pb)  : " << std::scientific << pythia.info.sigmaGen() * 1e9 * elem->mWidth() << "\n\n";

        summary << "# DECAY WIDTHS FOR BSM PARTICLES\n";

        std::set<int> idsToWrite(bsmIDs.begin(), bsmIDs.end());

        for (int id : bsmIDs) {
            auto particle = pythia.particleData.findParticle(id);
            if (!particle) {
                std::cout << "no particle found !" << std::endl;
                continue;
            }
            
            double width = particle->mWidth();
            if (width <= 0.0) continue;

            summary << "DECAY  " << id << "   " << std::scientific << width << "\n";
            std::vector<Pythia8::DecayChannel> decay_channels;
            for (int i =0; i< particle->sizeChannels(); i++) {
                decay_channels.push_back(particle->channel(i));
            }

            for (const auto& channel : decay_channels) {
                summary << "   " << std::scientific << channel.bRatio() << "   " << channel.multiplicity();
                for (int i = 0; i < channel.multiplicity(); ++i) {
                    summary << "    " << channel.product(i);
                }
                summary << " # " << channel.bRatio() * width << "\n";
            }
        }
        summary.close();
        }
};

class EventGeneratorFactory {
public:
    static std::shared_ptr<EventGenerator> createPythiaGenerator(
        const std::string& inFile,
        const std::string& outFileNameLHE,
        const std::string& outFileNameHepMC,
        const std::string& outFileNameTxt,
        const std::string& suffix,
        int totalEvents) {
        return std::make_shared<PythiaEventGenerator>(inFile, outFileNameLHE, outFileNameHepMC, suffix, outFileNameTxt, totalEvents);
    }
};
