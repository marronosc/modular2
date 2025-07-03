from flask import Blueprint, request, render_template, redirect, url_for, make_response
from services.top_videos import (
    get_top_videos, format_number, format_date, format_duration,
    get_sorted_videos, export_to_csv, generate_chart_data
)
import logging

top_videos_bp = Blueprint('top_videos', __name__, url_prefix='/top-videos')

@top_videos_bp.route('/', methods=['GET', 'POST'])
def top_videos():
    if request.method == 'POST':
        channel_url = request.form.get('channel_url', '').strip()
        duration_filter = request.form.get('duration_filter', '0')
        analysis_depth = request.form.get('analysis_depth', '1000')
        
        if not channel_url:
            return render_template('top_videos/index.html', 
                                 error="La URL del canal es obligatoria.")
        
        try:
            return redirect(url_for('top_videos.generate_report', 
                                  channel_url=channel_url,
                                  duration_filter=duration_filter,
                                  analysis_depth=analysis_depth))
        except Exception as e:
            error_msg = f"Error procesando la URL: {str(e)}"
            logging.error(error_msg)
            return render_template('top_videos/index.html', error=error_msg)
    
    return render_template('top_videos/index.html')

@top_videos_bp.route('/report/<path:channel_url>')
def generate_report(channel_url):
    try:
        # Obtener parámetros de filtro/ordenación de la URL
        sort_by = request.args.get('sort', 'views')
        order = request.args.get('order', 'desc')
        duration_filter = int(request.args.get('duration_filter', '0'))
        analysis_depth = int(request.args.get('analysis_depth', '1000'))
        
        result = get_top_videos(channel_url, duration_filter=duration_filter, analysis_depth=analysis_depth)
        
        # Aplicar ordenación si se especifica
        if sort_by != 'views' or order != 'desc':
            result['videos'] = get_sorted_videos(result['videos'], sort_by, order)
        
        # Generar datos para gráficos
        chart_data = generate_chart_data(result['videos'])
        
        return render_template('top_videos/report.html',
                             result=result,
                             chart_data=chart_data,
                             current_sort=sort_by,
                             current_order=order,
                             channel_url=channel_url,
                             duration_filter=duration_filter,
                             format_number=format_number,
                             format_date=format_date,
                             format_duration=format_duration)
                             
    except Exception as e:
        error_message = f"Error al generar el análisis: {str(e)}"
        logging.error(error_message)
        return render_template('top_videos/error.html', 
                             error=error_message, 
                             channel_url=channel_url)

@top_videos_bp.route('/export/<path:channel_url>')
def export_csv(channel_url):
    try:
        duration_filter = int(request.args.get('duration_filter', '0'))
        result = get_top_videos(channel_url, duration_filter=duration_filter)
        csv_data = export_to_csv(result)
        
        response = make_response(csv_data)
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename="{result["channel_info"]["title"]}_top_videos.csv"'
        
        return response
        
    except Exception as e:
        error_message = f"Error al exportar: {str(e)}"
        logging.error(error_message)
        return redirect(url_for('top_videos.generate_report', channel_url=channel_url))