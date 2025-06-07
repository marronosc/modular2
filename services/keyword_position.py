import os
from googleapiclient.discovery import build
from datetime import datetime
import logging

# Configurar la API de YouTube
api_key = os.environ.get('YOUTUBE_API_KEY')
if api_key:
    youtube = build('youtube', 'v3', developerKey=api_key)
else:
    youtube = None

def search_channel_position(keyword, channel_id, max_results=100):
    """
    Busca la posición de un canal específico en los resultados de búsqueda de YouTube
    
    Args:
        keyword (str): Palabra clave para buscar
        channel_id (str): ID del canal a buscar
        max_results (int): Número máximo de resultados a analizar (por defecto 100)
    
    Returns:
        dict: Información sobre las posiciones encontradas y videos del canal
    """
    if not youtube:
        raise Exception("API de YouTube no configurada. Verifica la variable YOUTUBE_API_KEY")
    
    try:
        found_videos = []
        position = 1
        next_page_token = None
        total_searched = 0
        
        logging.info(f"Buscando canal {channel_id} para la palabra clave: {keyword}")
        
        while total_searched < max_results:
            # Determinar cuántos resultados obtener en esta página
            results_to_get = min(50, max_results - total_searched)
            
            request = youtube.search().list(
                q=keyword,
                type='video',
                part='id,snippet',
                maxResults=results_to_get,
                pageToken=next_page_token
            )
            response = request.execute()
            
            for item in response['items']:
                video_channel_id = item['snippet']['channelId']
                
                if video_channel_id == channel_id:
                    # Obtener estadísticas del video
                    video_id = item['id']['videoId']
                    video_stats = get_video_statistics(video_id)
                    
                    video_info = {
                        'position': position,
                        'title': item['snippet']['title'],
                        'video_id': video_id,
                        'video_url': f"https://www.youtube.com/watch?v={video_id}",
                        'thumbnail': item['snippet']['thumbnails'].get('medium', {}).get('url', ''),
                        'published_at': datetime.strptime(item['snippet']['publishedAt'], "%Y-%m-%dT%H:%M:%SZ"),
                        'description': item['snippet'].get('description', '')[:200] + '...' if len(item['snippet'].get('description', '')) > 200 else item['snippet'].get('description', ''),
                        'views': video_stats.get('views', 0),
                        'likes': video_stats.get('likes', 0),
                        'comments': video_stats.get('comments', 0)
                    }
                    found_videos.append(video_info)
                    logging.info(f"Video encontrado en posición {position}: {item['snippet']['title']}")
                
                position += 1
                total_searched += 1
                
                if total_searched >= max_results:
                    break
            
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
        
        # Obtener información del canal
        channel_info = get_channel_info(channel_id)
        
        result = {
            'keyword': keyword,
            'channel_id': channel_id,
            'channel_info': channel_info,
            'total_searched': total_searched,
            'found_videos': found_videos,
            'total_found': len(found_videos),
            'best_position': found_videos[0]['position'] if found_videos else None,
            'search_date': datetime.now()
        }
        
        logging.info(f"Búsqueda completada. Encontrados {len(found_videos)} videos del canal en {total_searched} resultados")
        return result
        
    except Exception as e:
        logging.error(f"Error en la búsqueda: {str(e)}")
        raise Exception(f"Error al buscar posiciones del canal: {str(e)}")

def get_video_statistics(video_id):
    """Obtiene las estadísticas de un video específico"""
    try:
        request = youtube.videos().list(
            part='statistics',
            id=video_id
        )
        response = request.execute()
        
        if 'items' in response and len(response['items']) > 0:
            stats = response['items'][0]['statistics']
            return {
                'views': int(stats.get('viewCount', 0)),
                'likes': int(stats.get('likeCount', 0)),
                'comments': int(stats.get('commentCount', 0))
            }
    except Exception as e:
        logging.error(f"Error obteniendo estadísticas del video {video_id}: {str(e)}")
    
    return {'views': 0, 'likes': 0, 'comments': 0}

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
                'title': snippet.get('title', 'Canal desconocido'),
                'description': snippet.get('description', '')[:200] + '...' if len(snippet.get('description', '')) > 200 else snippet.get('description', ''),
                'thumbnail': snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
                'subscriber_count': int(statistics.get('subscriberCount', 0)),
                'video_count': int(statistics.get('videoCount', 0)),
                'view_count': int(statistics.get('viewCount', 0)),
                'published_at': datetime.strptime(snippet['publishedAt'], "%Y-%m-%dT%H:%M:%SZ") if 'publishedAt' in snippet else None
            }
    except Exception as e:
        logging.error(f"Error obteniendo información del canal {channel_id}: {str(e)}")
    
    return {
        'title': 'Canal desconocido',
        'description': '',
        'thumbnail': '',
        'subscriber_count': 0,
        'video_count': 0,
        'view_count': 0,
        'published_at': None
    }

def format_number(value):
    """Formatea números para mostrar de manera legible"""
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