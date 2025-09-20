# ToddlerTransducer
Project for playing audio from a speaker using physical pucks


# Todo

- [x] Wiring Diagram
- [ ] Finalise enclosure
- [ ] Basic Software
- [ ] OTA Update
- [ ] Playback without puck
- [ ] Codeless adding of new files

## Music Playback loop

Each loop
Check if tag is present
If there is no change then continue
If there wasn't before and is now load new song and start playing
If there was before and isn't now, fade out
If the tag has changed id then change song


## OTA Update

https://dhirajpatra.medium.com/ota-for-python-application-running-in-raspberry-pi-967e3e8d591d


## Codeless adding of new files

Flask App
https://www.digitalocean.com/community/tutorials/how-to-make-a-web-application-using-flask-in-python-3
https://stackabuse.com/step-by-step-guide-to-file-upload-with-flask/


## Playback without puck

Flask App
https://www.geeksforgeeks.org/python/how-to-add-authentication-to-your-app-with-flask-login/
https://www.raspberrypi.com/documentation/computers/configuration.html#enable-hotspot
