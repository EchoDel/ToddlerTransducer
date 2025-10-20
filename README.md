# ToddlerTransducer
Project for playing audio from a speaker using physical pucks. These use an RFID/NFC tag to identify which song to play.


# Functionality

1. Playback of audio when a puck is placed on top.
2. Playback of audio through a web app.
3. Uploading of new audio tracks through a web app.
4. Over the air updated from the github repo.


## What does the Playback Loop do

Check if tag is present
If there is no change then continue
If there wasn't before and is now load new song and start playing
If there was before and isn't now, fade out
If the tag has changed id then change song

# How does the OTA update work

The OTA update checks if there has been an update to the git repo, and if there has been then pull it, rebuild the package and relaunch the application.

This is built on the work done by Dhiraj Patra.
https://dhirajpatra.medium.com/ota-for-python-application-running-in-raspberry-pi-967e3e8d591d

## How does the web app work

The web app is built on flask and multithreaded with the other threads by constructing the app once the multithreading proxies have been initialized.

Flask App
https://www.geeksforgeeks.org/python/how-to-add-authentication-to-your-app-with-flask-login/
https://www.digitalocean.com/community/tutorials/how-to-make-a-web-application-using-flask-in-python-3
https://stackabuse.com/step-by-step-guide-to-file-upload-with-flask/

The raspberry pi will launch its own wifi hotspot when you press the button on the top.
https://www.raspberrypi.com/documentation/computers/configuration.html#enable-hotspot
https://askubuntu.com/questions/155791/how-do-i-sudo-a-command-in-a-script-without-being-asked-for-a-password/155827#155827

Select box for playing the next song.
https://select2.org/getting-started/installation

Additionally, you can back up the files from the TT by downloading a packing with all the songs and the metadata.
No upload has been created yet but this will need to load on top of the previous data.

# How the songs are played

Behind the scenes VLC is used to play the audio. This is controlled with the python vlc bindings. 
This package seems to be built in a C way instead of pythonic so its quite complicated to use.

VLC Python docs, https://www.olivieraubert.net/vlc/python-ctypes/doc/
Loop VLC, https://stackoverflow.com/questions/7214843/repeating-single-movie-using-python-bindings-for-vlc-what-is-a-psz-name


# Todo

- [x] Wiring Diagram
  - [ ] Add a filter for the noise, https://andybrown.me.uk/2015/07/24/usb-filtering/
- [ ] Finalise enclosure
- [x] Basic Software
  - [x] Seamless looping of puck
  - [x] Add a physical button for the looping and get light to toggle when switched in UI
- [x] OTA Update
  - [x] Build Pipeline
- [x] Playback without puck
- [x] Codeless adding of new files
- [x] Type hints and doc strings
- [x] Clean up GPIO after stopping
- [x] Error check and keep backups of the metadata
- [x] VLC to its own thread
- [ ] Add the ability to check if the songs inputs is valid / move to a different selection list


# Install

1. Set up a new raspberry pi
2. Install VLC
3. clone the git repo,
   * `git clone https://github.com/EchoDel/ToddlerTransducer.git`
4. Change to that folder
   * `cd ToddlerTransducer`
5. Copy the service 
   * `sudo cp ./install/ToddlerTransducer.service /etc/systemd/system/ToddlerTransducer.service`
6. Launch the service for the first time
   * `sudo systemctl start ToddlerTransducer.service`
   * Validate that it has started correctly
7. Setup the automated updates
   * `crontab -e`
   * `Add the following;  */5 * * * * /home/pi/ToddlerTransducer/install/ota_update.sh`
