#pragma once

#include "Pythia8/Pythia.h"
#include "Pythia8Plugins/HepMC3.h"
#include "OutputStrategy.h"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <memory>
#include <set>
#include <sstream>
#include <string>
#include <vector>

struct ParticleHardCut {
    int pdgId = 0;                 // 0 means: accept any PDG id.
    bool useAbsId = true;          // true: match particle and antiparticle.
    bool finalOnly = false;        // true: require p.isFinal().

    double minPt = -1.0;           // GeV, negative disables the cut.
    double maxPt = -1.0;           // GeV, negative disables the cut.
    double minEta = std::numeric_limits<double>::quiet_NaN();
    double maxEta = std::numeric_limits<double>::quiet_NaN();
    double minEnergy = -1.0;       // GeV, negative disables the cut.
    double maxEnergy = -1.0;       // GeV, negative disables the cut.

    int minCount = 1;              // number of particles matching this cut.
    int maxCount = -1;             // negative disables the upper multiplicity cut.

    bool matches(const Pythia8::Particle& particle) const {
        if (pdgId != 0) {
            const int eventId = useAbsId ? std::abs(particle.id()) : particle.id();
            const int requestedId = useAbsId ? std::abs(pdgId) : pdgId;
            if (eventId != requestedId) return false;
        }

        if (finalOnly && !particle.isFinal()) return false;
        if (minPt >= 0.0 && particle.pT() < minPt) return false;
        if (maxPt >= 0.0 && particle.pT() > maxPt) return false;
        if (std::isfinite(minEta) && particle.eta() < minEta) return false;
        if (std::isfinite(maxEta) && particle.eta() > maxEta) return false;
        if (minEnergy >= 0.0 && particle.e() < minEnergy) return false;
        if (maxEnergy >= 0.0 && particle.e() > maxEnergy) return false;
        return true;
    }
};

struct PythiaRunOptions {
    // Extra Pythia settings applied after the CMND file is read and before init().
    // Example: "PhaseSpace:pTHatMin = 20".
    std::vector<std::string> settings;

    // Particle-data overrides applied before init(). Values are in Pythia units.
    // lifetimes are tau0 in mm; widths are mWidth in GeV.
    std::map<int, double> lifetimes;
    std::map<int, double> widths;

    // Event-level post-generation cuts. Empty means no event filtering.
    std::vector<ParticleHardCut> hardCuts;
    bool requireAllCuts = true;

    // Safety bound for retrying rejected events. <= 0 means totalEvents, i.e. no extra retry budget.
    int maxTrials = 1000000;

    // Keep the existing mass-shift repair logic configurable instead of forcing it for every model.
    bool fixDecayMasses = true;
};

class EventGenerator {
public:
    virtual void generateEvents(
        const std::vector<int>& particleIDs = {},
        const PythiaRunOptions& options = PythiaRunOptions()) = 0;
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
    std::unique_ptr<HepMC3::WriterAscii> hepMCWriter;
    std::shared_ptr<OutputStrategy> lheStrategy;
    std::shared_ptr<OutputStrategy> hepmcStrategy;
    std::shared_ptr<OutputStrategy> txtStrategy;

    static std::string formatDouble(double value) {
        std::ostringstream ss;
        ss << std::setprecision(17) << value;
        return ss.str();
    }

    static std::string boolToPythia(bool value) {
        return value ? "on" : "off";
    }

    void applyRuntimeOptions(Pythia8::Pythia& pythia, const PythiaRunOptions& options) {
        for (const auto& setting : options.settings) {
            if (!setting.empty()) {
                pythia.readString(setting);
            }
        }

        for (const auto& item : options.lifetimes) {
            const int pid = item.first;
            const double tau0 = item.second;
            pythia.readString(std::to_string(pid) + ":tauCalc = off");
            pythia.readString(std::to_string(pid) + ":tau0 = " + formatDouble(tau0));
        }

        for (const auto& item : options.widths) {
            const int pid = item.first;
            const double width = item.second;
            pythia.readString(std::to_string(pid) + ":mWidth = " + formatDouble(width));
            pythia.readString(std::to_string(pid) + ":doForceWidth = on");
        }
    }

    double branchingRatioSum(Pythia8::Pythia& pythia, int pid) const {
        auto* entry = pythia.particleData.particleDataEntryPtr(pid);
        if (!entry) return 0.0;

        double totalBR = 0.0;
        for (int i = 0; i < entry->sizeChannels(); ++i) {
            totalBR += entry->channel(i).bRatio();
        }
        return totalBR;
    }

    void initFromConfig(Pythia8::Pythia& pythia,
                        const std::vector<int>& particleIDs,
                        const std::string& configFile,
                        const PythiaRunOptions& options) {
        pythia.readFile(configFile);
        applyRuntimeOptions(pythia, options);

        if (!options.fixDecayMasses || particleIDs.empty()) {
            pythia.init();
            return;
        }

        pythia.init();

        std::map<int, double> originalMasses;
        for (int pid : particleIDs) {
            auto* entry = pythia.particleData.particleDataEntryPtr(pid);
            if (entry) originalMasses[pid] = entry->m0();
        }

        const double deltaMin = 1e-5;
        const double deltaMax = 1e-2;
        const int maxIterations = 20;

        for (const auto& item : originalMasses) {
            const int pid = item.first;
            const double originalMass = item.second;
            bool fixed = false;

            std::cout << "[INFO] Checking decay table for PID " << pid << "\n";

            if (branchingRatioSum(pythia, pid) > 0.0) {
                std::cout << "[INFO] No decay-mass fix needed for PID " << pid << "\n";
                continue;
            }

            const int directions[] = {+1, -1};
            for (int dir : directions) {
                double low = 0.0;
                double high = deltaMax;
                bool directionFixable = false;

                while (high >= deltaMin) {
                    const double testMass = originalMass + dir * high;
                    pythia.particleData.particleDataEntryPtr(pid)->setM0(testMass);
                    if (!pythia.init()) {
                        high /= 2.0;
                        continue;
                    }

                    if (branchingRatioSum(pythia, pid) > 0.0) {
                        directionFixable = true;
                        break;
                    }

                    high /= 2.0;
                }

                if (!directionFixable) continue;

                for (int iter = 0; iter < maxIterations && (high - low > 1e-6); ++iter) {
                    const double mid = (low + high) / 2.0;
                    const double testMass = originalMass + dir * mid;
                    pythia.particleData.particleDataEntryPtr(pid)->setM0(testMass);
                    if (!pythia.init()) break;

                    if (branchingRatioSum(pythia, pid) > 0.0) {
                        high = mid;
                        fixed = true;
                    } else {
                        low = mid;
                    }
                }

                if (fixed) {
                    const double finalMass = originalMass + dir * high;
                    pythia.particleData.particleDataEntryPtr(pid)->setM0(finalMass);
                    pythia.particleData.particleDataEntryPtr(pid)->setMayDecay(true);
                    std::cout << "[FIXED] PID " << pid << ": mass changed from "
                              << originalMass << " to " << finalMass
                              << " to enable decays.\n";
                    break;
                }
            }

            if (!fixed) {
                std::cerr << "[WARNING] PID " << pid
                          << ": could not enable decays; restoring original mass.\n";
                pythia.particleData.particleDataEntryPtr(pid)->setM0(originalMass);
            }
        }

        std::cout << "[INFO] Final Pythia initialization...\n";
        pythia.init();
    }

    bool cutIsSatisfied(const Pythia8::Event& event, const ParticleHardCut& cut) const {
        int count = 0;
        for (int i = 0; i < event.size(); ++i) {
            if (cut.matches(event[i])) ++count;
        }

        if (count < cut.minCount) return false;
        if (cut.maxCount >= 0 && count > cut.maxCount) return false;
        return true;
    }

    bool passesHardCuts(const Pythia8::Event& event, const PythiaRunOptions& options) const {
        if (options.hardCuts.empty()) return true;

        if (options.requireAllCuts) {
            for (const auto& cut : options.hardCuts) {
                if (!cutIsSatisfied(event, cut)) return false;
            }
            return true;
        }

        for (const auto& cut : options.hardCuts) {
            if (cutIsSatisfied(event, cut)) return true;
        }
        return false;
    }

    std::set<int> summaryParticleIDs(const std::vector<int>& particleIDs,
                                     const PythiaRunOptions& options) const {
        std::set<int> ids;
        for (int id : particleIDs) ids.insert(std::abs(id));
        for (const auto& item : options.lifetimes) ids.insert(std::abs(item.first));
        for (const auto& item : options.widths) ids.insert(std::abs(item.first));
        for (const auto& cut : options.hardCuts) {
            if (cut.pdgId != 0) ids.insert(std::abs(cut.pdgId));
        }
        return ids;
    }

    void writeSummary(const std::vector<int>& particleIDs,
                      const PythiaRunOptions& options,
                      int requestedEvents,
                      int generatedEvents,
                      int triedEvents) {
        std::ofstream summary(outFileNameTxt);
        summary << "# MGGenerationInfo-like summary\n";
        summary << "#  Requested Events        : " << requestedEvents << "\n";
        summary << "#  Generated Events        : " << generatedEvents << "\n";
        summary << "#  Tried Events            : " << triedEvents << "\n";
        summary << "#  Pythia sigmaGen (pb)    : " << std::scientific << pythia.info.sigmaGen() * 1e9 << "\n";

        auto idsToWrite = summaryParticleIDs(particleIDs, options);
        if (!idsToWrite.empty()) {
            const int firstId = *idsToWrite.begin();
            auto firstParticle = pythia.particleData.findParticle(firstId);
            if (firstParticle) {
                summary << "#  Integrated weight (pb)  : " << std::scientific
                        << pythia.info.sigmaGen() * 1e9 * firstParticle->mWidth() << "\n";
            }
        }
        summary << "\n# DECAY WIDTHS FOR REQUESTED PARTICLES\n";

        for (int id : idsToWrite) {
            auto particle = pythia.particleData.findParticle(id);
            if (!particle) {
                std::cout << "[WARNING] No particle found for PID " << id << "\n";
                continue;
            }

            const double width = particle->mWidth();
            summary << "DECAY  " << id << "   " << std::scientific << width << "\n";

            for (int i = 0; i < particle->sizeChannels(); ++i) {
                const auto& channel = particle->channel(i);
                summary << "   " << std::scientific << channel.bRatio()
                        << "   " << channel.multiplicity();
                for (int j = 0; j < channel.multiplicity(); ++j) {
                    summary << "    " << channel.product(j);
                }
                summary << " # " << channel.bRatio() * width << "\n";
            }
        }
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
          hepMCWriter(nullptr),
          lheStrategy(std::make_shared<LHEOutputStrategy>()),
          hepmcStrategy(std::make_shared<HepMCOutputStrategy>()),
          txtStrategy(std::make_shared<DecaySummaryOutputStrategy>())
    {}

    void generateEvents(
        const std::vector<int>& particleIDs = {},
        const PythiaRunOptions& options = PythiaRunOptions()) override {
        lheStrategy->prepareOutput(outFileNameLHE, suffix);
        hepmcStrategy->prepareOutput(outFileNameHepMC, suffix);
        txtStrategy->prepareOutput(outFileNameTxt, suffix);

        initFromConfig(pythia, particleIDs, inFile, options);

        hepMCWriter.reset(new HepMC3::WriterAscii(outFileNameHepMC));
        lhef3.openLHEF(outFileNameLHE);
        lhef3.setInit();
        lhef3.initLHEF();

        HepMC3::Pythia8ToHepMC3 toHepMC;

        int iAbort = 0;
        const int nAbort = pythia.mode("Main:timesAllowErrors");
        const int requestedEvents = totalEvents;
        const int maxTrials = options.maxTrials > 0 ? options.maxTrials : requestedEvents;

        int generatedEvents = 0;
        int triedEvents = 0;

        while (generatedEvents < requestedEvents && triedEvents < maxTrials) {
            ++triedEvents;

            if (!pythia.next()) {
                pythia.event.list();
                if (++iAbort < nAbort) continue;
                std::cout << "Event generation aborted prematurely, owing to error!\n";
                break;
            }

            if (!passesHardCuts(pythia.event, options)) {
                continue;
            }

            lhef3.setEvent();

            HepMC3::GenEvent hepmcEvent;
            toHepMC.fill_next_event(pythia, hepmcEvent);
            hepMCWriter->write_event(hepmcEvent);

            ++generatedEvents;
            std::cout << generatedEvents << "/" << requestedEvents << " accepted events done" << std::endl;
        }

        if (generatedEvents < requestedEvents) {
            std::cout << "[WARNING] Generated " << generatedEvents << " accepted events out of "
                      << requestedEvents << " requested after " << triedEvents << " trials.\n";
        }

        pythia.stat();
        lhef3.closeLHEF(true);
        writeSummary(particleIDs, options, requestedEvents, generatedEvents, triedEvents);
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
        return std::make_shared<PythiaEventGenerator>(
            inFile, outFileNameLHE, outFileNameHepMC, suffix, outFileNameTxt, totalEvents);
    }
};
