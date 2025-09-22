import json
from pathlib import Path
from uuid import uuid1

from flask import render_template, request, redirect
from werkzeug.utils import secure_filename

from .app import flask_app
from ..audio_file_manager import get_current_files
from ..audio import load_track
from ..config import AUDIO_FILE_BASE_PATH
from ..metadata import load_metadata, save_metadata
from ..rfid import get_rfid_id


@flask_app.route('/')
def home():
    playable_tracks = get_current_files()
    track_names = list(playable_tracks.keys())
    html_files = render_template('index.html',
                                 playable_tracks=track_names,
                                 playable_tracks_list=json.dumps(track_names))
    return html_files

@flask_app.route('/play_track', methods=['POST'])
def play_track():
    # Play the audio track
    playable_tracks = get_current_files()
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
