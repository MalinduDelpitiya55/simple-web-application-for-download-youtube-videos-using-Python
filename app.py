from flask import Flask, request, jsonify, render_template, send_file, after_this_request, redirect, url_for
from flask_socketio import SocketIO, emit
import yt_dlp
import os

app = Flask(__name__)
socketio = SocketIO(app)

# Directory for storing downloaded videos
DOWNLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

@app.route("/", methods=["GET", "POST"])
def handler():
    try:
        # Your main function logic
        return jsonify({
            "statusCode": 200,
            "body": "Function executed successfully"
        }), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({
            "statusCode": 500,
            "body": "An internal server error occurred"
        }), 500
@app.route('/get-video-details', methods=['GET'])
def get_video_details():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "URL is required."}), 400

    try:
        ydl = yt_dlp.YoutubeDL()
        info_dict = ydl.extract_info(url, download=False)
        thumbnail = info_dict.get('thumbnail', '')
        title = info_dict.get('title', 'Video')

        return jsonify({"thumbnail": thumbnail, "title": title})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def progress_hook(d):
    if d['status'] == 'downloading':
        total_bytes = d.get('total_bytes')
        downloaded_bytes = d.get('downloaded_bytes')
        speed = d.get('speed')

        if total_bytes and downloaded_bytes:
            percent = round(downloaded_bytes / total_bytes * 100, 2)
            total_mb = round(total_bytes / (1024 * 1024), 2)
            downloaded_mb = round(downloaded_bytes / (1024 * 1024), 2)
            speed_mb_s = round(speed / (1024 * 1024), 2) if speed else 0

            socketio.emit('download_progress', {
                'percent': percent,
                'total_mb': total_mb,
                'downloaded_mb': downloaded_mb,
                'speed': speed_mb_s
            })

@app.route('/download', methods=['POST'])
def download_video():
    data = request.get_json()
    url = data.get('url')
    quality = data.get('quality', 'best')

    if not url:
        return jsonify({"error": "URL is required."}), 400

    try:
        ydl_opts = {
            'format': quality,
            'progress_hooks': [progress_hook],
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(url)
            filename = ydl.prepare_filename(result)

        return jsonify({"message": "Download completed.", "filename": os.path.basename(filename)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download-file/<filename>')
def download_file(filename):
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)

    @after_this_request
    def delete_file(response):
        try:
            os.remove(file_path)
            print(f"File {filename} deleted after download.")
        except Exception as e:
            print(f"Error deleting file {filename}: {e}")
        return response

    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
