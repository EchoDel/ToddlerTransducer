#!/bin/bash
cd "$HOME/ToddlerTransducer" || exit 1
poetry install --with deployment
poetry run launch_toddler_transducer
