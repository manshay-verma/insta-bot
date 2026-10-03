#!/bin/bash
# setup_python.sh - Configure Python/Conda environment

set -e

echo "Installing Miniconda..."
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh
bash miniconda.sh -b -p $HOME/miniconda
eval "$($HOME/miniconda/bin/conda shell.bash hook)"

echo "Creating 'inst-bot-venv'..."
conda create -n inst-bot-venv python=3.11 -y
conda activate inst-bot-venv

echo "Installing project requirements..."
pip install -r requirements.txt

echo "Installing Playwright..."
playwright install --with-deps

echo "Python environment setup complete!"
