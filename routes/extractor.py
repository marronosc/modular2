from flask import Blueprint, request, render_template
from services.channel_extractor import obtener_id_canal
import io
import logging
import sys

extractor_bp = Blueprint('extractor', __name__, url_prefix='/extractor')

@extractor_bp.route('/', methods=['GET', 'POST'])
def extractor():
    result = None
    debug_info = None
    
    if request.method == 'POST':
        url = request.form.get('url', '').strip()
        
        if not url:
            return render_template('extractor/index.html', 
                                 result=None, 
                                 debug_info="Error: URL vacía")
        
        # Configurar logging para capturar debug info
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        # Obtener el logger y configurarlo
        logger = logging.getLogger()
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        try:
            # Intentar extraer el ID del canal
            result = obtener_id_canal(url)
            
            # Capturar la información de debug
            debug_info = log_capture.getvalue()
            
            if result:
                debug_info += f"\n✅ ÉXITO: Channel ID extraído: {result}"
            else:
                debug_info += f"\n❌ FALLO: No se pudo extraer el Channel ID de la URL: {url}"
                
        except Exception as e:
            result = None
            debug_info = log_capture.getvalue()
            debug_info += f"\n💥 EXCEPCIÓN: {str(e)}"
            logging.error(f"Error en extractor: {e}")
        finally:
            # Limpiar el handler
            logger.removeHandler(handler)
            handler.close()
    
    return render_template('extractor/index.html', result=result, debug_info=debug_info)