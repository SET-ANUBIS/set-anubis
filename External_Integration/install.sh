#!/bin/bash

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

get_package_manager() {
    if command_exists dnf; then
        echo "dnf"
    elif command_exists apt; then
        echo "apt"
    else
        echo "unknown"
    fi
}

required_tools=("cmake" "gcc" "gfortran" "g++")

verify_tools() {
    local package_manager=$(get_package_manager)

    for tool in "${required_tools[@]}"; do
        if ! command_exists $tool; then
            echo "$tool is not installed. Please install it using the following command:"
            case $package_manager in
                "dnf")
                    echo "sudo dnf install $tool"
                    ;;
                "apt")
                    echo "sudo apt install $tool"
                    ;;
                "unknown")
                    echo "Package manager not detected. Please install $tool manually."
                    ;;
            esac
            exit 1
        fi
    done
}

# Call the verification function
verify_tools

declare -A software_dependencies
software_dependencies=(
    ["Pythia"]="HepMC3"
    ["HepMC3"]=""
    ["MadGraph"]=""
    ["Marty"]=""
)

installed_software=()
cd External_Integration

check_dependencies() {
    local software=$1
    local dependencies=${software_dependencies[$software]}

    if [[ -n "$dependencies" ]]; then
        for dep in $dependencies; do
            if [[ ! " ${installed_software[@]} " =~ " ${dep} " ]]; then
                echo "Error: $software needs $dep which is not installed."
                exit 1
            fi
        done
    fi
}

resolve_install_order() {
    local to_install=("$@")
    local resolved=()
    local unresolved=()

    for software in "${to_install[@]}"; do
        resolve_dependencies "$software" resolved unresolved
    done

    echo "${resolved[@]}"
}

resolve_dependencies() {
    local software=$1
    local dependencies=${software_dependencies[$software]}
    local resolved_ref=$2
    local unresolved_ref=$3

    if [[ " ${!resolved_ref} " =~ " ${software} " ]]; then
        return
    fi

    if [[ " ${!unresolved_ref} " =~ " ${software} " ]]; then
        echo "Error: Circular dependency detected for $software"
        exit 1
    fi

    eval "$unresolved_ref+=(\"$software\")"

    if [[ -n "$dependencies" ]]; then
        for dep in $dependencies; do
            resolve_dependencies "$dep" "$resolved_ref" "$unresolved_ref"
        done
    fi

    eval "$resolved_ref+=(\"$software\")"
    eval "$unresolved_ref=(\"${!unresolved_ref[@]/$software}\")"
}

install_software() {
    local software=$1
    echo $software/install.sh
    echo "Installation of $software..."

    check_dependencies $software

    if [[ -f $software/install.sh ]]; then
        (cd $software && ./install.sh)
        if [[ $? -ne 0 ]]; then
            echo "Error during installation of $software."
            exit 1
        fi
        installed_software+=($software)
    else
        echo "Installation script for $software not found."
        exit 1
    fi
}

software_to_install=$(resolve_install_order "$@")
for software in $software_to_install; do
    install_software $software
done

echo "Installation ended with success for: ${installed_software[@]}"

cd ..