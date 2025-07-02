from flask import Blueprint, request, render_template, redirect, url_for
from urllib.parse import quote, unquote

thumbnail_comparison_bp = Blueprint('thumbnail_comparison', __name__, url_prefix='/thumbnail-comparison')

@thumbnail_comparison_bp.route('/', methods=['GET', 'POST'])
def thumbnail_comparison():
    if request.method == 'POST':
        keyword = request.form['keyword'].strip()
        video_url = request.form['video_url'].strip()
        show_titles = 'show_titles' in request.form
        
        # Validar URL básica
        if not any(domain in video_url for domain in ['youtube.com', 'youtu.be']):
            return render_template('thumbnail_comparison/index.html', 
                                 error="Por favor, introduce una URL válida de YouTube")
        
        # Codificar la URL para pasarla de forma segura
        encoded_video_url = quote(video_url, safe='')
        
        return redirect(url_for('thumbnail_comparison.generate_comparison', 
                              keyword=keyword, 
                              video_url=encoded_video_url,
                              show_titles=str(show_titles).lower()))
    
    return render_template('thumbnail_comparison/index.html')

@thumbnail_comparison_bp.route('/comparison/<keyword>/<path:video_url>/<show_titles>')
def generate_comparison(keyword, video_url, show_titles):
    try:
        # Importar aquí para evitar importaciones circulares
        from services.thumbnail_comparison import search_videos_and_compare, format_number, format_date
        
        # Decodificar la URL
        decoded_video_url = unquote(video_url)
        show_titles_bool = show_titles.lower() == 'true'
        
        result = search_videos_and_compare(keyword, decoded_video_url, show_titles_bool)
        
        return render_template('thumbnail_comparison/comparison.html',
                             result=result,
                             format_number=format_number,
                             format_date=format_date)
                             
    except Exception as e:
        error_message = f"Error al generar la comparación: {str(e)}"
        return render_template('thumbnail_comparison/error.html', 
                             error=error_message, 
                             keyword=keyword, 
                             video_url=unquote(video_url) if video_url else "URL no válida")