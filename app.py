# Update app.py
from flask import Flask, render_template, request, send_file, redirect, url_for, flash, jsonify
import yt_dlp
import os
import tempfile
from pathlib import Path
import json

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

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        video_url = request.form.get('video_url')
        download_type = request.form.get('download_type', 'video')
        
        if not video_url:
            flash('Please enter a valid YouTube URL', 'error')
            return redirect(url_for('index'))
            
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                if download_type == 'video':
                    ydl_opts = {
                        'format': 'best[ext=mp4]',
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
                        'format': 'bestaudio[ext=m4a]',
                        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                        'quiet': True,
                        'no_warnings': True,
                        'nocheckcertificate': True,
                        'prefer_ffmpeg': False,
                        'postprocessors': [],
                        'logger': MyLogger(),
                        'progress_hooks': [my_hook]
                    }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(video_url, download=False)
                    filename = ydl.prepare_filename(info)
                    
                    ydl.download([video_url])
                    
                    downloaded_file = Path(temp_dir) / filename
                    
                    # For audio, rename the file extension to mp3 if it's not already
                    if download_type == 'audio' and filename.lower().endswith('.m4a'):
                        mp3_filename = filename[:-4] + '.mp3'
                        downloaded_file.rename(mp3_filename)
                        downloaded_file = Path(temp_dir) / mp3_filename
                        
                    return send_file(
                        str(downloaded_file),
                        as_attachment=True,
                        download_name=os.path.basename(str(downloaded_file)),
                        mimetype='video/mp4' if download_type == 'video' else 'audio/mpeg'
                    )
            
        except Exception as e:
            error_message = str(e)
            if '404' in error_message:
                flash('Video not found. Please check the URL and try again.', 'error')
            elif '403' in error_message:
                flash('Access to this video is restricted. Please try a different video.', 'error')
            elif 'ffmpeg' in error_message.lower():
                flash('Error: Audio extraction requires ffmpeg. Try downloading the video instead.', 'error')
            else:
                flash(f'An error occurred: {error_message}', 'error')
            return redirect(url_for('index'))
    
    return render_template('index.html')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)