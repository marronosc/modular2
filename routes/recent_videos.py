from flask import Blueprint, request, render_template, redirect, url_for
from services.recent_videos import analyze_recent_videos, format_number, format_date, format_duration
import logging

recent_videos_bp = Blueprint('recent_videos', __name__, url_prefix='/recent-videos')

@recent_videos_bp.route('/', methods=['GET', 'POST'])
def recent_videos():
    if request.method == 'POST':
        channel_url = request.form.get('channel_url', '').strip()
        content_type = request.form.get('content_type', 'all')
        
        if not channel_url:
            return render_template('recent_videos/index.html', 
                                 error="La URL del canal es obligatoria.")
        
        try:
            return redirect(url_for('recent_videos.generate_report', 
                                  channel_url=channel_url, 
                                  content_type=content_type))
        except Exception as e:
            error_msg = f"Error procesando la URL: {str(e)}"
            logging.error(error_msg)
            return render_template('recent_videos/index.html', error=error_msg)
    
    return render_template('recent_videos/index.html')

@recent_videos_bp.route('/report/<path:channel_url>/<content_type>')
def generate_report(channel_url, content_type):
    try:
        result = analyze_recent_videos(channel_url, content_type)
        
        return render_template('recent_videos/report.html',
                             result=result,
                             format_number=format_number,
                             format_date=format_date,
                             format_duration=format_duration)
                             
    except Exception as e:
        error_message = f"Error al generar el análisis: {str(e)}"
        logging.error(error_message)
        return render_template('recent_videos/error.html', 
                             error=error_message, 
                             channel_url=channel_url,
                             content_type=content_type)