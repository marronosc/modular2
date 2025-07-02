from flask import Blueprint, request, render_template, redirect, url_for, make_response
import logging

# Configurar logging para debug
logging.basicConfig(level=logging.INFO)

keyword_research_bp = Blueprint('keyword_research', __name__, url_prefix='/keyword-research')

@keyword_research_bp.route('/', methods=['GET', 'POST'])
def keyword_research():
    try:
        if request.method == 'POST':
            keyword = request.form.get('keyword', '').strip()
            
            if not keyword:
                return render_template('keyword_research/index.html', 
                                     error="Por favor, introduce una palabra clave para buscar sugerencias.")
            
            # Validación básica de la palabra clave
            if len(keyword) < 2:
                return render_template('keyword_research/index.html', 
                                     error="La palabra clave debe tener al menos 2 caracteres.")
            
            if len(keyword) > 100:
                return render_template('keyword_research/index.html', 
                                     error="La palabra clave no puede exceder los 100 caracteres.")
            
            # Escapar caracteres problemáticos para URL
            safe_keyword = keyword.replace('/', '_').replace('?', '_').replace('#', '_')
            
            return redirect(url_for('keyword_research.generate_results', keyword=safe_keyword))
        
        return render_template('keyword_research/index.html')
        
    except Exception as e:
        logging.error(f"Error en keyword_research index: {str(e)}")
        return render_template('keyword_research/index.html', 
                             error=f"Error interno: {str(e)}")

@keyword_research_bp.route('/results/<keyword>')
def generate_results(keyword):
    try:
        # Importar aquí para evitar importaciones circulares
        from services.keyword_research import search_keyword_suggestions, format_suggestions_for_export
        
        logging.info(f"Generando resultados para keyword: {keyword}")
        
        # Buscar sugerencias con manejo de errores robusto
        result = search_keyword_suggestions(keyword)
        
        # Verificar que tenemos un resultado válido
        if not result or not isinstance(result, dict):
            logging.error("Resultado inválido de search_keyword_suggestions")
            return render_template('keyword_research/error.html', 
                                 error="Error procesando la búsqueda de sugerencias", 
                                 keyword=keyword)
        
        # Preparar datos para exportación solo si hay sugerencias
        export_data = None
        if result.get('has_suggestions', False) and result.get('suggestions'):
            try:
                export_data = format_suggestions_for_export(result['suggestions'], keyword)
            except Exception as export_error:
                logging.warning(f"Error preparando datos de exportación: {str(export_error)}")
                export_data = None
        
        logging.info(f"Renderizando resultados. Sugerencias: {result.get('total_suggestions', 0)}")
        
        return render_template('keyword_research/results.html',
                             result=result,
                             export_data=export_data)
                             
    except ImportError as e:
        logging.error(f"Error de importación: {str(e)}")
        return render_template('keyword_research/error.html', 
                             error=f"Error de configuración del sistema: {str(e)}", 
                             keyword=keyword)
    except Exception as e:
        error_message = f"Error al buscar sugerencias: {str(e)}"
        logging.error(error_message)
        return render_template('keyword_research/error.html', 
                             error=error_message, 
                             keyword=keyword)

@keyword_research_bp.route('/export/<keyword>/<format_type>')
def export_suggestions(keyword, format_type):
    """
    Endpoint para exportar sugerencias en diferentes formatos
    """
    try:
        # Importar aquí para evitar problemas
        from services.keyword_research import search_keyword_suggestions, format_suggestions_for_export
        
        logging.info(f"Exportando sugerencias para '{keyword}' en formato '{format_type}'")
        
        # Validar formato
        if format_type not in ['txt', 'csv', 'json']:
            return render_template('keyword_research/error.html', 
                                 error="Formato de exportación no válido. Use: txt, csv o json", 
                                 keyword=keyword)
        
        # Volver a buscar las sugerencias
        result = search_keyword_suggestions(keyword)
        
        if not result or not result.get('has_suggestions', False):
            return render_template('keyword_research/error.html', 
                                 error="No hay sugerencias para exportar", 
                                 keyword=keyword)
        
        # Formatear datos para exportación
        export_data = format_suggestions_for_export(result['suggestions'], keyword)
        
        # Preparar nombre de archivo seguro
        safe_filename = keyword.replace(' ', '_').replace('/', '_').replace('\\', '_')
        safe_filename = ''.join(c for c in safe_filename if c.isalnum() or c in ('_', '-'))
        
        if format_type == 'txt':
            response = make_response(export_data['text'])
            response.headers['Content-Type'] = 'text/plain; charset=utf-8'
            response.headers['Content-Disposition'] = f'attachment; filename="sugerencias_{safe_filename}.txt"'
            return response
            
        elif format_type == 'csv':
            response = make_response(export_data['csv'])
            response.headers['Content-Type'] = 'text/csv; charset=utf-8'
            response.headers['Content-Disposition'] = f'attachment; filename="sugerencias_{safe_filename}.csv"'
            return response
            
        elif format_type == 'json':
            response = make_response(export_data['json'])
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            response.headers['Content-Disposition'] = f'attachment; filename="sugerencias_{safe_filename}.json"'
            return response
                                 
    except ImportError as e:
        logging.error(f"Error de importación en export: {str(e)}")
        return render_template('keyword_research/error.html', 
                             error=f"Error de configuración: {str(e)}", 
                             keyword=keyword)
    except Exception as e:
        error_message = f"Error al exportar sugerencias: {str(e)}"
        logging.error(error_message)
        return render_template('keyword_research/error.html', 
                             error=error_message, 
                             keyword=keyword)