from SetAnubis.core.DataBase.domain.UFODecayManager import DecayUFOManager
import matplotlib
matplotlib.use('tkagg')
import matplotlib.pyplot as plt
import numpy as np

import os

UFO_HNL_DIR = os.path.abspath(os.path.join(__file__, "..", "..", "..", "..", "..", "..", "Assets", "UFO", "UFO_HNL"))

if __name__ == "__main__":
    decay = DecayUFOManager(UFO_HNL_DIR)

    decay.evaluate_with_sm()

    decay.create_func_caches()
    
    print("Decay 9900012 -> (23, 12) with mN1 = 100 and VeN1 = 1", decay.evaluate(9900012, (23, 12), {"mN1" : 100, "VeN1" : 1}))
    decays_values = []
    for x in np.arange(0.1,10,0.1):
        decays_values.append(decay.evaluate(24, (9900012, -11), {"mN1" : x, "VeN1" : 1}))

    plt.plot(np.arange(0.1,10,0.1), decays_values, color = "purple", label = "partial decay width with VeN1 = 1, others coupling to 0")
    plt.legend()
    plt.xlabel(r"$m_{N1}$ [GeV]")
    plt.ylabel(r"$\Gamma \left(W^+ \to N_1 + e^+\right)$ [GeV]")
    plt.grid(True)
    plt.tick_params(axis="both", which="major", direction="in", length=10)
    plt.tick_params(axis="both", which="minor", direction="in", length=5)
    plt.xlim(0,10)
    plt.show()