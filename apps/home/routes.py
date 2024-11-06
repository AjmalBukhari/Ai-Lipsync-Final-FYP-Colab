from apps.home import blueprint
from flask import render_template, request, current_app, send_from_directory, flash, redirect, url_for
from flask_login import login_required
from apps.authentication.routes import current_user, log_user_action
from apps.authentication.models import Feedback
from apps import db
from jinja2 import TemplateNotFound
import os
import subprocess
import shutil
from moviepy.editor import VideoFileClip
from pydub import AudioSegment
from werkzeug.utils import secure_filename
import threading


# Route to render templates dynamically
@blueprint.route('/<template>', methods=['GET', 'POST'])
@login_required
def route_template(template):
    try:
        template = template if template.endswith('.html') else f"{template}.html"

        if current_user.is_authenticated:
            log_user_action(current_user.username, f"in {template}")

        return render_template(f"home/{template}", segment=get_segment(request))

    except TemplateNotFound:
        return render_template('home/page-404.html'), 404
    except Exception as e:
        print(f"An error occurred: {e}")
        return render_template('home/page-500.html'), 500


# Helper functions
def get_segment(request):
    return request.path.split('/')[-1] or 'index'

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def get_user_directory(username, filetype):
    return os.path.join(current_app.config['USER_FOLDER'], username, filetype)

def ensure_directory_exists(directory):
    os.makedirs(directory, exist_ok=True)

def convert_video(input_path, output_path):
    try:
        clip = VideoFileClip(input_path)
        clip.write_videofile(output_path, codec='libx264')
        clip.close()
    except Exception as e:
        flash(f"Error converting video: {e}")

def convert_audio(input_path, output_path):
    try:
        audio = AudioSegment.from_file(input_path)
        audio.export(output_path, format='mp3')
    except Exception as e:
        flash(f"Error converting audio: {e}")

# Home Page
@blueprint.route('/index', methods=['GET'])
@login_required
def home():
    videos_dir = os.path.join(current_app.static_folder, 'videos')
    videos = [f for f in os.listdir(videos_dir) if f.endswith('.mp4')]
    return render_template("home/index.html", videos=videos)

# User Dashboard
@blueprint.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    username = current_user.username
    base_path = os.path.join(current_app.config['USER_FOLDER'], username)
    video_dir, audio_dir, output_dir = [os.path.join(base_path, ftype) for ftype in ['video', 'audio', 'output']]
    
    video_files = [f for f in os.listdir(video_dir) if f.endswith(('.mp4', '.webm', '.ogg'))]
    audio_files = [f for f in os.listdir(audio_dir) if f.endswith(('.mp3', '.wav', '.ogg'))]
    output_files = [f for f in os.listdir(output_dir) if f.endswith(('.mp4', '.webm', '.ogg', '.mkv'))]
    
    return render_template("home/dashboard.html", videos=video_files, audios=audio_files, outputs=output_files, base_path=base_path)

# User Profile Picture upload
@blueprint.route('/upload-profile-image', methods=['POST'])
@login_required
def upload_profile_image():
    file = request.files.get('profile_image')

    if not file or not file.filename:
        flash("No file selected", "danger")
        return redirect(url_for('home_blueprint.route_template', template='user'))

    if allowed_file(file.filename, current_app.config['ALLOWED_IMAGE_EXTENSIONS']):
        username = current_user.username
        profile_dir = get_user_directory(username, 'profile/dp')
        file_path = os.path.join(profile_dir, current_app.config['PROFILE_IMAGE_NAME'])

        ensure_directory_exists(profile_dir)
        try:
            file.save(file_path)
            log_user_action(username, "profile picture is updated.")
            flash("Profile image uploaded successfully", "success")
        except Exception as e:
            flash(f"Error saving file: {e}", "danger")
    else:
        flash("Invalid file type", "danger")

    return redirect(url_for('home_blueprint.route_template', template='user'))


@blueprint.route('/user_data/<username>/profile/dp/<filename>')
@login_required
def profile_image(username, filename):
    profile_dir = get_user_directory(username, 'profile/dp')
    file_path = os.path.join(profile_dir, filename)
    return send_from_directory(profile_dir, filename) if os.path.exists(file_path) else ("File not found", 404)

# Upload video
@blueprint.route('/upload-video', methods=['POST'])
@login_required
def upload_video():
    username = current_user.username
    file = request.files.get('video')

    if not file or not file.filename:
        flash('No video file selected', 'danger')
        return redirect(url_for('home_blueprint.route_template', template='lipsync'))

    if allowed_file(file.filename, current_app.config['ALLOWED_VIDEO_EXTENSIONS']):
        filename = secure_filename(file.filename)
        user_dir, temp_dir = get_user_directory(username, 'video'), get_user_directory(username, 'temp')
        original_path, temp_video_path = os.path.join(user_dir, filename), os.path.join(temp_dir, 'temp_uploaded_video.mp4')

        ensure_directory_exists(user_dir)
        ensure_directory_exists(temp_dir)

        try:
            file.save(original_path)
            if not filename.lower().endswith('.mp4'):
                convert_video(original_path, temp_video_path)
            else:
                shutil.copy(original_path, temp_video_path)

            log_user_action(username, "uploaded and converted video file.")
            flash('Video uploaded and converted successfully', 'success')
        except Exception as e:
            flash(f"Error processing video file: {e}", "danger")
    else:
        flash('Invalid video file type', 'danger')

    return redirect(url_for('home_blueprint.route_template', template='lipsync'))

# Upload Auido
@blueprint.route('/upload-audio', methods=['POST'])
@login_required
def upload_audio():
    username = current_user.username
    file = request.files.get('audio')

    if not file or not file.filename:
        flash('No audio file selected', 'danger')
        return redirect(url_for('home_blueprint.route_template', template='lipsync'))

    if allowed_file(file.filename, current_app.config['ALLOWED_AUDIO_EXTENSIONS']):
        filename = secure_filename(file.filename)
        user_dir, temp_dir = get_user_directory(username, 'audio'), get_user_directory(username, 'temp')
        original_path, temp_audio_path = os.path.join(user_dir, filename), os.path.join(temp_dir, 'temp_uploaded_audio.mp3')

        ensure_directory_exists(user_dir)
        ensure_directory_exists(temp_dir)

        try:
            file.save(original_path)
            if not filename.lower().endswith('.mp3'):
                convert_audio(original_path, temp_audio_path)
            else:
                shutil.copy(original_path, temp_audio_path)

            log_user_action(username, "uploaded and converted audio file.")
            flash('Audio uploaded and converted successfully', 'success')
        except Exception as e:
            flash(f"Error processing audio file: {e}", "danger")
    else:
        flash('Invalid audio file type', 'danger')

    return redirect(url_for('home_blueprint.route_template', template='lipsync'))

# Process Trimming
processing_status = {}

@blueprint.route('/lipsync', methods=['POST'])
@login_required
def trim_media():
    username = current_user.username
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    padding_top = request.form.get('padding_top')
    padding_left = request.form.get('padding_left')
    padding_bottom = request.form.get('padding_bottom')
    padding_right = request.form.get('padding_right')
    output_filename = request.form.get('output_filename')
    model_type = request.form.get('model_type')

    trim_dir, temp_dir, output_dir = (
        get_user_directory(username, 'trim'),
        get_user_directory(username, 'temp'),
        get_user_directory(username, 'output')
    )
    temp_video_path = os.path.join(temp_dir, 'temp_uploaded_video.mp4')
    temp_audio_path = os.path.join(temp_dir, 'temp_uploaded_audio.mp3')
    output_path = os.path.join(output_dir, f"{output_filename}.mp4")

    ensure_directory_exists(trim_dir)

    trimmed_video_path = os.path.join(trim_dir, 'trimmed_video.mp4')
    trimmed_audio_path = os.path.join(trim_dir, 'trimmed_audio.mp3')

    subprocess.run(['ffmpeg', '-i', temp_video_path, '-ss', start_time, '-to', end_time, '-c', 'copy', trimmed_video_path, '-y'], check=True)
    subprocess.run(['ffmpeg', '-i', temp_audio_path, '-ss', start_time, '-to', end_time, '-c', 'copy', trimmed_audio_path, '-y'], check=True)

    flash("Video and audio trimmed successfully.", "success")
    log_user_action(username, "trimmed video and audio successfully.")

    processing_status[username] = 'processing'
    thread = threading.Thread(target=start_lipsync, args=(trimmed_video_path, trimmed_audio_path, output_path, model_type, padding_top, padding_left, padding_bottom, padding_right, username))
    thread.start()

    return redirect(url_for('home_blueprint.process'))

@blueprint.route('/process')
@login_required
def process():
    username = current_user.username
    status = processing_status.get(username, 'not started')

    if status == 'completed':
        del processing_status[username]
        return redirect(url_for('home_blueprint.preview'))
    elif status == 'error':
        flash("An error occurred during processing. Please try again.", "danger")
        del processing_status[username]
        return redirect(url_for('home_blueprint.route_template', template='lipsync'))

    return render_template('home/process.html', status=status)

def start_lipsync(trimmed_video_path, trimmed_audio_path, output_path, model_type, padding_top, padding_left, padding_bottom, padding_right, username):
    try:
        model_path = 'models/wav2lip.pth' if model_type == 'wav2lip' else 'models/wav2lip_gan.pth'
        
        subprocess.run(
            ["python", "apps/wav2lip/inference.py", 
             "--checkpoint_path", model_path, 
             "--face", trimmed_video_path,
             "--audio", trimmed_audio_path, 
             "--outfile", output_path, 
             "--pads", padding_top, padding_left, padding_bottom, padding_right],
            check=True
        )
        print("Lipsync process completed successfully.")
        processing_status[username] = 'completed'
    except subprocess.CalledProcessError as e:
        print(f"Error during lipsync processing: {e}")
        processing_status[username] = 'error'

@blueprint.route('/preview')
@login_required
def preview():
    username = current_user.username
    output_dir = get_user_directory(username, 'output')

    video_file = next((file for file in os.listdir(output_dir) if file.endswith(('.mp4', '.avi', '.mov', '.mkv'))), None)
    video_url = f"/video/{username}/{video_file}" if video_file else None

    return render_template("home/preview.html", video_url=video_url)


@blueprint.route('/video/<username>/<filename>')
@login_required
def serve_video(username, filename):
    output_dir = get_user_directory(username, 'output')
    return send_from_directory(output_dir, filename)


@blueprint.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    if request.method == 'POST':
        feedback_text, rating = request.form.get('feedback_text'), request.form.get('rating')

        new_feedback = Feedback(
            user_id=current_user.id,
            feedback_text=feedback_text,
            rating=rating
        )

        db.session.add(new_feedback)
        db.session.commit()

        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('home_blueprint.feedback'))

    return render_template("home/feedback.html")
