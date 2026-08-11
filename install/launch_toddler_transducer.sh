#!/bin/bash
cd /home/pi/ToddlerTransducer
/home/pi/.local/bin/poetry install --with deployment
/home/pi/.local/bin/poetry run launch_toddler_transducer
