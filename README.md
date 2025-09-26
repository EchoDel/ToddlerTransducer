# ToddlerTransducer
Project for playing audio from a speaker using physical pucks


# Todo

- [x] Wiring Diagram
- [ ] Finalise enclosure
- [ ] Basic Software
- [ ] OTA Update
  - [ ] Build Pipeline
- [x] Playback without puck
- [x] Codeless adding of new files
- [ ] Type hints

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
   * Current song ` ,.VLC_MEDIA_PLAYER.get_media().get_mrl()`
   * Time through it `VLC_MEDIA_PLAYER.get_time()`
   * Time left  `VLC_MEDIA_PLAYER.get_length(), VLC_MEDIA_PLAYER.get_position()`
   * If its repeating
1. Add ability to repeat song
2. Error check the song name input so it can only be a song that exists.

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


## Download a copy of the configs

https://stackoverflow.com/questions/24577349/flask-download-a-file

VLC Python docs, https://www.olivieraubert.net/vlc/python-ctypes/doc/
Loop VLC, https://stackoverflow.com/questions/7214843/repeating-single-movie-using-python-bindings-for-vlc-what-is-a-psz-name

# Install

1. clone the git repo,
   * git clone https://github.com/EchoDel/ToddlerTransducer.git
1. Change to that folder
   * cd ToddlerTransducer
1. Copy the service 
   * sudo cp ./install/ToddlerTransducer.service /etc/systemd/system/ToddlerTransducer.service
1. Launch the service
   * sudo systemctl start ToddlerTransducer.service
1. `crontab -e`
   * Add the following;  */5 * * * * /home/pi/ToddlerTransducer/install/ota_update.sh
