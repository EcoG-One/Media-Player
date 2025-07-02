# Web Media Player
## with Professional Crossfade

## Key Features:

1. **Flask Web Application** - Python backend with HTML/JavaScript frontend
2. **Menu System** - Two main options: "Load Playlist" and "Load File"
3. **Playlist Support** - Handles M3U, M3U8, and JSON formats as specified
4. **Database Integration** - SQLite database with automatic timestamp updates for JSON playlists
5. **Metadata Display** - Shows album art, artist, title, and length from audio file metadata
6. **Continuous Playback** - Seamless playback between tracks with no gaps
7. **Professional Crossfade** - Creates a professional listening experience similar to radio or DJ mixing!

## How it works:
### Load Playlist:

- JSON format: Parses to list of dictionaries with file_path and file_id keys
- M3U/M3U8 format: Reads line by line, ignoring comment lines starting with "#"
- Updates database last_played timestamp for JSON playlist tracks
- Displays metadata for each track during playback

### Load File:

- Loads individual media files
- Extracts and displays metadata (album art, artist, title, length)
- Plays the selected file immediately

### Player:
- Track Starts: Main track plays normally while next track preloads
- 3.5 Seconds Before End: Crossfade begins
- Next track starts playing at volume 0
- Current track begins fading out
- Next track begins fading in
- Crossfade Complete:
    - Current track stops
    - Next track becomes the main track at full volume
    - Display updates to show new track info
    - Process repeats for subsequent tracks

### Crossfade Features:
1. **Dual Audio Elements**

Implements a second hidden audio element (audioPlayerNext) for preloading the next track
Main player remains visible with controls, while the next track loads silently

2. **Preloading System**

preloadNextTrack() function loads the next track in the background
Triggered when a track's metadata loads, ensuring smooth transitions

3. **Crossfade Timing**

Monitors playback time and triggers crossfade exactly 3.5 seconds before track end
Uses timeupdate event to check remaining time continuously

4. **Smooth Crossfade Effect**

*Fade Out:* Current track volume gradually decreases from 100% to 0%
*Fade In:* Next track volume gradually increases from 0% to 100%
Both tracks play simultaneously for exactly 3.5 seconds
50ms intervals for smooth volume transitions (70 steps total)

5. **Seamless Track Switching**

After crossfade completes, seamlessly switches to the next track
Updates display, playlist status, and database timestamps
Resets crossfade state and preloads the following track

### Benefits:

- No Gaps: Continuous music flow with overlapping audio
- Professional Sound: Smooth DJ-style transitions
- Efficient: Preloading prevents delays or stuttering
- Database Integrity: Still updates timestamps correctly
- User Experience: Maintains all original functionality while adding seamless transitions

The crossfade only applies in playlist mode - single file playback remains unchanged. The 3.5-second overlap creates a professional listening experience similar to radio or DJ mixing!

## Technical Implementation:

- Backend: Flask with mutagen library for metadata extraction
- Frontend: Modern, responsive HTML/CSS/JavaScript interface
- Database: SQLite with automatic table creation
- Audio Support: MP3, FLAC, MP4/M4A and other mutagen-supported formats

The application includes proper error handling, a beautiful glassmorphism UI design, and all the database operations you specified. To use it, simply install the dependencies, save the files in the correct structure, and run the Flask application.
