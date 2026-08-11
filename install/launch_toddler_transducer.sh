#!/bin/bash
export PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring
cd "$(dirname "$(dirname "$(readlink -f "$0")")")"
"$HOME/.local/bin/poetry" install --with deployment
"$HOME/.local/bin/poetry" run launch_toddler_transducer
