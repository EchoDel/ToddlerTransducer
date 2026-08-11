#!/bin/bash
export PATH="$HOME/.local/bin:$PATH"
export PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring
cd "$(dirname "$(dirname "$(readlink -f "$0")")")" || exit 1
git fetch
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse @{u})
if [ "$LOCAL" != "$REMOTE" ]; then
    echo "Repository is outdated. Updating..."
    git pull
    git submodule update --init --recursive
    sudo systemctl stop ToddlerTransducer.service
    poetry install
    poetry build
    sudo systemctl start ToddlerTransducer.service
else
    echo "Repository is up to date."
fi
