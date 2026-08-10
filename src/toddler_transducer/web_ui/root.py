"""
Web UI Root

Module containing all of the routes for the root page of the application.
"""
import subprocess
from multiprocessing import Process
from multiprocessing.managers import ValueProxy, DictProxy
from pathlib import Path
from shutil import disk_usage
from uuid import uuid1

from flask import render_template, request, redirect, session, Flask, send_from_directory
from werkzeug.utils import secure_filename

from toddler_transducer.audio_file_manager import get_current_files, backup_audio_files, get_sorted_backup_item
from toddler_transducer.audio import seconds_to_mmss, save_volume, save_puck_lockout
from toddler_transducer.config import AUDIO_FILE_BASE_PATH
from toddler_transducer.metadata import append_to_metadata, load_metadata, remove_from_metadata_by_track_name


def add_root_routes(flask_app: Flask, rfid_tag_proxy: ValueProxy,
                    vlc_playback_manager: DictProxy) -> None:
    """Register all web UI routes on the Flask app.

    Args:
        flask_app: Flask application instance.
        rfid_tag_proxy: Proxy for the current RFID tag id.
        vlc_playback_manager: Shared dict for VLC control and state.
    """

    def resolve_track_name(track_uuid: str | None) -> str:
        """Look up the display name for a track UUID.

        Returns:
            str: The track display name, or 'Load Track' if unknown.
        """
        if track_uuid is None:
            return 'Load Track'
        meta = load_metadata()
        entry = meta.get(track_uuid)
        return entry['track_name'] if entry else 'Load Track'

    @flask_app.route('/')
    def home() -> str:
        """Render the home page with player state and track list."""
        playable_tracks = get_current_files()
        current_track_uuid = vlc_playback_manager['current_playing_track_uuid']
        track_names = list(playable_tracks.keys())
        current_puck_id = rfid_tag_proxy.value
        session['current_puck_id'] = current_puck_id

        track_name = resolve_track_name(current_track_uuid)

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
            loop_icon_class = 'loop-active'
        else:
            loop_icon_class = ''

        html_files = render_template('index.html',
                                     playable_tracks=track_names,
                                     track_name=track_name,
                                     play_status=play_status,
                                     play_track_length=track_length_str,
                                     play_current_time=track_time_str,
                                     loop_icon_class=loop_icon_class,
                                     volume=vlc_playback_manager.get('volume', 50),
                                     current_puck_id=current_puck_id)
        return html_files

    @flask_app.route('/play_track', methods=['POST'])
    def play_track():
        """Play a track selected via form submission."""
        playable_tracks = get_current_files()
        vlc_playback_manager['play_rfid_id'] = False
        vlc_playback_manager['play_track_name'] = playable_tracks[request.form['AudioTrackName']]
        vlc_playback_manager['playback_source'] = 'webui'
        return redirect(request.referrer)

    @flask_app.route('/pause', methods=['POST'])
    def pause_track():
        """Pause playback via form submission."""
        vlc_playback_manager['do_pause'] = True
        return redirect(request.referrer)

    @flask_app.route('/upload_track', methods=['POST'])
    def upload_track():
        """Upload an audio file and create a metadata entry."""
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

    @flask_app.route('/api/seek', methods=['POST'])
    def api_seek():
        """Seek to a position in the current track."""
        data = request.get_json()
        if data and 'position' in data:
            vlc_playback_manager['seek_position'] = float(data['position'])
        return {'ok': True}

    @flask_app.route('/api/volume', methods=['POST'])
    def api_volume():
        """Set the playback volume."""
        data = request.get_json()
        if data and 'volume' in data:
            vol = max(0, min(100, int(data['volume'])))
            vlc_playback_manager['volume'] = vol
            save_volume(vol)
        return {'ok': True}

    @flask_app.route('/api/puck_lockout', methods=['GET'])
    def api_get_puck_lockout():
        """Return the current puck lockout state."""
        return {'puck_lockout': vlc_playback_manager.get('puck_lockout', False)}

    @flask_app.route('/api/puck_lockout', methods=['POST'])
    def api_set_puck_lockout():
        """Set the puck lockout state."""
        data = request.get_json()
        if data and 'puck_lockout' in data:
            locked = bool(data['puck_lockout'])
            vlc_playback_manager['puck_lockout'] = locked
            save_puck_lockout(locked)
        return {'ok': True}

    @flask_app.route('/api/player_state')
    def api_player_state():
        """Return the full player state as JSON."""
        current_track_uuid = vlc_playback_manager['current_playing_track_uuid']
        track_name = resolve_track_name(current_track_uuid)
        return {
            'is_playing': vlc_playback_manager['is_playing'],
            'is_looping': vlc_playback_manager['is_looping'],
            'track_name': track_name,
            'track_length': vlc_playback_manager['track_length'],
            'track_time': vlc_playback_manager['track_time_through'],
            'volume': vlc_playback_manager.get('volume', 50),
            'puck_lockout': vlc_playback_manager.get('puck_lockout', False),
        }

    @flask_app.route('/api/play_track', methods=['POST'])
    def api_play_track():
        """Play a track by name via JSON API."""
        data = request.get_json()
        if data and 'track_name' in data:
            playable_tracks = get_current_files()
            if data['track_name'] in playable_tracks:
                vlc_playback_manager['play_rfid_id'] = False
                vlc_playback_manager['play_track_name'] = playable_tracks[data['track_name']]
                vlc_playback_manager['playback_source'] = 'webui'
        return {'ok': True}

    @flask_app.route('/api/toggle_playback', methods=['POST'])
    def api_toggle_playback():
        """Toggle between play and pause."""
        if vlc_playback_manager['is_playing']:
            vlc_playback_manager['do_pause'] = True
        else:
            vlc_playback_manager['do_play'] = True
        return {'ok': True}

    @flask_app.route('/api/toggle_loop', methods=['POST'])
    def api_toggle_loop():
        """Toggle looping on the current track."""
        vlc_playback_manager['toggle_looping'] = True
        return {'ok': True}

    @flask_app.route('/api/tracks')
    def api_tracks():
        """Return a list of track entries with UUIDs."""
        playable_tracks = get_current_files()
        meta = load_metadata()
        entries = []
        for name, filename in playable_tracks.items():
            for uuid, entry in meta.items():
                if entry.get('file_name') == filename:
                    entries.append({'uuid': uuid, 'track_name': name})
                    break
        return {'tracks': entries}

    @flask_app.route('/api/disk_usage')
    def api_disk_usage():
        """Return disk usage stats for the audio files directory."""
        usage = disk_usage(AUDIO_FILE_BASE_PATH)
        return {
            'total': usage.total,
            'used': usage.used,
            'free': usage.free,
        }

    @flask_app.route('/api/delete_track', methods=['POST'])
    def api_delete_track():
        """Delete a track by name via JSON API."""
        data = request.get_json()
        if data and 'track_name' in data:
            removed = remove_from_metadata_by_track_name(data['track_name'])
            if removed:
                file_path = AUDIO_FILE_BASE_PATH / removed['file_name']
                if file_path.exists():
                    file_path.unlink()
                vlc_playback_manager['play_rfid_id'] = False
                if vlc_playback_manager.get('current_playing_track_uuid') == removed.get('uuid'):
                    vlc_playback_manager['do_stop'] = True
                return {'ok': True}
        return {'ok': False}, 400

    @flask_app.route('/loop_track', methods=['POST'])
    def loop_track():
        """Toggle looping via form submission."""
        vlc_playback_manager['toggle_looping'] = True
        return redirect(request.referrer)

    @flask_app.route('/backup_audio', methods=['GET'])
    def download_backup():
        """Download the latest audio backup ZIP."""
        latest_backup = get_sorted_backup_item(1)
        backup_location = next(iter(latest_backup.values()))
        backup_location = Path(__file__).parents[3] / backup_location
        # https://stackoverflow.com/questions/24577349/flask-download-a-file
        return send_from_directory(backup_location.parent, backup_location.name)

    @flask_app.route('/api/restart_service', methods=['POST'])
    def api_restart_service():
        """Restart the systemd ToddlerTransducer service."""
        try:
            subprocess.Popen(
                ['sudo', 'systemctl', 'restart', 'ToddlerTransducer.service'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return {'ok': True}
        except Exception:
            return {'ok': False}, 500
