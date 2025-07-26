from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
import mysql.connector
from mysql.connector import Error
import json
import os
import mutagen
from mutagen.id3 import ID3
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from datetime import datetime
import glob
from pathlib import Path

app = Flask(__name__)

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '$jla63000M',
    'database': 'Songs_db'
}

# Global variables
slot = {"genre": "", "mood": "", "year": 0, "tempo": 0, "rotation": 0}
clock = []

def create_database():
    """Create database and table if they don't exist"""
    try:
        # Connect without specifying database first
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cursor = conn.cursor()
        
        # Create database if it doesn't exist
        cursor.execute("CREATE DATABASE IF NOT EXISTS Songs_db")
        cursor.execute("USE Songs_db")
        
        # Create table if it doesn't exist
        create_table_query = """
        CREATE TABLE IF NOT EXISTS Songs (
            id INT NOT NULL AUTO_INCREMENT,
            path CHAR(255) NOT NULL,
            file_name CHAR(120) NOT NULL,
            artist CHAR(120) NOT NULL,
            song_title CHAR(120) NOT NULL,
            duration INT NOT NULL,
            end CHAR(1),
            genre CHAR(80),
            mood CHAR(80),
            year SMALLINT,
            tempo SMALLINT,
            rotation SMALLINT,
            last_played TIMESTAMP DEFAULT '2000-01-01 00:00:01',
            play_history TEXT,
            PRIMARY KEY (id)
        )
        """
        cursor.execute(create_table_query)
        conn.commit()
        
        cursor.close()
        conn.close()
        return True
        
    except Error as e:
        print(f"Error creating database: {e}")
        return False

def get_db_connection():
    """Get database connection"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Database connection error: {e}")
        return None

def extract_metadata(file_path):
    """Extract metadata from audio file"""
    try:
        audio_file = mutagen.File(file_path)
        if audio_file is None:
            return None
        
        metadata = {
            'artist': '',
            'title': '',
            'duration': 0,
            'genre': '',
            'mood': '',
            'year': 0,
            'tempo': 0
        }
        
        # Get basic info
        if hasattr(audio_file, 'info') and audio_file.info:
            metadata['duration'] = int(audio_file.info.length)
        
        # Handle different file types
        if isinstance(audio_file, MP3):
            tags = audio_file.tags
            if tags:
                metadata['artist'] = str(tags.get('TPE1', [''])[0])
                metadata['title'] = str(tags.get('TIT2', [''])[0])
                metadata['genre'] = str(tags.get('TCON', [''])[0])
                metadata['mood'] = str(tags.get('TMOO', [''])[0])
                year_tag = tags.get('TDRC', [''])[0]
                if year_tag:
                    metadata['year'] = int(str(year_tag)[:4]) if str(year_tag)[:4].isdigit() else 0
                tempo_tag = tags.get('TBPM', [''])[0]
                if tempo_tag:
                    metadata['tempo'] = int(str(tempo_tag)) if str(tempo_tag).isdigit() else 0
        
        elif isinstance(audio_file, FLAC):
            metadata['artist'] = audio_file.get('ARTIST', [''])[0]
            metadata['title'] = audio_file.get('TITLE', [''])[0]
            metadata['genre'] = audio_file.get('GENRE', [''])[0]
            metadata['mood'] = audio_file.get('MOOD', [''])[0]
            year_str = audio_file.get('DATE', [''])[0]
            if year_str and year_str[:4].isdigit():
                metadata['year'] = int(year_str[:4])
            tempo_str = audio_file.get('BPM', [''])[0]
            if tempo_str and tempo_str.isdigit():
                metadata['tempo'] = int(tempo_str)
        
        elif isinstance(audio_file, MP4):
            metadata['artist'] = audio_file.get('\xa9ART', [''])[0]
            metadata['title'] = audio_file.get('\xa9nam', [''])[0]
            metadata['genre'] = audio_file.get('\xa9gen', [''])[0]
            year_tuple = audio_file.get('\xa9day', [''])
            if year_tuple and len(year_tuple) > 0:
                year_str = str(year_tuple[0])
                if year_str[:4].isdigit():
                    metadata['year'] = int(year_str[:4])
        
        return metadata
    except Exception as e:
        print(f"Error extracting metadata from {file_path}: {e}")
        return None

@app.route('/')
def index():
    return render_template('radio_scheduler.html')


@app.route('/scan_library', methods=['GET', 'POST'])
def scan_library():
    if request.method == 'POST':
        # Handle multiple directory paths
        folder_paths_input = request.form.get('folder_paths', '').strip()

        if not folder_paths_input:
            return jsonify({'error': 'No folder paths provided'}), 400

        # Split paths by newlines and clean them up
        folder_paths = [path.strip() for path in folder_paths_input.split('\n') if path.strip()]

        # Validate all paths exist
        invalid_paths = []
        valid_paths = []

        for path in folder_paths:
            if os.path.exists(path) and os.path.isdir(path):
                valid_paths.append(path)
            else:
                invalid_paths.append(path)

        if not valid_paths:
            return jsonify({'error': 'No valid folder paths found'}), 400

        if invalid_paths:
            return jsonify({
                'warning': f'Some paths were invalid and skipped: {", ".join(invalid_paths)}',
                'valid_paths': valid_paths
            }), 400

        try:
            conn = get_db_connection()
            if not conn:
                return jsonify({'error': 'Database connection failed'}), 500

            cursor = conn.cursor(dictionary=True)
            audio_extensions = ['.mp3', '.flac', '.m4a', '.wav', '.ogg']

            # Statistics
            files_added = 0
            files_updated = 0
            files_removed = 0

            # Step 1: Get all existing files from database (normalize paths)
            cursor.execute("SELECT id, path, file_name, artist, song_title, duration, genre, mood, year, tempo FROM Songs")
            db_files = cursor.fetchall()
            existing_files = {}
            for row in db_files:
                # Normalize path for comparison
                abs_path = os.path.abspath(row['path']) if os.path.exists(row['path']) else row['path']
                existing_files[abs_path] = row

            # Step 2: Scan all folders and collect all current audio files
            current_files = {}
            scanned_directories = []

            for folder_path in valid_paths:
                scanned_directories.append(folder_path)
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        if any(file.lower().endswith(ext) for ext in audio_extensions):
                            file_path = os.path.join(root, file)
                            # Use absolute path to avoid duplicates
                            abs_path = os.path.abspath(file_path)
                            current_files[abs_path] = file

            # Step 3: Add new files and update existing ones
            for file_path, file_name in current_files.items():
                metadata = extract_metadata(file_path)

                if not metadata:
                    continue  # Skip files with extraction errors

                # Normalize the file path for storage
                normalized_path = os.path.abspath(file_path)

                if normalized_path not in existing_files:
                    # New file - add to database
                    insert_query = """
                    INSERT INTO Songs (path, file_name, artist, song_title, duration, 
                                     genre, mood, year, tempo, rotation, last_played)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    values = (
                        file_path, file_name, metadata['artist'], metadata['title'],
                        metadata['duration'], metadata['genre'], metadata['mood'],
                        metadata['year'], metadata['tempo'], 1, '2000-01-01 00:00:01'
                    )
                    cursor.execute(insert_query, values)
                    files_added += 1

                else:
                    # Existing file - check if metadata has changed
                    existing = existing_files[normalized_path]

                    # Compare metadata fields
                    metadata_changed = (
                        existing['artist'] != metadata['artist'] or
                        existing['song_title'] != metadata['title'] or
                        existing['duration'] != metadata['duration'] or
                        existing['genre'] != metadata['genre'] or
                        existing['mood'] != metadata['mood'] or
                        existing['year'] != metadata['year'] or
                        existing['tempo'] != metadata['tempo'] or
                        existing['file_name'] != file_name
                    )

                    if metadata_changed:
                        # Update existing record
                        update_query = """
                        UPDATE Songs SET file_name=%s, artist=%s, song_title=%s, duration=%s, 
                                       genre=%s, mood=%s, year=%s, tempo=%s 
                        WHERE id=%s
                        """
                        values = (
                            file_name, metadata['artist'], metadata['title'],
                            metadata['duration'], metadata['genre'], metadata['mood'],
                            metadata['year'], metadata['tempo'], existing['id']
                        )
                        cursor.execute(update_query, values)
                        files_updated += 1

            # Step 4: Remove entries for files that no longer exist
            for normalized_path, db_record in existing_files.items():
                if normalized_path not in current_files:
                    # File no longer exists - remove from database
                    cursor.execute("DELETE FROM Songs WHERE id = %s", (db_record['id'],))
                    files_removed += 1

            conn.commit()
            cursor.close()
            conn.close()

            # Prepare result message
            results = []
            if files_added > 0:
                results.append(f'{files_added} files added')
            if files_updated > 0:
                results.append(f'{files_updated} files updated')
            if files_removed > 0:
                results.append(f'{files_removed} files removed')

            if not results:
                message = 'Library scan completed - no changes detected'
            else:
                message = f'Library scan completed: {", ".join(results)}'

            return jsonify({
                'message': message,
                'details': {
                    'added': files_added,
                    'updated': files_updated,
                    'removed': files_removed,
                    'total_scanned': len(current_files),
                    'directories_scanned': scanned_directories,
                    'valid_paths_count': len(valid_paths)
                }
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return render_template('scan_library.html')


@app.route('/edit_songs', methods=['GET', 'POST'])
def edit_songs():
    if request.method == 'POST':
        if 'search' in request.form:
            # Search for songs
            search_term = request.form.get('search_term', '')
            search_field = request.form.get('search_field', 'artist')

            try:
                conn = get_db_connection()
                cursor = conn.cursor(dictionary=True)

                query = f"SELECT * FROM Songs WHERE {search_field} LIKE %s"
                cursor.execute(query, (f'%{search_term}%',))
                results = cursor.fetchall()

                cursor.close()
                conn.close()

                return render_template('edit_songs.html', results=results,
                                       search_performed=True)

            except Exception as e:
                return render_template('edit_songs.html', error=str(e))

        elif 'update' in request.form:
            # Update song
            try:
                song_id = request.form.get('song_id')

                conn = get_db_connection()
                cursor = conn.cursor()

                update_query = """
                UPDATE Songs SET artist=%s, song_title=%s, duration=%s, genre=%s, 
                               mood=%s, year=%s, tempo=%s, rotation=%s 
                WHERE id=%s
                """
                values = (
                    request.form.get('artist', ''),
                    request.form.get('song_title', ''),
                    int(request.form.get('duration', 0)),
                    request.form.get('genre', ''),
                    request.form.get('mood', ''),
                    int(request.form.get('year', 0)),
                    int(request.form.get('tempo', 0)),
                    int(request.form.get('rotation', 1)),
                    song_id
                )

                cursor.execute(update_query, values)
                conn.commit()

                # Get the updated search results to maintain context
                # Reconstruct the original search parameters from the form data
                # (You'll need to add hidden fields to the edit form for this)
                original_search_term = request.form.get('original_search_term',
                                                        '')
                original_search_field = request.form.get(
                    'original_search_field', 'artist')

                if original_search_term and original_search_field:
                    # Re-run the search to get updated results
                    cursor = conn.cursor(dictionary=True)
                    query = f"SELECT * FROM Songs WHERE {original_search_field} LIKE %s"
                    cursor.execute(query, (f'%{original_search_term}%',))
                    results = cursor.fetchall()

                    cursor.close()
                    conn.close()

                    return render_template('edit_songs.html',
                                           success='Song updated successfully',
                                           results=results,
                                           search_performed=True)
                else:
                    cursor.close()
                    conn.close()
                    return render_template('edit_songs.html',
                                           success='Song updated successfully')

            except Exception as e:
                return render_template('edit_songs.html', error=str(e))

    return render_template('edit_songs.html')


@app.route('/serve_audio')
def serve_audio():
    """Serve audio files for playback"""
    file_path = request.args.get('path')

    if not file_path or not os.path.exists(file_path):
        return "File not found", 404

    try:
        # Security check: ensure the file is within allowed directories
        # You might want to restrict this to specific directories for security
        if not os.path.isfile(file_path):
            return "Invalid file", 404

        # Get file extension to determine MIME type
        file_ext = os.path.splitext(file_path)[1].lower()
        mime_types = {
            '.mp3' : 'audio/mpeg',
            '.flac': 'audio/flac',
            '.m4a' : 'audio/mp4',
            '.wav' : 'audio/wav',
            '.ogg' : 'audio/ogg'
        }

        mime_type = mime_types.get(file_ext, 'audio/mpeg')

        return send_file(file_path, mimetype=mime_type)

    except Exception as e:
        print(f"Error serving audio file: {e}")
        return "Error serving file", 500

@app.route('/create_clock', methods=['GET', 'POST'])
def create_clock():
    global clock, slot
    
    if request.method == 'POST':
        if 'add_slot' in request.form:
            # Add slot to clock
            slot = {
                'genre': request.form.get('genre', ''),
                'mood': request.form.get('mood', ''),
                'year': int(request.form.get('year', 0)),
                'tempo': int(request.form.get('tempo', 0)),
                'rotation': int(request.form.get('rotation', 1))
            }
            clock.append(slot.copy())
            return render_template('create_clock.html', clock=clock, success='Slot added successfully')
        
        elif 'finish' in request.form:
            # Save clock to JSON file
            filename = request.form.get('filename', 'clock.json')
            if not filename.endswith('.json'):
                filename += '.json'
            
            try:
                with open(filename, 'w') as f:
                    json.dump(clock, f, indent=2)
                
                clock = []  # Empty the clock
                return render_template('create_clock.html', success=f'Clock saved as {filename}')
            
            except Exception as e:
                return render_template('create_clock.html', error=str(e))
    
    return render_template('create_clock.html', clock=clock)

@app.route('/edit_clock', methods=['GET', 'POST'])
def edit_clock():
    global clock
    
    if request.method == 'POST':
        if 'load' in request.form:
            # Load clock from JSON file
            file_path = request.form.get('file_path')
            try:
                with open(file_path, 'r') as f:
                    clock = json.load(f)
                return render_template('edit_clock.html', clock=clock, loaded=True, file_path=file_path)
            
            except Exception as e:
                return render_template('edit_clock.html', error=str(e))
        
        elif 'save' in request.form:
            # Save edited clock
            file_path = request.form.get('original_file_path')
            try:
                # Update clock with form data
                for i in range(len(clock)):
                    clock[i] = {
                        'genre': request.form.get(f'genre_{i}', ''),
                        'mood': request.form.get(f'mood_{i}', ''),
                        'year': int(request.form.get(f'year_{i}', 0)),
                        'tempo': int(request.form.get(f'tempo_{i}', 0)),
                        'rotation': int(request.form.get(f'rotation_{i}', 1))
                    }
                
                with open(file_path, 'w') as f:
                    json.dump(clock, f, indent=2)
                
                clock = []  # Empty the clock
                return render_template('edit_clock.html', success='Clock updated successfully')
            
            except Exception as e:
                return render_template('edit_clock.html', error=str(e))
    
    return render_template('edit_clock.html')

@app.route('/combine_clocks', methods=['GET', 'POST'])
def combine_clocks():
    if request.method == 'POST':
        file_paths = request.form.getlist('file_paths')
        filename = request.form.get('filename', 'combined_clock.json')
        
        if not filename.endswith('.json'):
            filename += '.json'
        
        try:
            clocks = []
            for file_path in file_paths:
                if file_path.strip():
                    with open(file_path.strip(), 'r') as f:
                        clock_data = json.load(f)
                        clocks.extend(clock_data)
            
            with open(filename, 'w') as f:
                json.dump(clocks, f, indent=2)
            
            return render_template('combine_clocks.html', success=f'Combined clocks saved as {filename}')
        
        except Exception as e:
            return render_template('combine_clocks.html', error=str(e))
    
    return render_template('combine_clocks.html')

@app.route('/create_playlist', methods=['GET', 'POST'])
def create_playlist():
    if request.method == 'POST':
        file_path = request.form.get('file_path')
        playlist_filename = request.form.get('playlist_filename', 'playlist.json')
        
        if not playlist_filename.endswith('.json'):
            playlist_filename += '.json'
        
        try:
            # Load clock file
            with open(file_path, 'r') as f:
                clocks = json.load(f)
            
            # Create playlist
            playlist = []
            file_paths = []
            
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            for slot in clocks:
                # Build WHERE clause based on non-empty slot values
                where_conditions = []
                params = []
                
                if slot.get('genre'):
                    where_conditions.append("genre = %s")
                    params.append(slot['genre'])
                if slot.get('mood'):
                    where_conditions.append("mood = %s")
                    params.append(slot['mood'])
                if slot.get('year'):
                    where_conditions.append("year = %s")
                    params.append(slot['year'])
                if slot.get('tempo'):
                    where_conditions.append("tempo = %s")
                    params.append(slot['tempo'])
                if slot.get('rotation'):
                    where_conditions.append("rotation = %s")
                    params.append(slot['rotation'])
                
                if where_conditions:
                    where_clause = " AND ".join(where_conditions)
                    query = f"SELECT * FROM Songs WHERE {where_clause} ORDER BY last_played ASC LIMIT 1"
                    cursor.execute(query, params)
                else:
                    # If no conditions, get any song with minimum last_played
                    query = "SELECT * FROM Songs ORDER BY last_played ASC LIMIT 1"
                    cursor.execute(query)
                
                result = cursor.fetchone()
                if result:
                    file_path_combined = os.path.join(result['path'])
                    playlist_item = {
                        'file_path': file_path_combined,
                        'file_id': result['id']
                    }
                    playlist.append(playlist_item)
                    file_paths.append(file_path_combined)
            
            cursor.close()
            conn.close()
            
            # Save playlist JSON
            with open(playlist_filename, 'w') as f:
                json.dump(playlist, f, indent=2)
            
            # Save M3U file
            m3u_filename = playlist_filename.replace('.json', '.m3u')
            with open(m3u_filename, 'w') as f:
                f.write('#EXTM3U\n')
                for file_path in file_paths:
                    f.write(f'{file_path}\n')
            
            return render_template('create_playlist.html', 
                                 success=f'Playlist saved as {playlist_filename} and {m3u_filename}',
                                 playlist_count=len(playlist))
        
        except Exception as e:
            return render_template('create_playlist.html', error=str(e))
    
    return render_template('create_playlist.html')

if __name__ == '__main__':
    # Initialize database
    if create_database():
        print("Database initialized successfully")
    else:
        print("Failed to initialize database")
    
    app.run(debug=True, host='0.0.0.0', port=5000)