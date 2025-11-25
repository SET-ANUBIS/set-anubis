# Installation Guide

Follow the steps below to set up the environment and install the required software.

---

## Prerequisites

Ensure the following tools are installed on your system:
- **Bash**
- **Python 3** with `pip`
- System tools: `cmake`, `gcc`, `gfortran`, `g++`

If missing, the script will guide you to install them using:
- `dnf` for AlmaLinux
- `apt` for Ubuntu

1. **Clone the repository**:
   ```bash
   git clone https://gitlab.dur.scotgrid.ac.uk/anubis_sensitivity/neo-set-anubis.git
   cd neo-set-anubis

2. **Run the main installation script**:
   Execute the main script to install the required software and configure the environment:
   ```bash
   ./install.sh [software...]
   ```
   - Example: Install specific software in the correct order:
     ```bash
     ./install.sh HepMC3 Pythia
     ```
   - If no arguments are provided, the script will guide you.

   - For now, HepMC3, Pythia and MadGraph are the three software available.

3. **Install Python dependencies**:
   If a `requirements.txt` file exists, the script will install the dependencies automatically using:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Setup**:
   The script adds the current directory to your `PYTHONPATH`. If this is not already configured in `~/.bashrc`, the script will update it.

---

## Features

- **System Tools Check**: Verifies the presence of essential tools like `cmake`, `gcc`, `gfortran`, and `g++`.
- **Dependency Management**: Automatically determines the correct order for software installation based on dependencies.
- **Customizable Installation**: Allows you to specify which software to install.

---

## Example Command

To install specific software:
```bash
./install.sh Pythia HepMC3 MadGraph
```
The script will reorder the installation based on the dependencies (e.g., `HepMC3` is installed before `Pythia`).

---

## Final Messages

- On success: `Installation completed successfully.`
- On error: The script will stop and display the issue.

---

## Notes

- Update `requirements.txt` to add or modify Python dependencies.
- Ensure necessary permissions (e.g., `sudo`) to install system tools if prompted.