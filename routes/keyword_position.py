from flask import Blueprint, request, render_template, redirect, url_for
from services.keyword_position import search_channel_position, format_number, format_date
from services.channel_extractor import obtener_id_canal
import logging

keyword_position_bp = Blueprint('keyword_position', __name__, url_prefix='/keyword-position')

@keyword_position_bp.route('/', methods=['GET', 'POST'])
def keyword_position():
    if request.method == 'POST':
        keyword = request.form.get('keyword', '').strip()
        channel_url = request.form.get('channel_url', '').strip()
        max_results = int(request.form.get('max_results', 100))
        
        # Validaciones básicas
        if not keyword:
            return render_template('keyword_position/index.html', 
                                 error="La palabra clave es obligatoria.")
        
        if not channel_url:
            return render_template('keyword_position/index.html', 
                                 error="La URL del canal es obligatoria.")
        
        try:
            # Extraer el ID del canal usando el extractor existente
            logging.info(f"Extrayendo channel ID de URL: {channel_url}")
            channel_id = obtener_id_canal(channel_url)
            
            if not channel_id:
                error_msg = f"No se pudo extraer el ID del canal de la URL proporcionada: {channel_url}. "
                error_msg += "Verifica que sea una URL válida de YouTube (canal, video, etc.)"
                return render_template('keyword_position/index.html', error=error_msg)
            
            logging.info(f"Channel ID extraído exitosamente: {channel_id}")
            
            return redirect(url_for('keyword_position.generate_report', 
                                  keyword=keyword, 
                                  channel_id=channel_id, 
                                  max_results=max_results))
                                  
        except Exception as e:
            error_msg = f"Error al procesar la URL del canal: {str(e)}"
            logging.error(error_msg)
            return render_template('keyword_position/index.html', error=error_msg)
    
    return render_template('keyword_position/index.html')

@keyword_position_bp.route('/report/<keyword>/<channel_id>')
@keyword_position_bp.route('/report/<keyword>/<channel_id>/<int:max_results>')
def generate_report(keyword, channel_id, max_results=100):
    try:
        result = search_channel_position(keyword, channel_id, max_results)
        
        return render_template('keyword_position/report.html',
                             result=result,
                             format_number=format_number,
                             format_date=format_date)
                             
    except Exception as e:
        error_message = f"Error al generar el informe: {str(e)}"
        logging.error(error_message)
        return render_template('keyword_position/error.html', 
                             error=error_message, 
                             keyword=keyword, 
                             channel_id=channel_id)