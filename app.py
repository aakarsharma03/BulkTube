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
            formats = []
            seen_res = set()
            available_resolutions = []
            
            all_formats = info.get('formats', [])
            
            # If no formats found, it might be a direct file (common in some extractors like Instagram)
            if not all_formats and info.get('url'):
                 # It's likely a single file
                 pass 

            # Filter for mp4/useful formats if they exist
            if all_formats:
                for f in all_formats:
                    # Check for video streams (some might not have acodec if it's video-only, but we want ready-to-play)
                    # For Instagram, often 'vcodec' is not 'none' and 'acodec' is not 'none' usually works,
                    # but sometimes simple file entries don't have these clearly defined.
                    is_video = f.get('vcodec') != 'none'
                    # Some inputs might be direct video files
                    
                    if is_video:
                        res = f.get('height')
                        if res:
                            available_resolutions.append(res)
            
            available_resolutions = sorted(list(set(available_resolutions)), reverse=True)
            
            resolution_options = [{'id': 'best', 'label': 'Best Quality'}]
            
            if available_resolutions:
                for res in available_resolutions:
                    resolution_options.append({'id': str(res), 'label': f'{res}p'})
            
            # Fallback if no specific resolutions found but we have a valid video
            # (common for some Instagram videos where we just get one "one quality")
            if not resolution_options and (info.get('url') or all_formats):
                 resolution_options = [{'id': 'best', 'label': 'Best Quality'}]

            return jsonify({
                'title': info.get('title') or 'Video',
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
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s [%(id)s].%(ext)s'),
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
