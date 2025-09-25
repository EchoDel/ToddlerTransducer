#!/bin/bash
cd /home/pi/ToddlerTransducer
/home/pi/.local/bin/poetry install --with deployment
/home/pi/.local/bin/poetry run waitress-serve --call 'toddler_transducer:launch_toddler_transducer'
