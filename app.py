import os
import yt_dlp
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DOWNLOAD_FOLDER = os.path.join(os.getcwd(), 'downloads')
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/info', methods=['POST'])
def get_video_info():
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Extract relevant formats (video + audio best combinations or specific resolutions)
            # Simplified approach: return list of available formats that have video
            formats = []
            seen_res = set()
            
            # Sort formats by resolution height (descending)
            all_formats = info.get('formats', [])
            # Filter for mp4/useful formats
            for f in all_formats:
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                    # It's a progressive stream (video+audio)
                    res = f.get('height')
                    if res and res not in seen_res:
                        formats.append({
                            'format_id': f['format_id'],
                            'resolution': f'{res}p',
                            'ext': f['ext'],
                            'filesize': f.get('filesize'),
                            'label': f"{res}p ({f['ext']})"
                        })
                        seen_res.add(res)
            
            # Also add best video-only streams combined with best audio if needed? 
            # For simplicity in this "BulkTube", let's stick to progressive or let yt-dlp merge them if we request 'bestvideo+bestaudio'.
            # BUT, user wants to SELECT quality.
            # Usually, yt-dlp handles merging. If we want specific resolution, we pass it.
            # Let's just offer generic "Best", "1080p", "720p", "480p" etc. and let yt-dlp pick the format.
            
            # Refined approach: Just return the metadata and let user pick "Best" or common resolutions.
            # or better: Return actual available resolutions.
            
            # Simple list of common resolutions to check availability against 'formats':
            available_resolutions = []
            for f in all_formats:
                if f.get('height'):
                    available_resolutions.append(f.get('height'))
            
            available_resolutions = sorted(list(set(available_resolutions)), reverse=True)
            resolution_options = [{'id': f'best', 'label': 'Best Quality'}]
            for res in available_resolutions:
                resolution_options.append({'id': str(res), 'label': f'{res}p'})

            return jsonify({
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration_string'),
                'url': url,
                'qualities': resolution_options
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download', methods=['POST'])
def download_video():
    data = request.json
    url = data.get('url')
    quality = data.get('quality', 'best') # 'best' or '1080', '720' etc.

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    # Simplified robust approach for systems without FFMPEG
    # "SABR" warnings and "fragment not found" indicate we shouldn't use default web client for HLS.
    # We switch to 'android' client which usually serves standard progressive streams or working HLS.
    
    ydl_opts = {
        'format': 'best[ext=mp4]/best', # Prefer mp4, fallback to best available
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
        'quiet': False,
        'nocheckcertificate': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios'] # Try mobile clients first
            }
        }
    }
    
    if quality != 'best':
         ydl_opts['format'] = f'best[height<={quality}][ext=mp4]/best[height<={quality}]'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return jsonify({'status': 'success', 'message': 'Download started/completed'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
