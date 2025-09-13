# Update app.py
from flask import Flask, render_template, request, send_file, redirect, url_for, flash, jsonify
import yt_dlp
import os
import tempfile
from pathlib import Path
import json
import re

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_secret_key_for_development')

class MyLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)

def my_hook(d):
    if d['status'] == 'downloading':
        progress = round(d['downloaded_bytes'] / d['total_bytes'] * 100, 1)
        print(f"Download progress: {progress}%")
        return jsonify({'progress': progress})

def validate_youtube_url(url):
    """Validate if the URL is a valid YouTube URL"""
    youtube_regex = r'^(https?://)?(www\.)?(youtube\.com/(watch\?v=|embed/|v/)|youtu\.be/)[\w-]+'
    return bool(re.match(youtube_regex, url))

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        video_url = request.form.get('video_url', '').strip()
        download_type = request.form.get('download_type', 'video')
        
        if not video_url:
            flash('Please enter a YouTube URL', 'error')
            return redirect(url_for('index'))
        
        if not validate_youtube_url(video_url):
            flash('Please enter a valid YouTube URL (e.g., https://www.youtube.com/watch?v=...)', 'error')
            return redirect(url_for('index'))
            
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                if download_type == 'video':
                    ydl_opts = {
                        'format': 'best[ext=mp4]/best',
                        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                        'quiet': True,
                        'no_warnings': True,
                        'nocheckcertificate': True,
                        'merge_output_format': 'mp4',
                        'prefer_ffmpeg': False,
                        'postprocessors': [],
                        'logger': MyLogger(),
                        'progress_hooks': [my_hook]
                    }
                else:
                    ydl_opts = {
                        'format': 'bestaudio[ext=m4a]/bestaudio',
                        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                        'quiet': True,
                        'no_warnings': True,
                        'nocheckcertificate': True,
                        'prefer_ffmpeg': False,
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        }] if os.system('which ffmpeg') == 0 else [],
                        'logger': MyLogger(),
                        'progress_hooks': [my_hook]
                    }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    try:
                        info = ydl.extract_info(video_url, download=False)
                        title = info.get('title', 'video')
                        
                        # Clean title for filename
                        clean_title = re.sub(r'[<>:"/\\|?*]', '', title)[:50]
                        
                        ydl.download([video_url])
                        
                        # Find the downloaded file
                        files = list(Path(temp_dir).glob('*'))
                        if not files:
                            raise Exception('No file was downloaded')
                        
                        downloaded_file = files[0]
                        
                        # Determine the correct MIME type and filename
                        if download_type == 'video':
                            mimetype = 'video/mp4'
                            if not downloaded_file.suffix.lower() in ['.mp4', '.mkv', '.webm']:
                                # Rename to mp4 if not already
                                new_file = downloaded_file.with_suffix('.mp4')
                                downloaded_file = downloaded_file.rename(new_file)
                            download_name = f"{clean_title}.mp4"
                        else:
                            mimetype = 'audio/mpeg'
                            if not downloaded_file.suffix.lower() in ['.mp3', '.m4a']:
                                # Keep original extension if no conversion happened
                                download_name = f"{clean_title}{downloaded_file.suffix}"
                            else:
                                download_name = f"{clean_title}.mp3"
                        
                        return send_file(
                            str(downloaded_file),
                            as_attachment=True,
                            download_name=download_name,
                            mimetype=mimetype
                        )
                    
                    except yt_dlp.DownloadError as e:
                        error_msg = str(e)
                        if 'Video unavailable' in error_msg:
                            flash('Video is unavailable or private. Please check the URL and try again.', 'error')
                        elif 'Sign in to confirm your age' in error_msg:
                            flash('This video requires age verification. Please try a different video.', 'error')
                        else:
                            flash(f'Download failed: {error_msg}', 'error')
                        return redirect(url_for('index'))
            
        except Exception as e:
            error_message = str(e)
            if '404' in error_message or 'not found' in error_message.lower():
                flash('Video not found. Please check the URL and try again.', 'error')
            elif '403' in error_message or 'forbidden' in error_message.lower():
                flash('Access to this video is restricted. Please try a different video.', 'error')
            elif 'network' in error_message.lower() or 'connection' in error_message.lower():
                flash('Network error. Please check your internet connection and try again.', 'error')
            else:
                flash(f'An unexpected error occurred. Please try again.', 'error')
            return redirect(url_for('index'))
    
    return render_template('index.html')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)