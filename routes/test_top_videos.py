from flask import Blueprint, request, render_template, jsonify
import logging
from services.top_videos import get_all_channel_videos, get_channel_info
from services.channel_extractor import obtener_id_canal

test_top_videos_bp = Blueprint('test_top_videos', __name__)

@test_top_videos_bp.route('/test-top-videos', methods=['GET', 'POST'])
def test_top_videos():
    """Página de prueba simple para diagnosticar top videos"""
    if request.method == 'POST':
        try:
            channel_url = request.form.get('channel_url')
            
            # Obtener channel ID
            channel_id = obtener_id_canal(channel_url)
            if not channel_id:
                return render_template('test_top_videos/error.html', 
                                     error="No se pudo extraer el ID del canal")
            
            # Obtener info del canal
            channel_info = get_channel_info(channel_id)
            if not channel_info:
                return render_template('test_top_videos/error.html', 
                                     error="El canal no existe o no es público")
            
            # Obtener videos usando el método optimizado con profundidad configurable
            analysis_depth = int(request.form.get('analysis_depth', '1000'))
            videos = get_all_channel_videos(channel_id, 0, 20, analysis_depth)
            
            # Preparar datos para mostrar
            test_data = {
                'channel_info': channel_info,
                'videos': videos,
                'total_videos': len(videos),
                'api_method': 'search().list() con order=viewCount'
            }
            
            return render_template('test_top_videos/results.html', **test_data)
            
        except Exception as e:
            logging.error(f"Error en test top videos: {str(e)}")
            return render_template('test_top_videos/error.html', error=str(e))
    
    return render_template('test_top_videos/index.html')

@test_top_videos_bp.route('/test-top-videos-api/<channel_id>')
def test_top_videos_api(channel_id):
    """API endpoint para obtener solo los datos JSON"""
    try:
        videos = get_all_channel_videos(channel_id, 0, 20)
        
        # Simplificar datos para debug
        simple_videos = []
        for i, video in enumerate(videos, 1):
            simple_videos.append({
                'rank': i,
                'title': video['title'],
                'views': video['views'],
                'likes': video['likes'],
                'published_at': video['published_at'].strftime('%Y-%m-%d'),
                'duration': video['duration_formatted'],
                'url': video['video_url']
            })
        
        return jsonify({
            'success': True,
            'total_videos': len(simple_videos),
            'videos': simple_videos
        })
        
    except Exception as e:
        logging.error(f"Error en API test: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })