import os
import re
from googleapiclient.discovery import build
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import logging

# Configurar la API de YouTube
api_key = os.environ.get('YOUTUBE_API_KEY')
if api_key:
    youtube = build('youtube', 'v3', developerKey=api_key)
else:
    youtube = None

def extract_video_id(url):
    """Extrae el ID del video de una URL de YouTube"""
    try:
        parsed_url = urlparse(url)
        
        if 'youtube.com' in parsed_url.netloc:
            if 'watch' in parsed_url.path:
                return parse_qs(parsed_url.query).get('v', [None])[0]
            elif '/embed/' in parsed_url.path:
                return parsed_url.path.split('/embed/')[1].split('?')[0]
        elif 'youtu.be' in parsed_url.netloc:
            return parsed_url.path.strip('/')
            
        return None
    except Exception:
        return None

def get_video_info(video_url):
    """Obtiene información de un video específico"""
    if not youtube:
        raise Exception("API de YouTube no configurada")
    
    video_id = extract_video_id(video_url)
    if not video_id:
        raise Exception("URL de video inválida")
    
    try:
        request = youtube.videos().list(
            part='snippet,statistics,status',
            id=video_id
        )
        response = request.execute()
        
        if not response.get('items'):
            raise Exception("Video no encontrado o no es público")
        
        video = response['items'][0]
        
        # Verificar que el video sea público o no listado
        privacy_status = video.get('status', {}).get('privacyStatus', '')
        if privacy_status == 'private':
            raise Exception("El video debe ser público o no listado (no privado)")
        
        snippet = video['snippet']
        statistics = video.get('statistics', {})
        
        return {
            'video_id': video_id,
            'title': snippet.get('title', 'Sin título'),
            'thumbnail': snippet.get('thumbnails', {}).get('high', {}).get('url', ''),
            'channel_title': snippet.get('channelTitle', 'Canal desconocido'),
            'published_at': datetime.strptime(snippet['publishedAt'], "%Y-%m-%dT%H:%M:%SZ"),
            'views': int(statistics.get('viewCount', 0)),
            'likes': int(statistics.get('likeCount', 0)),
            'comments': int(statistics.get('commentCount', 0)),
            'video_url': f"https://www.youtube.com/watch?v={video_id}"
        }
        
    except Exception as e:
        if "debe ser público" in str(e):
            raise e
        raise Exception(f"Error al obtener información del video: {str(e)}")

def search_top_videos(keyword, max_results=12):
    """Busca los videos mejor posicionados para una palabra clave"""
    if not youtube:
        raise Exception("API de YouTube no configurada")
    
    try:
        videos = []
        
        request = youtube.search().list(
            q=keyword,
            type='video',
            part='id,snippet',
            maxResults=max_results,
            order='relevance'
        )
        response = request.execute()
        
        for item in response['items']:
            video_id = item['id']['videoId']
            
            # Obtener estadísticas del video
            video_stats = youtube.videos().list(
                part='statistics',
                id=video_id
            ).execute()
            
            stats = {}
            if video_stats.get('items'):
                stats = video_stats['items'][0].get('statistics', {})
            
            video_info = {
                'video_id': video_id,
                'title': item['snippet'].get('title', 'Sin título'),
                'thumbnail': item['snippet'].get('thumbnails', {}).get('high', {}).get('url', ''),
                'channel_title': item['snippet'].get('channelTitle', 'Canal desconocido'),
                'published_at': datetime.strptime(item['snippet']['publishedAt'], "%Y-%m-%dT%H:%M:%SZ"),
                'views': int(stats.get('viewCount', 0)),
                'likes': int(stats.get('likeCount', 0)),
                'comments': int(stats.get('commentCount', 0)),
                'video_url': f"https://www.youtube.com/watch?v={video_id}",
                'position': len(videos) + 1
            }
            videos.append(video_info)
        
        return videos
        
    except Exception as e:
        raise Exception(f"Error al buscar videos: {str(e)}")

def find_user_video_position(videos, user_video_id):
    """Encuentra la posición del video del usuario en los resultados"""
    for i, video in enumerate(videos):
        if video['video_id'] == user_video_id:
            return i + 1
    return None

def search_extended_results(keyword, user_video_id, max_results=50):
    """Busca más resultados para encontrar la posición real del video del usuario"""
    if not youtube:
        raise Exception("API de YouTube no configurada")
    
    try:
        position = 1
        next_page_token = None
        searched_count = 0
        
        while searched_count < max_results:
            results_to_get = min(50, max_results - searched_count)
            
            request = youtube.search().list(
                q=keyword,
                type='video',
                part='id,snippet',
                maxResults=results_to_get,
                pageToken=next_page_token,
                order='relevance'
            )
            response = request.execute()
            
            for item in response['items']:
                if item['id']['videoId'] == user_video_id:
                    return position
                position += 1
                searched_count += 1
                
                if searched_count >= max_results:
                    break
            
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
        
        return None  # No encontrado en los primeros max_results
        
    except Exception as e:
        logging.error(f"Error buscando posición extendida: {str(e)}")
        return None

def prepare_desktop_view(top_videos, user_video):
    """Prepara la vista desktop con 3 columnas, insertando el video del usuario en la posición 7"""
    # Crear lista combinada con el video del usuario en la posición 7
    combined_videos = []
    
    # Agregar los primeros 6 videos
    combined_videos.extend(top_videos[:6])
    
    # Insertar el video del usuario en la posición 7
    user_video_copy = user_video.copy()
    user_video_copy['position'] = 7  # Forzar posición 7 para mostrar
    combined_videos.append(user_video_copy)
    
    # Agregar el resto de videos (del 7 al 11 de top_videos)
    combined_videos.extend(top_videos[6:11])
    
    # Crear 3 columnas y distribuir los 12 videos
    columns = [[], [], []]
    for i, video in enumerate(combined_videos):
        column = i % 3
        columns[column].append(video)
    
    return {
        'columns': columns
    }

def prepare_mobile_view(top_videos, user_video):
    """Prepara la vista móvil estilo YouTube - máximo 5 videos con scroll"""
    mobile_videos = []
    
    # Tomar los primeros 2 videos
    mobile_videos.extend(top_videos[:2])
    
    # Video del usuario en posición 3
    user_video_copy = user_video.copy()
    mobile_videos.append(user_video_copy)
    
    # Agregar 2 videos más para completar 5 (requiere scroll)
    mobile_videos.extend(top_videos[2:4])
    
    # Títulos completos para móvil
    for video in mobile_videos:
        video['mobile_title'] = video['title']
    
    return mobile_videos

def search_videos_and_compare(keyword, video_url, show_titles=True):
    """Busca videos top y compara con el video del usuario"""
    try:
        # Obtener información del video del usuario
        user_video = get_video_info(video_url)
        
        # Buscar videos top (buscamos 12 para tener suficientes)
        top_videos = search_top_videos(keyword, 12)
        
        # Encontrar posición del video del usuario en los top 12
        user_position = find_user_video_position(top_videos, user_video['video_id'])
        
        # Si no está en los top 12, buscar en más resultados (hasta 50)
        if not user_position:
            user_position = search_extended_results(keyword, user_video['video_id'], 50)
        
        # Si el video del usuario está en los resultados top, lo removemos para evitar duplicados
        if user_position and user_position <= 12:
            top_videos = [v for v in top_videos if v['video_id'] != user_video['video_id']]
            user_video['found_in_results'] = True
        else:
            user_video['found_in_results'] = False
        
        # Establecer la posición encontrada
        user_video['position'] = user_position
        
        # Tomar solo los primeros 11 videos (ya que removimos el del usuario si estaba)
        top_videos = top_videos[:11]
        
        # Preparar datos para vista desktop y móvil
        desktop_view = prepare_desktop_view(top_videos, user_video)
        mobile_view = prepare_mobile_view(top_videos, user_video)
        
        return {
            'keyword': keyword,
            'user_video': user_video,
            'top_videos': top_videos,
            'desktop_view': desktop_view,
            'mobile_view': mobile_view,
            'show_titles': show_titles,
            'total_analyzed': len(top_videos) + 1,
            'search_date': datetime.now()
        }
        
    except Exception as e:
        raise Exception(str(e))

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