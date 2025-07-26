import os
import subprocess
from flask import Flask, request, render_template, send_from_directory, redirect, url_for, flash
from pydub import AudioSegment

app = Flask(__name__)
app.secret_key = 'rahasia123'

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
ALLOWED_EXTENSIONS = {'mp4', 'mp3', 'wav'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def combine_instrumental(folder_path): 
    bass_path = os.path.join(folder_path, "bass.wav")
    drums_path = os.path.join(folder_path, "drums.wav")
    other_path = os.path.join(folder_path, "other.wav")
    output_path = os.path.join(folder_path, "no_vocals.wav")

    if all(os.path.exists(p) for p in [bass_path, drums_path, other_path]):
        bass = AudioSegment.from_wav(bass_path)
        drums = AudioSegment.from_wav(drums_path)
        other = AudioSegment.from_wav(other_path)
        combined = bass.overlay(drums).overlay(other)
        combined.export(output_path, format="wav")
        return True
    return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/remove', methods=['GET', 'POST'])
def remove_vocals():
    if request.method == 'GET':
        return redirect(url_for('index'))  

    file = request.files.get('file')

    if not file:
        flash('No file part in the request.')
        return redirect(url_for('index'))

    if file.filename == '':
        flash('No selected file.')
        return redirect(url_for('index'))

    if allowed_file(file.filename):
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            subprocess.run([
                'demucs',
                '-n', 'htdemucs',
                '-o', OUTPUT_FOLDER,
                filepath
            ], check=True)

            song_name = os.path.splitext(os.path.basename(filename))[0]
            result_path = os.path.join(OUTPUT_FOLDER, 'htdemucs', song_name)

            if not os.path.exists(result_path):
                flash('Proses gagal. Folder hasil tidak ditemukan.')
                return redirect(url_for('index'))

            combine_instrumental(result_path)

            return render_template('index.html',
                song=song_name,
                has_result=True,
                vocals=f'/download/{song_name}/vocals.wav',
                instrumental=f'/download/{song_name}/no_vocals.wav',
                bass=f'/download/{song_name}/bass.wav',
                drums=f'/download/{song_name}/drums.wav',
                other=f'/download/{song_name}/other.wav'
            )

        except subprocess.CalledProcessError as e:
            flash('Gagal menjalankan Demucs.')
            print(e)
            return redirect(url_for('index'))

    else:
        flash('Format file tidak didukung. Hanya MP3 dan WAV yang diperbolehkan.')
        return redirect(url_for('index'))


@app.route('/download/<song>/<stem>')
def download_file(song, stem):
    folder = os.path.join(OUTPUT_FOLDER, 'htdemucs', song)
    return send_from_directory(folder, stem, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
