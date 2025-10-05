#!/bin/bash

if [ "$1" == "-h" -o "$1" == "--help" ]; then
    echo "Usage: $0 [-h|--help] [-u|--upgrade]"
    echo "Setup or upgrade the environment"
    echo "Options:"
    echo "  --help         Show this help message and exit"
    echo "  -u, --upgrade  Upgrade the environment"
    exit 0
fi

#==========================================================#

if [ ! -d .venv ]; then
    echo "Creating virtual environment"
    python -m venv .venv
fi
. .venv/bin/activate
pip install -U pip pip-tools

if [ "$1" == "-u" -o "$1" == "--upgrade" -o ! -f requirements.txt ]; then
    echo "Upgrading requirements.txt"
    pip-compile requirements.in -o requirements.txt
    pip install -r requirements.txt
fi

#==========================================================#
echo "Setup done"
