import os
import logging
import math
from datetime import datetime, timedelta
import isodate
from googleapiclient.discovery import build

# Configurar la API de YouTube
api_key = os.environ.get('YOUTUBE_API_KEY')
if api_key:
    youtube = build('youtube', 'v3', developerKey=api_key)
else:
    youtube = None

def get_top_videos(channel_url, max_results=20, duration_filter=0):
    """
    Obtiene los top videos de un canal de YouTube ordenados por visualizaciones
    
    Args:
        channel_url (str): URL del canal o video
        max_results (int): Número de videos a obtener (default: 20)
        duration_filter (int): Filtro de duración en segundos. 0 = todos, 60 = >1min, etc.
    
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
        
        # Obtener TODOS los videos del canal para encontrar los top
        videos = get_all_channel_videos(channel_id, duration_filter)
        
        # Ordenar por visualizaciones (descendente) y tomar los top
        videos.sort(key=lambda x: x['views'], reverse=True)
        top_videos = videos[:max_results]
        
        # Calcular estadísticas y análisis
        stats = calculate_basic_stats(top_videos) if top_videos else {}
        highlights = identify_highlights(top_videos) if top_videos else {}
        insights = generate_insights(top_videos) if top_videos else {}
        frequency = calculate_publication_frequency(top_videos) if top_videos else {}
        
        return {
            'channel_info': channel_info,
            'videos': top_videos,
            'total_videos': len(top_videos),
            'stats': stats,
            'highlights': highlights,
            'insights': insights,
            'frequency': frequency,
            'analysis_type': 'top_videos',
            'total_videos_analyzed': len(videos)
        }
        
    except Exception as e:
        logging.error(f"Error obteniendo top videos: {str(e)}")
        raise e

def get_channel_info(channel_id):
    """Obtiene información básica del canal"""
    try:
        request = youtube.channels().list(
            part='snippet,statistics',
            id=channel_id
        )
        response = request.execute()
        
        if not response.get('items'):
            return None
        
        channel = response['items'][0]
        snippet = channel['snippet']
        statistics = channel['statistics']
        
        return {
            'id': channel_id,
            'title': snippet.get('title', 'Canal sin nombre'),
            'description': snippet.get('description', '')[:200] + '...' if len(snippet.get('description', '')) > 200 else snippet.get('description', ''),
            'thumbnail': snippet.get('thumbnails', {}).get('high', {}).get('url', ''),
            'subscriber_count': int(statistics.get('subscriberCount', 0)),
            'video_count': int(statistics.get('videoCount', 0)),
            'view_count': int(statistics.get('viewCount', 0))
        }
    except Exception as e:
        logging.error(f"Error obteniendo información del canal {channel_id}: {str(e)}")
        return None

def get_all_channel_videos(channel_id, duration_filter=0):
    """Obtiene TODOS los videos del canal usando uploads playlist"""
    try:
        # Primero obtener el uploads playlist ID del canal
        channel_request = youtube.channels().list(
            part='contentDetails',
            id=channel_id
        )
        channel_response = channel_request.execute()
        
        if not channel_response.get('items'):
            raise Exception(f"No se pudo obtener información del canal: {channel_id}")
        
        uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        logging.info(f"Usando uploads playlist: {uploads_playlist_id}")
        
        videos = []
        next_page_token = None
        total_fetched = 0
        max_iterations = 50  # Incrementado para obtener más videos
        iterations = 0
        
        while iterations < max_iterations:
            iterations += 1
            
            # Usar playlistItems para obtener videos
            request = youtube.playlistItems().list(
                part='snippet',
                playlistId=uploads_playlist_id,
                maxResults=50,
                pageToken=next_page_token
            )
            response = request.execute()
            
            items = response.get('items', [])
            if not items:
                logging.info("No hay más videos en la playlist")
                break
            
            logging.info(f"Iteración {iterations}: procesando {len(items)} videos de playlist")
            
            for item in items:
                video_id = item['snippet']['resourceId']['videoId']
                video_details = get_video_details(video_id, item['snippet'])
                
                total_fetched += 1
                
                if video_details and should_include_video(video_details, duration_filter):
                    videos.append(video_details)
                    if len(videos) % 50 == 0:  # Log cada 50 videos válidos
                        logging.info(f"Videos válidos encontrados: {len(videos)}")
            
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                logging.info("No hay más páginas en la playlist")
                break
        
        logging.info(f"Total procesado: {total_fetched} videos, encontrados: {len(videos)} videos válidos")
        
        return videos
        
    except Exception as e:
        logging.error(f"Error obteniendo todos los videos del canal {channel_id}: {str(e)}")
        raise Exception(f"Error obteniendo videos del canal: {str(e)}")

# Reutilizar funciones del servicio recent_videos
from services.recent_videos import (
    get_video_details, should_include_video, get_filter_reason,
    calculate_basic_stats, identify_highlights, generate_insights,
    calculate_publication_frequency, format_number, format_date, 
    format_duration, get_sorted_videos, export_to_csv, generate_chart_data
)