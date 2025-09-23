import json
from pathlib import Path
from uuid import uuid1

from flask import render_template, request, redirect
from werkzeug.utils import secure_filename

from .app import flask_app
from .html_templates import PLAY_BUTTON, PAUSE_BUTTON
from ..audio_file_manager import get_current_files
from ..audio import load_track, get_playing_track, is_playing
from ..config import AUDIO_FILE_BASE_PATH
from ..metadata import load_metadata, save_metadata
from ..rfid import get_rfid_id


@flask_app.route('/')
def home() -> str:
    playable_tracks = get_current_files()
    current_track_metadata = get_playing_track()
    track_names = list(playable_tracks.keys())

    if current_track_metadata is None:
        track_name = 'Track Name'
    else:
        track_name = current_track_metadata['track_name']

    if is_playing():
        play_status_icon = PAUSE_BUTTON
    else:
        play_status_icon = PLAY_BUTTON

    html_files = render_template('index.html',
                                 playable_tracks=track_names,
                                 playable_tracks_list=json.dumps(track_names),
                                 track_name=track_name,
                                 play_status_icon=play_status_icon)
    return html_files

@flask_app.route('/play_track', methods=['POST'])
def play_track():
    playable_tracks = get_current_files()
    if request.form['AudioTrackName'] not in playable_tracks:
        return redirect(request.referrer)
    # Play the audio track
    load_track(track_name=playable_tracks[request.form['AudioTrackName']])
    return redirect(request.referrer)

@flask_app.route('/upload_track', methods=['POST'])
def upload_track():
    # Play the audio track
    if 'TrackFile' in request.files:
        file = request.files['TrackFile']
        filename = secure_filename(file.filename)
        # Here you should save the file
        file_extension = Path(filename).suffix
        file_stem = str(uuid1())
        file_name = Path(file_stem).with_suffix(file_extension)

        metadata = load_metadata()
        metadata[file_stem] = {'file_name': str(file_name),
                               'rfid_id': get_rfid_id(),
                               'track_name': request.form['TrackName']}

        save_metadata(metadata)
        file.save(AUDIO_FILE_BASE_PATH / file_name)

    return redirect(request.referrer)
