"""
YouTube Audio Downloader — Backend Server
Flask server that uses yt-dlp to extract audio from YouTube videos.
Run locally on your Mac for personal use.
"""

import os
import json
import uuid
import tempfile
import subprocess
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Directory to temporarily store downloaded audio
DOWNLOAD_DIR = os.path.join(tempfile.gettempdir(), "yt_audio_downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def get_video_info(url: str) -> dict:
    """Extract video metadata without downloading."""
    try:
        print(f"🔍 Extracting info for: {url}")
        result = subprocess.run(
            [
                "yt-dlp",
                "--dump-json",
                "--no-download",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            print(f"❌ yt-dlp error: {result.stderr}")
            raise Exception(result.stderr)

        info = json.loads(result.stdout)
        return {
            "title": info.get("title", "Unknown"),
            "channel": info.get("channel", info.get("uploader", "Unknown")),
            "duration": info.get("duration", 0),
            "thumbnail": info.get("thumbnail", ""),
            "video_id": info.get("id", ""),
        }
    except subprocess.TimeoutExpired:
        raise Exception("Timeout extracting video info")


def download_audio(url: str) -> tuple[str, dict]:
    """Download audio from YouTube URL. Returns (file_path, metadata)."""
    file_id = str(uuid.uuid4())
    output_path = os.path.join(DOWNLOAD_DIR, f"{file_id}.mp3")

    # First get metadata
    metadata = get_video_info(url)

    # Download and convert to MP3
    result = subprocess.run(
        [
            "yt-dlp",
            "-x",                          # Extract audio
            "--audio-format", "mp3",       # Convert to MP3
            "--audio-quality", "0",        # Best quality
            "-o", output_path,             # Output path
            "--no-playlist",               # Don't download playlists
            "--embed-thumbnail",           # Embed thumbnail in file
            "--add-metadata",              # Add metadata
            url,
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode != 0:
        raise Exception(f"Download failed: {result.stderr}")

    # yt-dlp may change extension, find the actual file
    actual_path = output_path
    if not os.path.exists(actual_path):
        # Try finding the file with different extension patterns
        base = os.path.join(DOWNLOAD_DIR, file_id)
        for ext in [".mp3", ".m4a", ".opus", ".webm"]:
            candidate = base + ext
            if os.path.exists(candidate):
                actual_path = candidate
                break

    if not os.path.exists(actual_path):
        raise Exception("Downloaded file not found")

    return actual_path, metadata


@app.route("/info", methods=["POST"])
def info_endpoint():
    """Get video metadata without downloading.

    Request body: {"url": "https://youtube.com/watch?v=..."}
    Response: {"title": "...", "channel": "...", "duration": 123, "thumbnail": "..."}
    """
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"error": "URL is required"}), 400

    url = data["url"]
    try:
        metadata = get_video_info(url)
        return jsonify(metadata)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/download", methods=["POST"])
def download_endpoint():
    """Download audio from YouTube URL.

    Request body: {"url": "https://youtube.com/watch?v=..."}
    Response: Audio file (MP3) with metadata in headers:
        X-Audio-Title, X-Audio-Channel, X-Audio-Duration, X-Audio-Thumbnail
    """
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"error": "URL is required"}), 400

    url = data["url"]
    try:
        file_path, metadata = download_audio(url)

        response = send_file(
            file_path,
            mimetype="audio/mpeg",
            as_attachment=True,
            download_name=f"{metadata['title']}.mp3",
        )

        # Add metadata as custom headers (URL-encoded for safety)
        from urllib.parse import quote
        response.headers["X-Audio-Title"] = quote(metadata["title"])
        response.headers["X-Audio-Channel"] = quote(metadata["channel"])
        response.headers["X-Audio-Duration"] = str(metadata["duration"])
        response.headers["X-Audio-Thumbnail"] = metadata.get("thumbnail", "")
        response.headers["X-Audio-VideoId"] = metadata.get("video_id", "")

        return response

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/", methods=["GET"])
def index():
    """Home route for verification."""
    return jsonify({
        "status": "online",
        "message": "YouTube Audio Backend is Live!",
        "version": "1.1.0"
    })


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"})


@app.route("/cleanup", methods=["POST"])
def cleanup():
    """Clean up temporary download files."""
    count = 0
    for f in os.listdir(DOWNLOAD_DIR):
        try:
            os.remove(os.path.join(DOWNLOAD_DIR, f))
            count += 1
        except OSError:
            pass
    return jsonify({"cleaned": count})


if __name__ == "__main__":
    # Get port from environment variable (required for Render/Heroku)
    port = int(os.environ.get("PORT", 5555))
    
    print("🎵 YouTube Audio Downloader Server (Cloud Ready)")
    print(f"📁 Temp dir: {DOWNLOAD_DIR}")
    print(f"🌐 Running on port {port}")
    print("=" * 40)
    app.run(host="0.0.0.0", port=port)
