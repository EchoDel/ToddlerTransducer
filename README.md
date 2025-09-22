# ToddlerTransducer
Project for playing audio from a speaker using physical pucks


# Todo

- [x] Wiring Diagram
- [ ] Finalise enclosure
- [ ] Basic Software
- [ ] OTA Update
  - [ ] Build Pipeline
- [ ] Playback without puck
- [ ] Codeless adding of new files

## Music Playback loop

Each loop
Check if tag is present
If there is no change then continue
If there wasn't before and is now load new song and start playing
If there was before and isn't now, fade out
If the tag has changed id then change song

## Web UI

Todo List

1. Add feedback on;
   * Current song
   * Time through it
   * Time left
   * If its repeating
1. Add ability to repeat song

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
https://askubuntu.com/questions/155791/how-do-i-sudo-a-command-in-a-script-without-being-asked-for-a-password/155827#155827
