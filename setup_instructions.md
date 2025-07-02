# Media Player Web Application Setup

## Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create the templates directory:**
   ```bash
   mkdir templates
   ```

3. **Save the HTML template:**
   - Save the HTML content as `templates/index.html`

4. **Prepare your media files and playlists**

## Directory Structure
```
media_player/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html        # HTML template
├── Songs_db.db           # SQLite database (auto-created)
├── playlist.m3u          # Sample M3U playlist
└── playlist.json         # Sample JSON playlist
```

## Sample Playlist Files

### M3U Playlist (playlist.m3u)
```
#EXTM3U
#EXTINF:180,Artist Name - Song Title
/path/to/your/music/song1.mp3
#EXTINF:240,Another Artist - Another Song
/path/to/your/music/song2.mp3
/path/to/your/music/song3.flac
```

### JSON Playlist (playlist.json)
```json
[
  {
    "file_path": "/path/to/your/music/song1.mp3",
    "file_id": 1
  },
  {
    "file_path": "/path/to/your/music/song2.mp3", 
    "file_id": 2
  },
  {
    "file_path": "/path/to/your/music/song3.flac",
    "file_id": 3
  }
]
```

## Running the Application

1. **Start the Flask server:**
   ```bash
   python app.py
   ```

2. **Open your web browser and navigate to:**
   ```
   http://localhost:5000
   ```

## Features

### Load Playlist
- Supports `.m3u`, `.m3u8`, and `.json` file formats
- For JSON playlists: Updates database with last played timestamps
- For M3U playlists: Plays files sequentially without database updates
- Displays album art, artist, title, and length for each track
- Continuous playback with no gaps between tracks

### Load File
- Load and play individual media files
- Displays metadata including album art, artist, title, and length
- Supports common audio formats (MP3, FLAC, MP4/M4A)

### Database Integration
- Automatically creates `Songs_db.db` SQLite database
- Updates `last_played` timestamp for JSON playlist tracks
- Table structure: `Songs(ID, file_path, last_played)`

## Supported Audio Formats
- MP3 (with ID3 tags)
- FLAC
- MP4/M4A
- Other formats supported by mutagen library

## Notes

### Browser Limitations
- Due to browser security restrictions, the audio serving functionality works best when:
  - Media files are in the same directory or subdirectory as the application
  - Or you configure proper CORS headers for external file access

### Database Setup
- The Songs table is automatically created on first run
- For JSON playlists to work with database updates, ensure your JSON contains valid `file_id` values that correspond to existing records in the Songs table

### Error Handling
- File not found errors are displayed to the user
- Metadata extraction errors are logged but don't stop playback
- Unsupported file formats show appropriate error messages

## Troubleshooting

1. **Audio files not playing:**
   - Check file paths are correct and accessible
   - Ensure audio files are in supported formats
   - Check browser console for detailed error messages

2. **Metadata not displaying:**
   - Ensure audio files have proper metadata tags
   - Some files may not have embedded album art

3. **Database errors:**
   - Check that the application has write permissions in the directory
   - For JSON playlists, ensure `file_id` values exist in the Songs table