from flask import Blueprint, request, render_template, redirect, url_for
from services.video_activity import analyze_video_activity
from services.thumbnail_comparison import extract_video_id

video_activity_bp = Blueprint('video_activity', __name__, url_prefix='/video-activity')

@video_activity_bp.route('/', methods=['GET', 'POST'])
def video_activity():
    if request.method == 'POST':
        video_url = request.form.get('video_url', '').strip()
        
        try:
            video_id = extract_video_id(video_url)
            if not video_id:
                return render_template('video_activity/index.html',
                                     error="URL de video inválida")
            
            return redirect(url_for('video_activity.generate_report',
                                  video_id=video_id))
        except Exception as e:
            return render_template('video_activity/index.html',
                                 error=str(e))
    
    return render_template('video_activity/index.html')

@video_activity_bp.route('/report/<video_id>')
def generate_report(video_id):
    try:
        result = analyze_video_activity(video_id)
        
        # Función helper para formatear números
        def format_number(num):
            if num >= 1000000:
                return f"{num/1000000:.1f}M"
            elif num >= 1000:
                return f"{num/1000:.0f}K"
            else:
                return f"{num:,}"
        
        return render_template('video_activity/report.html',
                             result=result,
                             format_number=format_number)
    except Exception as e:
        return render_template('video_activity/error.html',
                             error=str(e),
                             video_id=video_id)