/* 
   Pythia runner script to produce both Les Houches Event Files in LHEF 3.0 format
   and HepMC event files.
   Uses LHEF3FromPYTHIA8 for LHEF output and HepMC3 interface for HepMC output.
*/

#include "Pythia8/Pythia.h"
#include "Pythia8Plugins/HepMC3.h"
#include <iostream>
#include <fstream>
#include <string>
#include <regex>
using namespace Pythia8;

int main(int argc, char *argv[]) {

    std::string inFile = "pythia_config.cmnd";
    std::string outFileNameLHE = "";
    std::string outFileNameHepMC = "";
    std::string suffix = "";
    std::string mode = "hnl";
    std::string totalEvents = "100";

    for (int i = 0; i < argc; i++) {
        if (std::string(argv[i]) == "--infile" || std::string(argv[i]) == "-i") {
            inFile = std::string(argv[i + 1]);
            i++;
        } else if (std::string(argv[i]) == "--outfileLHE" || std::string(argv[i]) == "-ol") {
            outFileNameLHE = std::string(argv[i + 1]);
            i++;
        } else if (std::string(argv[i]) == "--outfileHepMC" || std::string(argv[i]) == "-oh") {
            outFileNameHepMC = std::string(argv[i + 1]);
            i++;
        } else if (std::string(argv[i]) == "--suffix" || std::string(argv[i]) == "-s") {
            suffix = std::string(argv[i + 1]);
            i++;
        } else if (std::string(argv[i]) == "--mode" || std::string(argv[i]) == "-m") {
            mode = std::string(argv[i + 1]);
            i++;
        } else if (std::string(argv[i]) == "--nevents" || std::string(argv[i]) == "-n") {
            totalEvents = std::string(argv[i + 1]);
            if (!std::regex_match(totalEvents, std::regex("((\\+|-)?[[:digit:]]+)(\\.([[:digit:]]+)?)?"))) {
                std::cout << "Input --nevents/-n (" << totalEvents << ") is not a number, please enter an integer value." << std::endl;
                return 1;
            }
            totalEvents = std::to_string(std::stoi(totalEvents));
            i++;
            continue;
        } else if (std::string(argv[i]) == "--help" || std::string(argv[i]) == "-h") {
            std::cout << "Run the pythia event generation. Usage:" << std::endl;
            std::cout << std::endl;
            std::cout << "Run [options]" << std::endl;
            std::cout << std::endl;
            std::cout << "--nevents/-n: The total number of pythia events to simulate." << std::endl;
            std::cout << "--infile/-i:  The input cmnd configuration file to use." << std::endl;
            std::cout << "--outfileLHE/-ol: The name of the Les Houches file output." << std::endl;
            std::cout << "--outfileHepMC/-oh: The name of the HepMC file output." << std::endl;
            std::cout << "--suffix/-s:  A suffix to add to the output file name." << std::endl;
            std::cout << "--mode/-m:    Specify which type of model to simulate." << std::endl;
            std::cout << "--help/-h:    Print this Message!." << std::endl;
            return 0;
        }
    }

    std::cout << "Infile: " << inFile <<std::endl;
    std::cout << "Outfile: " << outFileNameLHE <<std::endl;
    std::cout << "Suffix: " << suffix << std::endl;
    std::cout << "Mode: " << mode << std::endl;
    std::cout << "Total Events: " << totalEvents << std::endl;

    Pythia pythia;
    Event& event = pythia.event;

    pythia.readFile(inFile);

    LHEF3FromPythia8 lhef3(&pythia.event, &pythia.info);

    if (outFileNameLHE=="")
        outFileNameLHE = inFile.replace(inFile.find(".cmnd"),std::string(".cmnd").length(),".lhe");
    
    if (outFileNameHepMC=="")
        outFileNameHepMC = inFile.replace(inFile.find(".lhe"),std::string(".lhe").length(),".hepmc");


    if (outFileNameLHE.find(".") == std::string::npos)
        outFileNameLHE = outFileNameLHE + ".lhe";

    if (outFileNameHepMC.find(".") == std::string::npos)
        outFileNameHepMC = outFileNameLHE + ".hepmc";

    std::string fileExtension = "." + outFileNameLHE.substr(outFileNameLHE.find_last_of(".")+1); 
    if (fileExtension != ".lhe"){
        std::cout << "Current file extension is: " << fileExtension <<std::endl;
        outFileNameLHE = outFileNameLHE.replace(outFileNameLHE.find(fileExtension),fileExtension.length(),".lhe");
    }
    
    // Add suffix
    suffix = suffix + "_Events" + totalEvents;
    outFileNameLHE = outFileNameLHE.replace(outFileNameLHE.find(".lhe"),std::string(".lhe").length(),suffix+".lhe");

    suffix = suffix + "_Events" + totalEvents;
    outFileNameHepMC = outFileNameHepMC.replace(outFileNameHepMC.find(".hepmc"),std::string(".hepmc").length(),suffix+".hepmc");


    lhef3.openLHEF(outFileNameLHE);

    pythia.readString("Main:numberOfEvents = " + totalEvents);
    int nEvent   = pythia.mode("Main:numberOfEvents");
    int nAbort   = pythia.mode("Main:timesAllowErrors");
    pythia.init();
    
    lhef3.setInit();

    lhef3.initLHEF();

    HepMC3::Pythia8ToHepMC3 toHepMC;
    HepMC3::WriterAscii hepMCWriter(outFileNameHepMC);

    

    int iAbort = 0;

    for (int iEvent = 0; iEvent < nEvent; ++iEvent) {
        if (!pythia.next()) {
        event.list();
        if (++iAbort < nAbort) continue;
        cout << " Event generation aborted prematurely, owing to error!\n";
        break;
        }

        lhef3.setEvent();

        HepMC3::GenEvent hepmcEvent;
        toHepMC.fill_next_event(pythia, hepmcEvent);
        hepMCWriter.write_event(hepmcEvent);
    }

    pythia.stat();
    lhef3.closeLHEF(true);


    return 0;
}
