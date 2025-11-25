#include <iostream>
#include <string>

class OutputStrategy {
public:
    virtual void prepareOutput(std::string& outFileName, const std::string& suffix) = 0;
    virtual ~OutputStrategy() {}
};

class LHEOutputStrategy : public OutputStrategy {
public:
    void prepareOutput(std::string& outFileName, const std::string& suffix) override {
        std::string fileExtension = "." + outFileName.substr(outFileName.find_last_of(".")+1); 
        if (fileExtension != ".lhe"){
            std::cout << "Current file extension is: " << fileExtension << std::endl;
            outFileName = outFileName.replace(outFileName.find(fileExtension), fileExtension.length(), ".lhe");
        }
        outFileName = outFileName.replace(outFileName.find(".lhe"), std::string(".lhe").length(), suffix + ".lhe");
    }
};

class HepMCOutputStrategy : public OutputStrategy {
public:
    void prepareOutput(std::string& outFileName, const std::string& suffix) override {
        std::string fileExtension = "." + outFileName.substr(outFileName.find_last_of(".")+1); 
        if (fileExtension != ".hepmc"){
            std::cout << "Current file extension is: " << fileExtension << std::endl;
            outFileName = outFileName.replace(outFileName.find(fileExtension), fileExtension.length(), ".hepmc");
        }
        outFileName = outFileName.replace(outFileName.find(".hepmc"), std::string(".hepmc").length(), suffix + ".hepmc");
    }
};

class DecaySummaryOutputStrategy : public OutputStrategy {
public:
    void prepareOutput(std::string& outFileName, const std::string& suffix) override {
        std::string fileExtension = "." + outFileName.substr(outFileName.find_last_of(".")+1);
        if (fileExtension != ".txt") {
            outFileName = outFileName.replace(outFileName.find(fileExtension), fileExtension.length(), ".txt");
        }
        outFileName = outFileName.replace(outFileName.find(".txt"), std::string(".txt").length(), suffix + ".txt");
    }
};