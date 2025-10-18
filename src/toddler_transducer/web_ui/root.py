"""
Web UI Root

Module containing all of the routes for the root page of the application.
"""
import json
from multiprocessing import Process
from multiprocessing.managers import ValueProxy, DictProxy
from pathlib import Path
from uuid import uuid1

from flask import render_template, request, redirect, session, Flask, send_from_directory
from werkzeug.utils import secure_filename

from toddler_transducer.web_ui.html_templates import PLAY_BUTTON, PAUSE_BUTTON
from toddler_transducer.audio_file_manager import get_current_files, backup_audio_files, get_sorted_backup_item
from toddler_transducer.audio import seconds_to_mmss
from toddler_transducer.config import AUDIO_FILE_BASE_PATH
from toddler_transducer.metadata import append_to_metadata, load_metadata


def add_root_routes(flask_app: Flask, rfid_tag_proxy: ValueProxy, vlc_playback_manager: DictProxy):
    """
    Add routes for the root page of the application.

    Args:
        flask_app (Flask): Flask application instance to add routes to.
        rfid_tag_proxy (ValueProxy): Rfid tag proxy instance.
    """
    metadata = load_metadata()

    @flask_app.route('/')
    def home() -> str:
        playable_tracks = get_current_files()
        current_track_uuid = vlc_playback_manager['current_playing_track_uuid']
        track_names = list(playable_tracks.keys())
        current_puck_id = rfid_tag_proxy.value
        session['current_puck_id'] = current_puck_id

        if current_track_uuid is None:
            track_name = 'Load Track'
        else:
            track_name = metadata[current_track_uuid]['track_name']

        if vlc_playback_manager['is_playing']:
            play_status = 'Playing'
            track_length = vlc_playback_manager['track_length']
            track_time = vlc_playback_manager['track_time_through']
            track_length_str = seconds_to_mmss(track_length)
            track_time_str = seconds_to_mmss(track_time)
        else:
            play_status = 'Paused'
            track_length_str = "00:00"
            track_time_str = "00:00"

        if vlc_playback_manager['is_looping']:
            loop_icon_class = 'icon-container-looping'
        else:
            loop_icon_class = 'icon-container'

        html_files = render_template('index.html',
                                     playable_tracks=track_names,
                                     playable_tracks_list=json.dumps(track_names),
                                     track_name=track_name,
                                     play_status=play_status,
                                     play_track_length=track_length_str,
                                     play_current_time=track_time_str,
                                     loop_icon_class=loop_icon_class,
                                     current_puck_id=current_puck_id)
        return html_files

    @flask_app.route('/play_track', methods=['POST'])
    def play_track():

        # if request.form['AudioTrackName'] not in playable_tracks:
        #     if 'Playing' in request.form:
        #         vlc_playback_manager['do_pause'] = True
        #     else:
        #         vlc_playback_manager['do_play'] = True
        #     return redirect(request.referrer)
        # Play the audio track

        playable_tracks = get_current_files()
        vlc_playback_manager['play_track_name'] = playable_tracks[request.form['AudioTrackName']]
        vlc_playback_manager['playback_source'] = 'webui'
        return redirect(request.referrer)

    @flask_app.route('/pause', methods=['POST'])
    def pause_track():
        vlc_playback_manager['do_pause'] = True
        return redirect(request.referrer)

    @flask_app.route('/upload_track', methods=['POST'])
    def upload_track():
        # Play the audio track
        if ('TrackFile' in request.files) and ('current_puck_id' in session):
            file = request.files['TrackFile']
            filename = secure_filename(file.filename)
            # Here you should save the file
            file_extension = Path(filename).suffix
            file_stem = str(uuid1())
            file_name = Path(file_stem).with_suffix(file_extension)

            append_to_metadata(file_stem, str(file_name), session['current_puck_id'], request.form['TrackName'])
            file.save(AUDIO_FILE_BASE_PATH / file_name)

            # Create a new backup of the files
            backup_process = Process(target=backup_audio_files)
            backup_process.start()

        return redirect(request.referrer)

    @flask_app.route('/loop_track', methods=['POST'])
    def loop_track():
        vlc_playback_manager['toggle_looping'] = True
        return redirect(request.referrer)

    @flask_app.route('/backup_audio', methods=['GET'])
    def download_backup():
        latest_backup = get_sorted_backup_item(-1)
        backup_location = next(iter(latest_backup.values()))
        backup_location = Path(__file__).parents[3] / backup_location
        # https://stackoverflow.com/questions/24577349/flask-download-a-file
        return send_from_directory(backup_location.parent, backup_location.name)
