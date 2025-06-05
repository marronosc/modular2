import os
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import isodate
from collections import defaultdict
import logging

# Configurar la API de YouTube
api_key = os.environ.get('YOUTUBE_API_KEY')
if api_key:
    youtube = build('youtube', 'v3', developerKey=api_key)
else:
    youtube = None

def analyze_recent_videos(channel_url, content_type='all', max_results=20):
    """
    Analiza los últimos videos de un canal
    
    Args:
        channel_url (str): URL del canal o video
        content_type (str): 'all', 'videos', 'shorts', 'lives'
        max_results (int): Número de videos a analizar
    
    Returns:
        dict: Análisis completo de los videos
    """
    if not youtube:
        raise Exception("API de YouTube no configurada. Es necesario configurar la variable de entorno YOUTUBE_API_KEY para usar esta herramienta.")
    
    try:
        # Extraer channel ID usando el servicio existente
        from services.channel_extractor import obtener_id_canal
        
        logging.info(f"Intentando extraer Channel ID de: {channel_url}")
        channel_id = obtener_id_canal(channel_url)
        
        if not channel_id:
            logging.error(f"No se pudo extraer Channel ID de: {channel_url}")
            raise Exception(f"No se pudo extraer el ID del canal desde la URL: {channel_url}. Verifica que sea una URL válida de YouTube.")
        
        logging.info(f"Channel ID extraído exitosamente: {channel_id}")
        
        # Obtener información del canal
        channel_info = get_channel_info(channel_id)
        
        if not channel_info:
            logging.error(f"No se pudo obtener información del canal: {channel_id}")
            raise Exception(f"El canal {channel_id} no existe o no es público")
        
        # Obtener videos del canal
        videos = get_channel_videos(channel_id, content_type, max_results)
        
        if not videos:
            return create_empty_result(channel_info, content_type)
        
        # Calcular estadísticas
        stats = calculate_statistics(videos)
        
        # Análisis de tendencias
        trends = analyze_trends(videos)
        
        # Análisis de frecuencia
        frequency = analyze_frequency(videos)
        
        # Videos destacados
        highlights = identify_highlights(videos)
        
        return {
            'channel_info': channel_info,
            'videos': videos,
            'content_type': content_type,
            'total_videos': len(videos),
            'stats': stats,
            'trends': trends,
            'frequency': frequency,
            'highlights': highlights,
            'analysis_date': datetime.now()
        }
        
    except Exception as e:
        logging.error(f"Error analizando videos recientes: {str(e)}")
        raise Exception(f"Error al analizar videos: {str(e)}")

def get_channel_info(channel_id):
    """Obtiene información básica del canal"""
    try:
        logging.info(f"Obteniendo información del canal: {channel_id}")
        
        request = youtube.channels().list(
            part='snippet,statistics',
            id=channel_id
        )
        response = request.execute()
        
        if 'items' in response and len(response['items']) > 0:
            channel = response['items'][0]
            snippet = channel['snippet']
            statistics = channel.get('statistics', {})
            
            channel_info = {
                'id': channel_id,
                'title': snippet.get('title', 'Canal desconocido'),
                'description': snippet.get('description', '')[:200] + '...' if len(snippet.get('description', '')) > 200 else snippet.get('description', ''),
                'thumbnail': snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
                'subscriber_count': int(statistics.get('subscriberCount', 0)),
                'video_count': int(statistics.get('videoCount', 0)),
                'view_count': int(statistics.get('viewCount', 0)),
                'published_at': datetime.strptime(snippet['publishedAt'], "%Y-%m-%dT%H:%M:%SZ") if 'publishedAt' in snippet else None
            }
            
            logging.info(f"Canal encontrado: {channel_info['title']} ({channel_info['subscriber_count']} suscriptores)")
            return channel_info
        else:
            logging.warning(f"No se encontró información para el canal: {channel_id}")
            return None
            
    except Exception as e:
        logging.error(f"Error obteniendo información del canal {channel_id}: {str(e)}")
        return None

def get_channel_videos(channel_id, content_type, max_results):
    """Obtiene los videos más recientes del canal en orden cronológico"""
    try:
        videos = []
        next_page_token = None
        fetched = 0
        max_fetch = max_results * 3  # Buscar 3x más videos para asegurar suficientes después del filtrado
        
        logging.info(f"Buscando videos para canal: {channel_id}")
        
        while len(videos) < max_results and fetched < max_fetch:
            # Obtener más videos por página para reducir llamadas a la API
            page_size = min(50, max_fetch - fetched)
            
            request = youtube.search().list(
                channelId=channel_id,
                part='id,snippet',
                order='date',  # Orden por fecha (más reciente primero)
                type='video',
                maxResults=page_size,
                pageToken=next_page_token
                # Eliminado filtro de 365 días - buscar en todo el historial
            )
            response = request.execute()
            
            logging.info(f"Obtenidos {len(response.get('items', []))} videos en esta página")
            
            for item in response.get('items', []):
                video_id = item['id']['videoId']
                
                # Obtener detalles del video
                video_details = get_video_details(video_id, item['snippet'])
                
                if video_details and should_include_video(video_details, content_type):
                    videos.append(video_details)
                    logging.info(f"Video incluido: {video_details['title'][:50]}... ({video_details['published_at']})")
                    
                    if len(videos) >= max_results:
                        break
                else:
                    if video_details:
                        logging.info(f"Video excluido ({video_details['content_type']}): {video_details['title'][:50]}...")
                
                fetched += 1
            
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                logging.info("No hay más páginas disponibles")
                break
        
        # Ordenar por fecha de publicación (más reciente primero) para asegurar orden correcto
        videos.sort(key=lambda x: x['published_at'], reverse=True)
        
        result = videos[:max_results]
        logging.info(f"Devolviendo {len(result)} videos finales")
        
        return result
        
    except Exception as e:
        logging.error(f"Error obteniendo videos del canal {channel_id}: {str(e)}")
        raise Exception(f"Error obteniendo videos del canal: {str(e)}")

def get_video_details(video_id, snippet):
    """Obtiene detalles completos de un video"""
    try:
        request = youtube.videos().list(
            part='contentDetails,statistics,liveStreamingDetails',
            id=video_id
        )
        response = request.execute()
        
        if not response.get('items'):
            return None
        
        video = response['items'][0]
        content_details = video['contentDetails']
        statistics = video.get('statistics', {})
        live_details = video.get('liveStreamingDetails', {})
        
        # Parsear duración
        duration_str = content_details['duration']
        duration = isodate.parse_duration(duration_str)
        
        # Determinar tipo de contenido
        is_live = 'actualStartTime' in live_details
        
        # Detectar Shorts de manera más conservadora
        is_short = False
        
        # Solo considerar Short si es realmente muy corto (menos de 60 segundos)
        if duration <= timedelta(seconds=60):
            is_short = True
            logging.info(f"Video marcado como Short por duración: {duration.total_seconds()}s")
            
        # Solo verificar URL si realmente contiene /shorts/ en la ruta
        # (no solo la palabra "short" en el título)
        # Nota: Las URLs de shorts tienen formato youtube.com/shorts/VIDEO_ID
        
        content_type = 'live' if is_live else ('short' if is_short else 'video')
        
        return {
            'video_id': video_id,
            'title': snippet.get('title', 'Sin título'),
            'published_at': datetime.strptime(snippet['publishedAt'], "%Y-%m-%dT%H:%M:%SZ"),
            'thumbnail': snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
            'duration': duration,
            'views': int(statistics.get('viewCount', 0)),
            'likes': int(statistics.get('likeCount', 0)),
            'comments': int(statistics.get('commentCount', 0)),
            'video_url': f"https://www.youtube.com/watch?v={video_id}",
            'content_type': content_type,
            'is_live': is_live,
            'is_short': is_short
        }
        
    except Exception as e:
        logging.error(f"Error obteniendo detalles del video {video_id}: {str(e)}")
        return None

def should_include_video(video, content_type_filter):
    """Determina si un video debe incluirse según el filtro"""
    if content_type_filter == 'all':
        return True
    elif content_type_filter == 'videos':
        include = not video['is_short'] and not video['is_live']
        if not include:
            reason = "Short" if video['is_short'] else "Live"
            logging.info(f"Video excluido por ser {reason}: {video['title'][:30]}... (duración: {video['duration']})")
        return include
    elif content_type_filter == 'shorts':
        return video['is_short']
    elif content_type_filter == 'lives':
        return video['is_live']
    return True

def calculate_statistics(videos):
    """Calcula estadísticas generales"""
    if not videos:
        return {}
    
    total_views = sum(v['views'] for v in videos)
    total_likes = sum(v['likes'] for v in videos)
    total_comments = sum(v['comments'] for v in videos)
    
    avg_duration = sum((v['duration'] for v in videos), timedelta()) / len(videos)
    
    return {
        'total_views': total_views,
        'total_likes': total_likes,
        'total_comments': total_comments,
        'avg_views': total_views / len(videos),
        'avg_likes': total_likes / len(videos),
        'avg_comments': total_comments / len(videos),
        'avg_duration': avg_duration,
        'content_distribution': get_content_distribution(videos)
    }

def get_content_distribution(videos):
    """Calcula distribución de tipos de contenido"""
    distribution = defaultdict(int)
    for video in videos:
        distribution[video['content_type']] += 1
    return dict(distribution)

def analyze_trends(videos):
    """Analiza tendencias de rendimiento"""
    if len(videos) < 2:
        return {}
    
    # Ordenar por fecha
    sorted_videos = sorted(videos, key=lambda x: x['published_at'])
    
    # Calcular tendencias
    recent_half = sorted_videos[len(sorted_videos)//2:]
    older_half = sorted_videos[:len(sorted_videos)//2]
    
    recent_avg_views = sum(v['views'] for v in recent_half) / len(recent_half)
    older_avg_views = sum(v['views'] for v in older_half) / len(older_half)
    
    trend_direction = 'up' if recent_avg_views > older_avg_views else 'down'
    trend_percentage = abs((recent_avg_views - older_avg_views) / older_avg_views * 100) if older_avg_views > 0 else 0
    
    return {
        'trend_direction': trend_direction,
        'trend_percentage': trend_percentage,
        'recent_avg_views': recent_avg_views,
        'older_avg_views': older_avg_views
    }

def analyze_frequency(videos):
    """Analiza frecuencia de publicación"""
    if len(videos) < 2:
        return {}
    
    # Calcular días entre publicaciones
    sorted_videos = sorted(videos, key=lambda x: x['published_at'], reverse=True)
    intervals = []
    
    for i in range(1, len(sorted_videos)):
        diff = sorted_videos[i-1]['published_at'] - sorted_videos[i]['published_at']
        intervals.append(diff.days)
    
    avg_interval = sum(intervals) / len(intervals) if intervals else 0
    
    # Análisis de días de la semana
    weekday_count = defaultdict(int)
    for video in videos:
        weekday = video['published_at'].strftime('%A')
        weekday_count[weekday] += 1
    
    return {
        'avg_days_between_videos': avg_interval,
        'most_active_weekday': max(weekday_count, key=weekday_count.get) if weekday_count else None,
        'weekday_distribution': dict(weekday_count)
    }

def identify_highlights(videos):
    """Identifica videos destacados"""
    if not videos:
        return {}
    
    # Video más exitoso
    best_video = max(videos, key=lambda x: x['views'])
    
    # Video menos exitoso
    worst_video = min(videos, key=lambda x: x['views'])
    
    # Video más reciente
    most_recent = max(videos, key=lambda x: x['published_at'])
    
    return {
        'best_performing': best_video,
        'worst_performing': worst_video,
        'most_recent': most_recent
    }

def create_empty_result(channel_info, content_type):
    """Crea resultado vacío"""
    return {
        'channel_info': channel_info,
        'videos': [],
        'content_type': content_type,
        'total_videos': 0,
        'stats': {},
        'trends': {},
        'frequency': {},
        'highlights': {},
        'analysis_date': datetime.now(),
        'error_message': f"No se encontraron videos del tipo '{content_type}' en este canal."
    }

# Funciones de formato (reutilizar las existentes)
def format_number(value):
    """Formatea números para mostrar"""
    if isinstance(value, (int, float)):
        if value >= 1000000:
            return f"{value/1000000:.1f}M"
        elif value >= 1000:
            return f"{value/1000:.1f}K"
        else:
            return f"{value:,.0f}"
    return str(value)

def format_date(value):
    """Formatea fechas para mostrar"""
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    return str(value)

def format_duration(duration):
    """Formatea duración para mostrar"""
    if isinstance(duration, timedelta):
        hours, remainder = divmod(duration.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{int(hours)}:{int(minutes):02d}:{int(seconds):02d}"
        else:
            return f"{int(minutes):02d}:{int(seconds):02d}"
    return str(duration) if duration else "00:00"