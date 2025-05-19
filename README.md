# Transcriptor de Audio Web

Transcriptor de Audio Web es una aplicación web desarrollada con Flask que permite subir archivos de audio, transcribirlos automáticamente usando Whisper, distinguir hablantes de manera básica, editar la transcripción y exportarla o guardarla en el servidor.

## Características
- Subida de archivos de audio (mp3, wav, etc.)
- Transcripción automática con Whisper
- Detección básica de cambios de hablante
- Edición en línea de la transcripción
- Guardado y exportación de la transcripción editada
- Reproductor de audio sincronizado con el texto
- Persistencia de transcripción editada (no reprocesa si ya existe)
- Notificación visual al guardar cambios

## Requisitos
- Python 3.10+ (recomendado)
- FFmpeg instalado y en el PATH

## Instalación
1. Clona el repositorio:
   ```bash
   git clone https://github.com/andryi777/speechtotext.git
   cd speechtotext
   ```
2. Crea y activa un entorno virtual:
   ```bash
   python -m venv venv
   # En Windows:
   venv\Scripts\activate
   # En Linux/Mac:
   source venv/bin/activate
   ```
3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
4. Asegúrate de tener FFmpeg instalado. En Windows puedes usar Chocolatey:
   ```bash
   choco install ffmpeg
   ```

## Uso
1. Ejecuta la aplicación:
   ```bash
   python app.py
   ```
2. Abre tu navegador en [http://127.0.0.1:5000](http://127.0.0.1:5000)
3. Sube un archivo de audio, edita la transcripción y guárdala o expórtala.

## Estructura del proyecto
```
speechtotext/
├── app.py                # Backend Flask principal
├── requirements.txt      # Dependencias del proyecto
├── templates/
│   └── index.html        # Interfaz web principal
├── uploads/              # Archivos de audio y transcripciones guardadas
├── .gitignore            # Ignora archivos innecesarios para git
└── README.md             # Este archivo
```

## Contribución
- Haz un fork del repositorio y crea una rama para tu feature o fix.
- Haz tus cambios y envía un Pull Request.
- Por favor, mantén el código limpio y documentado.

## Licencia
MIT
