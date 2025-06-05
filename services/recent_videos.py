import os
import logging
from datetime import datetime, timedelta
import isodate
from googleapiclient.discovery import build

# Configurar la API de YouTube
api_key = os.environ.get('YOUTUBE_API_KEY')
if api_key:
    youtube = build('youtube', 'v3', developerKey=api_key)
else:
    youtube = None

def get_recent_videos(channel_url, max_results=20):
    """
    Obtiene los últimos videos regulares de un canal de YouTube
    
    Args:
        channel_url (str): URL del canal o video
        max_results (int): Número de videos a obtener (default: 20)
    
    Returns:
        dict: Información del canal y lista de videos
    """
    if not youtube:
        raise Exception("API de YouTube no configurada. Es necesario configurar la variable de entorno YOUTUBE_API_KEY.")
    
    try:
        # Obtener channel ID usando el servicio existente
        from services.channel_extractor import obtener_id_canal
        
        logging.info(f"Extrayendo Channel ID de: {channel_url}")
        channel_id = obtener_id_canal(channel_url)
        
        if not channel_id:
            raise Exception(f"No se pudo extraer el ID del canal desde: {channel_url}")
        
        logging.info(f"Channel ID obtenido: {channel_id}")
        
        # Obtener información básica del canal
        channel_info = get_channel_info(channel_id)
        if not channel_info:
            raise Exception(f"El canal {channel_id} no existe o no es público")
        
        # Obtener videos del canal
        videos = get_channel_videos(channel_id, max_results)
        
        return {
            'channel_info': channel_info,
            'videos': videos,
            'total_videos': len(videos),
            'analysis_date': datetime.now()
        }
        
    except Exception as e:
        logging.error(f"Error obteniendo videos recientes: {str(e)}")
        raise Exception(f"Error al obtener videos: {str(e)}")

def get_channel_info(channel_id):
    """Obtiene información básica del canal"""
    try:
        request = youtube.channels().list(
            part='snippet,statistics',
            id=channel_id
        )
        response = request.execute()
        
        if 'items' in response and len(response['items']) > 0:
            channel = response['items'][0]
            snippet = channel['snippet']
            statistics = channel.get('statistics', {})
            
            return {
                'id': channel_id,
                'title': snippet.get('title', 'Canal desconocido'),
                'description': snippet.get('description', '')[:200] + '...' if len(snippet.get('description', '')) > 200 else snippet.get('description', ''),
                'thumbnail': snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
                'subscriber_count': int(statistics.get('subscriberCount', 0)),
                'video_count': int(statistics.get('videoCount', 0)),
                'view_count': int(statistics.get('viewCount', 0))
            }
        else:
            return None
            
    except Exception as e:
        logging.error(f"Error obteniendo información del canal {channel_id}: {str(e)}")
        return None

def get_channel_videos(channel_id, max_results):
    """Obtiene los videos más recientes del canal"""
    try:
        videos = []
        next_page_token = None
        fetched = 0
        max_fetch = max_results * 2  # Buscar el doble para filtrar Shorts
        
        logging.info(f"Buscando videos para canal: {channel_id}")
        
        while len(videos) < max_results and fetched < max_fetch:
            page_size = min(50, max_fetch - fetched)
            
            request = youtube.search().list(
                channelId=channel_id,
                part='id,snippet',
                order='date',
                type='video',
                maxResults=page_size,
                pageToken=next_page_token
            )
            response = request.execute()
            
            for item in response.get('items', []):
                video_id = item['id']['videoId']
                video_details = get_video_details(video_id, item['snippet'])
                
                if video_details and is_regular_video(video_details):
                    videos.append(video_details)
                    logging.info(f"Video incluido: {video_details['title'][:50]}...")
                    
                    if len(videos) >= max_results:
                        break
                
                fetched += 1
            
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
        
        # Ordenar por fecha (más reciente primero)
        videos.sort(key=lambda x: x['published_at'], reverse=True)
        
        return videos[:max_results]
        
    except Exception as e:
        logging.error(f"Error obteniendo videos del canal {channel_id}: {str(e)}")
        raise Exception(f"Error obteniendo videos del canal: {str(e)}")

def get_video_details(video_id, snippet):
    """Obtiene detalles de un video específico"""
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
        
        # Verificar si es live
        is_live = 'actualStartTime' in live_details
        
        return {
            'video_id': video_id,
            'title': snippet.get('title', 'Sin título'),
            'published_at': datetime.strptime(snippet['publishedAt'], "%Y-%m-%dT%H:%M:%SZ"),
            'thumbnail': snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
            'duration': duration,
            'duration_formatted': format_duration(duration),
            'views': int(statistics.get('viewCount', 0)),
            'likes': int(statistics.get('likeCount', 0)),
            'video_url': f"https://www.youtube.com/watch?v={video_id}",
            'is_live': is_live,
            'is_short': duration <= timedelta(seconds=60)
        }
        
    except Exception as e:
        logging.error(f"Error obteniendo detalles del video {video_id}: {str(e)}")
        return None

def is_regular_video(video):
    """Verifica si es un video regular (no Short ni live)"""
    return not video['is_short'] and not video['is_live']

def format_duration(duration):
    """Formatea duración para mostrar en formato MM:SS o HH:MM:SS"""
    if isinstance(duration, timedelta):
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    return "00:00"

def format_number(value):
    """Formatea números para mostrar (1.2M, 450K, etc.)"""
    if isinstance(value, (int, float)):
        if value >= 1000000:
            return f"{value/1000000:.1f}M"
        elif value >= 1000:
            return f"{value/1000:.1f}K"
        else:
            return f"{value:,.0f}"
    return str(value)

def format_date(value):
    """Formatea fechas para mostrar en formato DD/MM/YYYY"""
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    return str(value)