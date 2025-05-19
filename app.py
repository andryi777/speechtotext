import os
import whisper
import numpy as np
import torch
from flask import Flask, request, jsonify, render_template, send_file, send_from_directory
from werkzeug.utils import secure_filename
import ffmpeg
import json
from dotenv import load_dotenv
import time
import shutil
from datetime import datetime, timedelta
import tempfile

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Whisper model
model = whisper.load_model("base")

def format_timestamp(seconds):
    """Convierte segundos a formato HH:MM:SS"""
    return str(timedelta(seconds=int(seconds)))

def detect_speaker_changes(audio_path, min_silence_duration=0.5, energy_threshold=0.1):
    """Detecta cambios de hablante basados en silencios y energía del audio"""
    try:
        # Cargar el audio usando ffmpeg
        out, _ = (
            ffmpeg
            .input(audio_path)
            .output('pipe:', format='f32le', acodec='pcm_f32le', ac=1, ar='16k')
            .run(capture_stdout=True, capture_stderr=True)
        )
        
        # Convertir a numpy array
        audio = np.frombuffer(out, np.float32)
        
        # Calcular la energía del audio
        frame_length = int(0.025 * 16000)  # 25ms frames
        hop_length = int(0.010 * 16000)    # 10ms hop
        
        energy = []
        for i in range(0, len(audio) - frame_length, hop_length):
            frame = audio[i:i + frame_length]
            energy.append(np.sum(frame ** 2))
        
        energy = np.array(energy)
        
        # Normalizar la energía
        energy = (energy - np.min(energy)) / (np.max(energy) - np.min(energy))
        
        # Detectar silencios
        is_silence = energy < energy_threshold
        
        # Encontrar segmentos de silencio
        silence_segments = []
        start = None
        
        for i, silent in enumerate(is_silence):
            if silent and start is None:
                start = i
            elif not silent and start is not None:
                duration = (i - start) * hop_length / 16000  # Convertir a segundos
                if duration >= min_silence_duration:
                    silence_segments.append((start * hop_length / 16000, i * hop_length / 16000))
                start = None
        
        # Si terminamos en silencio
        if start is not None:
            duration = (len(is_silence) - start) * hop_length / 16000
            if duration >= min_silence_duration:
                silence_segments.append((start * hop_length / 16000, len(audio) / 16000))
        
        return silence_segments
    
    except Exception as e:
        print(f"Error en detect_speaker_changes: {str(e)}")
        return []

def cleanup_old_files():
    """Remove files older than 24 hours from the uploads directory"""
    current_time = time.time()
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.getmtime(filepath) < current_time - 86400:  # 24 hours
            try:
                os.remove(filepath)
            except Exception as e:
                print(f"Error removing file {filepath}: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'audio' not in request.files:
        return jsonify({'error': 'No se proporcionó ningún archivo'}), 400
    
    file = request.files['audio']
    if file.filename == '':
        return jsonify({'error': 'No se seleccionó ningún archivo'}), 400
    
    if file:
        try:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            transcript_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{os.path.splitext(filename)[0]}_transcription.json")
            # Si ya existe una transcripción guardada, cargarla y devolverla
            if os.path.exists(transcript_path):
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return jsonify({
                    'success': True,
                    'segments': data['segments'],
                    'audio_url': f"/uploads/{filename}"
                })
            # Si no existe, procesar el audio normalmente
            result = model.transcribe(filepath)
            speaker_changes = detect_speaker_changes(filepath)
            segments = []
            current_speaker = 1
            for segment in result['segments']:
                start = segment['start']
                end = segment['end']
                text = segment['text'].strip()
                for silence_start, silence_end in speaker_changes:
                    if silence_start <= start <= silence_end:
                        current_speaker = 2 if current_speaker == 1 else 1
                        break
                segments.append({
                    'speaker': f'Hablante {current_speaker}',
                    'start': format_timestamp(start),
                    'end': format_timestamp(end),
                    'start_seconds': start,
                    'end_seconds': end,
                    'text': text
                })
            # Guardar la transcripción como JSON para futuras ediciones
            with open(transcript_path, 'w', encoding='utf-8') as f:
                json.dump({'segments': segments}, f, ensure_ascii=False, indent=2)
            audio_url = f"/uploads/{filename}"
            return jsonify({
                'success': True,
                'segments': segments,
                'audio_url': audio_url
            })
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': str(e)}), 500

@app.route('/save', methods=['POST'])
def save_transcription():
    data = request.json
    filename = data.get('filename')
    transcription = data.get('transcription')
    if not filename or not transcription:
        return jsonify({'error': 'Missing data'}), 400
    try:
        # Sobrescribir el archivo JSON de la transcripción
        transcript_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{filename}_transcription.json")
        with open(transcript_path, 'w', encoding='utf-8') as f:
            json.dump({'segments': transcription}, f, ensure_ascii=False, indent=2)
        # También guardar el .txt para exportar
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{filename}_transcription.txt")
        with open(output_path, 'w', encoding='utf-8') as f:
            for segment in transcription:
                f.write(f"[{segment['speaker']}] {segment['timestamp']}: {segment['text']}\n")
        return jsonify({'success': True, 'file_path': output_path})
    except Exception as e:
        return jsonify({'error': f'Error saving transcription: {str(e)}'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except Exception as e:
        return jsonify({'error': f'Error downloading file: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True) 