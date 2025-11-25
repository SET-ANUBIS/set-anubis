# Installing WSL and Ubuntu on Windows

Windows Subsystem for Linux (WSL) allows you to run a Linux environment directly on Windows without the need for a virtual machine. This guide will help you install WSL and set up an Ubuntu distribution.

## Step 1: Enable WSL
1. Open **PowerShell** as Administrator.
2. Run the following command to enable WSL:
   ```powershell
   wsl --install
   ```
   This command installs WSL and the latest Ubuntu distribution by default.

3. Restart your computer if prompted.

# Stop here if you want to keep the default version.

## Step 2: Install a Specific Linux Distribution (Optional)
If you want to install a specific version of Ubuntu instead of the default one, follow these steps:

1. List available distributions with:
   ```powershell
   wsl --list --online
   ```
2. Install a specific version (e.g., Ubuntu 22.04):
   ```powershell
   wsl --install -d Ubuntu-22.04
   ```

## Step 3: Set Up Ubuntu
1. Open **Ubuntu** from the Start menu.
2. Wait for the installation process to complete.
3. Create a new UNIX username and password.
4. You are now ready to use Ubuntu on Windows!

## Step 4: Update and Upgrade
After installing Ubuntu, update it with:
```bash
sudo apt update && sudo apt upgrade -y
```

## Step 5: Set WSL Version (Optional)
To switch between WSL 1 and WSL 2:
```powershell
wsl --set-version Ubuntu-22.04 2
```
To make WSL 2 the default for future installations:
```powershell
wsl --set-default-version 2
```

## Step 6: Verify Installation
Check your installed distributions and their versions:
```powershell
wsl --list --verbose
```

## Uninstalling WSL (If Needed)
To remove a distribution:
```powershell
wsl --unregister Ubuntu-22.04
```
To completely remove WSL:
1. Disable the feature:
   ```powershell
   dism.exe /online /disable-feature /featurename:Microsoft-Windows-Subsystem-Linux
   ```
2. Restart your computer.

## Conclusion
You have successfully installed WSL and Ubuntu on Windows! You can now enjoy a full Linux environment integrated with your Windows workflow.
