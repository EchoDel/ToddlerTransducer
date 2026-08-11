#!/bin/bash
cd "$(dirname "$(dirname "$(readlink -f "$0")")")"
"$HOME/.local/bin/poetry" install --with deployment
"$HOME/.local/bin/poetry" run launch_toddler_transducer
