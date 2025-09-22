import json

from flask import render_template, request, redirect

from .app import flask_app
from ..audio_file_manager import get_current_files
from ..audio import load_track


@flask_app.route('/')
def home():
    print(request.form)
    playable_tracks = get_current_files()
    track_names = list(playable_tracks.keys())
    html_files = render_template('index.html',
                                 playable_tracks_list=json.dumps(track_names))
    return html_files

@flask_app.route('/submit', methods=['POST'])
def submit():
    # Play the audio track
    print(request.form['AudioTrack'])
    load_track(track_name=request.form['AudioTrack'])

    return redirect(request.referrer)
