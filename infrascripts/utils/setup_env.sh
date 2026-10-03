#!/bin/bash
# setup_env.sh - Initialize project environment from template

set -e

if [ ! -f .env.example ]; then
    echo "ERROR: .env.example not found in root!"
    exit 1
fi

if [ -f .env ]; then
    echo "Found existing .env, skipping copy."
else
    echo "Creating .env from .env.example..."
    cp .env.example .env
fi

echo "Environment initialized! Please update values in .env"
