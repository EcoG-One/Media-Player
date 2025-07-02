from flask import Flask, render_template, request, jsonify, send_file
import json
import os
import sqlite3
from datetime import datetime
import mutagen
from mutagen.id3 import ID3
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
import base64

app = Flask(__name__)

# Initialize database
def init_db():
    conn = sqlite3.connect('Songs_db.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Songs (
            ID INTEGER PRIMARY KEY,
            file_path TEXT,
            last_played TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Update last played timestamp
def update_last_played(file_id):
    conn = sqlite3.connect('Songs_db.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE Songs SET last_played = CURRENT_TIMESTAMP WHERE ID = ?', (file_id,))
    conn.commit()
    conn.close()

# Extract metadata from audio file
def get_metadata(file_path):
    try:
        audio_file = mutagen.File(file_path)
        if audio_file is None:
            return None
        
        metadata = {
            'artist': '',
            'title': '',
            'length': 0,
            'picture': None
        }
        
        # Get basic info
        if hasattr(audio_file, 'info') and audio_file.info:
            metadata['length'] = int(audio_file.info.length)
        
        # Handle different file types
        if isinstance(audio_file, MP3):
            tags = audio_file.tags
            if tags:
                metadata['artist'] = str(tags.get('TPE1', [''])[0])
                metadata['title'] = str(tags.get('TIT2', [''])[0])
                # Get album art
                for tag in tags.values():
                    if hasattr(tag, 'type') and tag.type == 3:  # Cover image
                        metadata['picture'] = base64.b64encode(tag.data).decode('utf-8')
                        break
        
        elif isinstance(audio_file, FLAC):
            metadata['artist'] = audio_file.get('ARTIST', [''])[0]
            metadata['title'] = audio_file.get('TITLE', [''])[0]
            if audio_file.pictures:
                metadata['picture'] = base64.b64encode(audio_file.pictures[0].data).decode('utf-8')
        
        elif isinstance(audio_file, MP4):
            metadata['artist'] = audio_file.get('\xa9ART', [''])[0]
            metadata['title'] = audio_file.get('\xa9nam', [''])[0]
            if 'covr' in audio_file:
                metadata['picture'] = base64.b64encode(audio_file['covr'][0]).decode('utf-8')
        
        return metadata
    except Exception as e:
        print(f"Error extracting metadata from {file_path}: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/load_playlist', methods=['POST'])
def load_playlist():
    try:
        file_path = request.json.get('file_path')
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 400
        
        playlist = []
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.json':
            with open(file_path, 'r') as f:
                playlist_data = json.load(f)
            
            for media_dic in playlist_data:
                if 'file_path' in media_dic and 'file_id' in media_dic:
                    metadata = get_metadata(media_dic['file_path'])
                    if metadata:
                        playlist.append({
                            'file_path': media_dic['file_path'],
                            'file_id': media_dic['file_id'],
                            'metadata': metadata
                        })
        
        elif file_ext in ['.m3u', '.m3u8']:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    song_path = os.path.split(file_path)[0]
                    song = os.path.join(song_path, line)
                    if line and not line.startswith('#'):
                        metadata = get_metadata(song)
                        if metadata:
                            playlist.append({
                                'file_path': song,
                                'metadata': metadata
                            })
        
        else:
            return jsonify({'error': 'Unsupported file format'}), 400
        
        return jsonify({'playlist': playlist})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/load_file', methods=['POST'])
def load_file():
    try:
        file_path = request.json.get('file_path')
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 400
        
        metadata = get_metadata(file_path)
        if not metadata:
            return jsonify({'error': 'Unable to read media file'}), 400
        
        return jsonify({
            'file_path': file_path,
            'metadata': metadata
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/update_played', methods=['POST'])
def update_played():
    try:
        file_id = request.json.get('file_id')
        if file_id:
            update_last_played(file_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/serve_audio/<path:filename>')
def serve_audio(filename):
    try:
        return send_file(filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 404

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)