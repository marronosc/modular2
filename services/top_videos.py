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
    """Obtiene los videos más vistos del canal usando search API optimizada"""
    try:
        videos = []
        next_page_token = None
        max_results_needed = max_results  # Solo obtener los videos que necesitamos
        total_fetched = 0
        
        logging.info(f"Buscando videos más vistos del canal {channel_id}")
        
        while len(videos) < max_results_needed:
            # Usar search API con order por viewCount para obtener directamente los más vistos
            request = youtube.search().list(
                part='snippet',
                channelId=channel_id,
                maxResults=50,
                order='viewCount',
                type='video',
                pageToken=next_page_token
            )
            response = request.execute()
            
            items = response.get('items', [])
            logging.info(f"Search API retornó {len(items)} items para canal {channel_id}")
            
            if not items:
                logging.warning(f"No se encontraron videos en search API para canal {channel_id}")
                # Intentar con orden diferente si no hay resultados
                if next_page_token is None:  # Solo en primera iteración
                    logging.info("Intentando con order='date' como fallback")
                    request_fallback = youtube.search().list(
                        part='snippet',
                        channelId=channel_id,
                        maxResults=50,
                        order='date',
                        type='video'
                    )
                    response_fallback = request_fallback.execute()
                    items = response_fallback.get('items', [])
                    logging.info(f"Fallback retornó {len(items)} items")
                
                if not items:
                    logging.error(f"No se encontraron videos para el canal {channel_id} con ningún orden")
                    break
                
            # Extraer video IDs para hacer batch request
            video_ids = [item['id']['videoId'] for item in items]
            
            # Obtener detalles de todos los videos en una sola llamada
            videos_details_request = youtube.videos().list(
                part='statistics,contentDetails,snippet,liveStreamingDetails',
                id=','.join(video_ids)
            )
            videos_details_response = videos_details_request.execute()
            
            videos_details_items = videos_details_response.get('items', [])
            
            logging.info(f"Procesando {len(videos_details_items)} videos")
            
            for video_item in videos_details_items:
                video_id = video_item['id']
                
                # Construir objeto de video usando datos combinados
                video_details = build_video_object(video_item, video_id)
                
                total_fetched += 1
                
                if video_details:
                    # Logging para debug
                    logging.info(f"Video procesado: {video_details.get('title', '')[:50]} - Duración: {video_details.get('duration_seconds', 0)}s - is_live: {video_details.get('is_live', False)}")
                    
                    if should_include_video(video_details, duration_filter):
                        videos.append(video_details)
                        logging.info(f"Video válido agregado: {video_details.get('title', '')[:50]} - Total: {len(videos)}")
                        
                        # Parar cuando tengamos suficientes videos válidos
                        if len(videos) >= max_results_needed:
                            logging.info(f"Alcanzados {len(videos)} videos válidos, parando búsqueda")
                            break
                    else:
                        logging.info(f"Video filtrado: {video_details.get('title', '')[:50]} - Razón: is_live={video_details.get('is_live')}, duration={video_details.get('duration_seconds')}s")
                else:
                    logging.warning(f"Video {video_id} no pudo ser procesado")
            
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                logging.info("No hay más páginas disponibles")
                break
                
            # Si ya tenemos suficientes videos válidos, parar completamente
            if len(videos) >= max_results_needed:
                logging.info(f"Completado: {len(videos)} videos válidos obtenidos")
                break
        
        logging.info(f"Total procesado: {total_fetched} videos, encontrados: {len(videos)} videos válidos")
        
        return videos
        
    except Exception as e:
        logging.error(f"Error obteniendo videos del canal {channel_id}: {str(e)}")
        raise Exception(f"Error obteniendo videos del canal: {str(e)}")

def build_video_object(video_item, video_id):
    """Construye el objeto de video con el formato esperado"""
    try:
        snippet = video_item.get('snippet', {})
        statistics = video_item.get('statistics', {})
        content_details = video_item.get('contentDetails', {})
        live_details = video_item.get('liveStreamingDetails', {})
        
        # Parsear fecha de publicación
        published_at_str = snippet.get('publishedAt', '')
        if published_at_str:
            # Convertir a datetime con timezone info y luego a naive UTC
            published_at = datetime.fromisoformat(published_at_str.replace('Z', '+00:00'))
            published_at = published_at.replace(tzinfo=None)  # Convertir a naive
        else:
            published_at = datetime.now()
        
        # Parsear duración
        duration_str = content_details.get('duration', 'PT0S')
        try:
            duration_obj = isodate.parse_duration(duration_str)
            duration_seconds = int(duration_obj.total_seconds())
        except:
            duration_seconds = 0
            duration_obj = timedelta(seconds=0)
        
        # Campos básicos de video
        views = int(statistics.get('viewCount', 0))
        likes = int(statistics.get('likeCount', 0))
        comments = int(statistics.get('commentCount', 0))
        
        # Verificar si es live
        is_live = 'actualStartTime' in live_details
        
        # Calcular métricas adicionales - asegurar que ambas fechas sean naive
        now_naive = datetime.now()
        age_days = (now_naive - published_at).days
        engagement_rate = (likes / views * 100) if views > 0 else 0
        views_per_day = (views / age_days) if age_days > 0 else views
        weekday = published_at.strftime('%A')
        
        # Traducir día de la semana
        weekday_es = translate_weekday(weekday)
        
        # Obtener categoría
        category_id = snippet.get('categoryId', '0')
        
        # Calcular índice de éxito usando la fórmula logarítmica
        success_index = calculate_success_index(views, age_days)
        
        return {
            'video_id': video_id,
            'title': snippet.get('title', 'Sin título'),
            'published_at': published_at,
            'thumbnail': snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
            'duration': duration_obj,
            'duration_formatted': format_duration(duration_obj),
            'duration_seconds': duration_seconds,
            'views': views,
            'likes': likes,
            'comments': comments,
            'video_url': f"https://www.youtube.com/watch?v={video_id}",
            'is_live': is_live,
            'is_short': duration_obj <= timedelta(seconds=90),
            'age_days': age_days,
            'engagement_rate': engagement_rate,
            'views_per_day': views_per_day,
            'weekday': weekday_es,
            'age_formatted': format_age(age_days),
            'success_index': success_index,
            'category': get_category_name(category_id),
            'category_id': category_id,
            'tags': snippet.get('tags', [])
        }
        
    except Exception as e:
        logging.error(f"Error construyendo objeto de video {video_id}: {str(e)}")
        return None

def calculate_success_index(visualizaciones, dias_desde_publicacion):
    """Calcula el índice de éxito de un video usando fórmula logarítmica"""
    try:
        dias = max(dias_desde_publicacion, 1)  # Evitar división por 0
        indice_exito = visualizaciones / math.log(dias + 1)
        return round(indice_exito, 2)
    except Exception as e:
        logging.error(f"Error al calcular el índice de éxito: {e}")
        return 0

def translate_weekday(weekday):
    """Traduce días de la semana al español"""
    translation = {
        'Monday': 'Lunes',
        'Tuesday': 'Martes', 
        'Wednesday': 'Miércoles',
        'Thursday': 'Jueves',
        'Friday': 'Viernes',
        'Saturday': 'Sábado',
        'Sunday': 'Domingo'
    }
    return translation.get(weekday, weekday)

def format_age(age_days):
    """Formatea la edad del video"""
    if age_days == 0:
        return "Hoy"
    elif age_days == 1:
        return "Ayer"
    elif age_days < 7:
        return f"Hace {age_days} días"
    elif age_days < 30:
        weeks = age_days // 7
        return f"Hace {weeks} semana{'s' if weeks > 1 else ''}"
    elif age_days < 365:
        months = age_days // 30
        return f"Hace {months} mes{'es' if months > 1 else ''}"
    else:
        years = age_days // 365
        return f"Hace {years} año{'s' if years > 1 else ''}"

def get_category_name(category_id):
    """Convierte el ID de categoría de YouTube a nombre legible"""
    categories = {
        '1': 'Cine y animación',
        '2': 'Coches y vehículos',
        '10': 'Música',
        '15': 'Mascotas y animales',
        '17': 'Deportes',
        '19': 'Viajes y eventos',
        '20': 'Videojuegos',
        '22': 'Gente y blogs',
        '23': 'Comedia',
        '24': 'Entretenimiento',
        '25': 'Noticias y política',
        '26': 'Guías y estilo',
        '27': 'Educación',
        '28': 'Ciencia y tecnología',
        '29': 'Sin fines de lucro y activismo'
    }
    return categories.get(str(category_id), 'Categoría desconocida')

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

# Reutilizar funciones del servicio recent_videos
from services.recent_videos import (
    get_video_details, should_include_video, get_filter_reason,
    calculate_basic_stats, identify_highlights, generate_insights,
    calculate_publication_frequency, format_number, format_date, 
    format_duration, get_sorted_videos, export_to_csv, generate_chart_data
)