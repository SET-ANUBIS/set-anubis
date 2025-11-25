import pythia_sim

generator = pythia_sim.create_pythia_generator("External_Integration/Pythia/scan_mN11p1_VeN11e-05.cmnd", "scan_mN11p1_VeN11e-05.lhe", "scan_mN11p1_VeN11e-05.hepmc", "scan_mN11p1_VeN11e-05.txt", "_suffix", 100)
generator.generate_events()
