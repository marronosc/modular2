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
        
        # Calcular estadísticas y análisis
        stats = calculate_basic_stats(videos) if videos else {}
        highlights = identify_highlights(videos) if videos else {}
        insights = generate_insights(videos) if videos else {}
        frequency = calculate_publication_frequency(videos) if videos else {}
        
        return {
            'channel_info': channel_info,
            'videos': videos,
            'total_videos': len(videos),
            'stats': stats,
            'highlights': highlights,
            'insights': insights,
            'frequency': frequency,
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
    """Obtiene los videos más recientes del canal usando uploads playlist"""
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
        max_iterations = 10
        iterations = 0
        
        while len(videos) < max_results and iterations < max_iterations:
            iterations += 1
            
            # Usar playlistItems para obtener videos en orden cronológico exacto
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
                
                if video_details and is_regular_video(video_details):
                    videos.append(video_details)
                    logging.info(f"Video {len(videos)} incluido: {video_details['title'][:50]}... (Fecha: {video_details['published_at'].strftime('%Y-%m-%d')})")
                    
                    if len(videos) >= max_results:
                        logging.info(f"Se encontraron {max_results} videos regulares")
                        break
                else:
                    if video_details:
                        video_type = "Short" if video_details['is_short'] else "Live" if video_details['is_live'] else "Unknown"
                        logging.info(f"Video filtrado ({video_type}): {video_details['title'][:30]}...")
            
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                logging.info("No hay más páginas en la playlist")
                break
        
        logging.info(f"Total procesado: {total_fetched} videos, encontrados: {len(videos)} videos regulares")
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
        
        published_at = datetime.strptime(snippet['publishedAt'], "%Y-%m-%dT%H:%M:%SZ")
        views = int(statistics.get('viewCount', 0))
        likes = int(statistics.get('likeCount', 0))
        comments = int(statistics.get('commentCount', 0))
        
        # Calcular métricas adicionales
        age_days = (datetime.now() - published_at).days
        engagement_rate = (likes / views * 100) if views > 0 else 0
        views_per_day = (views / age_days) if age_days > 0 else views
        weekday = published_at.strftime('%A')
        weekday_es = translate_weekday(weekday)
        
        return {
            'video_id': video_id,
            'title': snippet.get('title', 'Sin título'),
            'published_at': published_at,
            'thumbnail': snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
            'duration': duration,
            'duration_formatted': format_duration(duration),
            'duration_seconds': int(duration.total_seconds()),
            'views': views,
            'likes': likes,
            'comments': comments,
            'video_url': f"https://www.youtube.com/watch?v={video_id}",
            'is_live': is_live,
            'is_short': duration <= timedelta(seconds=60),
            # Nuevas métricas
            'age_days': age_days,
            'engagement_rate': engagement_rate,
            'views_per_day': views_per_day,
            'weekday': weekday_es,
            'age_formatted': format_age(age_days)
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

def format_age(days):
    """Formatea la edad del video en texto legible"""
    if days == 0:
        return "Hoy"
    elif days == 1:
        return "Ayer"
    elif days < 7:
        return f"Hace {days} días"
    elif days < 30:
        weeks = days // 7
        return f"Hace {weeks} semana{'s' if weeks > 1 else ''}"
    elif days < 365:
        months = days // 30
        return f"Hace {months} mes{'es' if months > 1 else ''}"
    else:
        years = days // 365
        return f"Hace {years} año{'s' if years > 1 else ''}"

def calculate_basic_stats(videos):
    """Calcula estadísticas básicas de los videos"""
    if not videos:
        return {}
    
    total_views = sum(v['views'] for v in videos)
    total_likes = sum(v['likes'] for v in videos)
    total_comments = sum(v['comments'] for v in videos)
    total_duration = sum(v['duration_seconds'] for v in videos)
    
    # Promedios
    avg_views = total_views / len(videos)
    avg_likes = total_likes / len(videos)
    avg_comments = total_comments / len(videos)
    avg_duration = total_duration / len(videos)
    avg_engagement = sum(v['engagement_rate'] for v in videos) / len(videos)
    
    # Tendencia simple (últimos 5 vs anteriores)
    if len(videos) >= 10:
        recent_videos = videos[:5]  # Ya están ordenados por fecha desc
        older_videos = videos[-5:]
        
        recent_avg_views = sum(v['views'] for v in recent_videos) / len(recent_videos)
        older_avg_views = sum(v['views'] for v in older_videos) / len(older_videos)
        
        trend_percentage = ((recent_avg_views - older_avg_views) / older_avg_views * 100) if older_avg_views > 0 else 0
        trend_direction = 'crecimiento' if trend_percentage > 5 else 'declive' if trend_percentage < -5 else 'estable'
    else:
        trend_percentage = 0
        trend_direction = 'sin_datos'
        recent_avg_views = avg_views
        older_avg_views = avg_views
    
    return {
        'total_views': total_views,
        'total_likes': total_likes,
        'total_comments': total_comments,
        'avg_views': avg_views,
        'avg_likes': avg_likes,
        'avg_comments': avg_comments,
        'avg_duration_seconds': avg_duration,
        'avg_duration_formatted': format_duration(timedelta(seconds=avg_duration)),
        'avg_engagement': avg_engagement,
        'trend_direction': trend_direction,
        'trend_percentage': abs(trend_percentage),
        'recent_avg_views': recent_avg_views,
        'older_avg_views': older_avg_views
    }

def identify_highlights(videos):
    """Identifica videos destacados"""
    if not videos:
        return {}
    
    # Videos por rendimiento
    best_video = max(videos, key=lambda x: x['views'])
    worst_video = min(videos, key=lambda x: x['views'])
    most_recent = videos[0]  # Ya están ordenados por fecha desc
    
    # Video con mejor engagement
    best_engagement = max(videos, key=lambda x: x['engagement_rate'])
    
    # Video con mejor velocidad de crecimiento
    best_growth = max(videos, key=lambda x: x['views_per_day'])
    
    return {
        'best_performing': best_video,
        'worst_performing': worst_video,
        'most_recent': most_recent,
        'best_engagement': best_engagement,
        'fastest_growing': best_growth
    }

def generate_insights(videos):
    """Genera insights automáticos"""
    if not videos:
        return {}
    
    # Análisis de días de publicación
    weekday_performance = {}
    for video in videos:
        day = video['weekday']
        if day not in weekday_performance:
            weekday_performance[day] = {'count': 0, 'total_views': 0, 'total_engagement': 0}
        
        weekday_performance[day]['count'] += 1
        weekday_performance[day]['total_views'] += video['views']
        weekday_performance[day]['total_engagement'] += video['engagement_rate']
    
    # Calcular promedios por día
    for day in weekday_performance:
        count = weekday_performance[day]['count']
        weekday_performance[day]['avg_views'] = weekday_performance[day]['total_views'] / count
        weekday_performance[day]['avg_engagement'] = weekday_performance[day]['total_engagement'] / count
    
    # Mejor día por views
    best_day_views = max(weekday_performance.keys(), key=lambda x: weekday_performance[x]['avg_views']) if weekday_performance else None
    
    # Análisis de duración óptima
    duration_ranges = {
        'corto': {'min': 0, 'max': 300, 'videos': []},      # 0-5 min
        'medio': {'min': 300, 'max': 900, 'videos': []},    # 5-15 min  
        'largo': {'min': 900, 'max': float('inf'), 'videos': []}  # 15+ min
    }
    
    for video in videos:
        duration = video['duration_seconds']
        for range_name, range_data in duration_ranges.items():
            if range_data['min'] <= duration < range_data['max']:
                range_data['videos'].append(video)
                break
    
    # Calcular rendimiento por rango de duración
    duration_performance = {}
    for range_name, range_data in duration_ranges.items():
        if range_data['videos']:
            avg_views = sum(v['views'] for v in range_data['videos']) / len(range_data['videos'])
            avg_engagement = sum(v['engagement_rate'] for v in range_data['videos']) / len(range_data['videos'])
            duration_performance[range_name] = {
                'count': len(range_data['videos']),
                'avg_views': avg_views,
                'avg_engagement': avg_engagement
            }
    
    # Mejor rango de duración
    best_duration_range = max(duration_performance.keys(), key=lambda x: duration_performance[x]['avg_views']) if duration_performance else None
    
    # Análisis de patrones en títulos
    title_patterns = analyze_title_patterns(videos)
    
    return {
        'weekday_performance': weekday_performance,
        'best_day_for_views': best_day_views,
        'duration_performance': duration_performance,
        'best_duration_range': best_duration_range,
        'title_patterns': title_patterns
    }

def analyze_title_patterns(videos):
    """Analiza patrones en títulos exitosos"""
    if len(videos) < 5:
        return {}
    
    # Obtener videos con mejor rendimiento (top 25%)
    sorted_by_views = sorted(videos, key=lambda x: x['views'], reverse=True)
    top_videos = sorted_by_views[:max(1, len(videos) // 4)]
    
    # Palabras comunes en títulos exitosos
    successful_words = {}
    for video in top_videos:
        words = video['title'].lower().split()
        for word in words:
            # Filtrar palabras comunes/irrelevantes
            if len(word) > 3 and word not in ['para', 'como', 'que', 'con', 'una', 'por', 'the', 'and', 'for']:
                successful_words[word] = successful_words.get(word, 0) + 1
    
    # Obtener las 5 palabras más frecuentes
    top_words = sorted(successful_words.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Análisis de longitud de título
    avg_title_length = sum(len(v['title']) for v in top_videos) / len(top_videos)
    
    return {
        'successful_words': dict(top_words),
        'optimal_title_length': int(avg_title_length)
    }

def calculate_publication_frequency(videos):
    """Calcula estadísticas de frecuencia de publicación"""
    if len(videos) < 2:
        return {}
    
    # Ordenar por fecha de publicación (más reciente primero)
    sorted_videos = sorted(videos, key=lambda x: x['published_at'], reverse=True)
    
    # Calcular intervalos entre publicaciones
    intervals = []
    for i in range(1, len(sorted_videos)):
        diff = sorted_videos[i-1]['published_at'] - sorted_videos[i]['published_at']
        intervals.append(diff.days)
    
    # Estadísticas básicas
    avg_days_between = sum(intervals) / len(intervals) if intervals else 0
    min_interval = min(intervals) if intervals else 0
    max_interval = max(intervals) if intervals else 0
    
    # Frecuencia por semana/mes
    videos_per_week = 7 / avg_days_between if avg_days_between > 0 else 0
    videos_per_month = 30 / avg_days_between if avg_days_between > 0 else 0
    
    # Días desde el último video
    days_since_last = (datetime.now() - sorted_videos[0]['published_at']).days
    
    # Predicción del próximo video (basado en promedio)
    predicted_days = max(0, int(avg_days_between - days_since_last))
    
    # Análisis de consistencia
    consistency_score = calculate_consistency_score(intervals)
    
    return {
        'avg_days_between': avg_days_between,
        'min_interval': min_interval,
        'max_interval': max_interval,
        'videos_per_week': videos_per_week,
        'videos_per_month': videos_per_month,
        'days_since_last': days_since_last,
        'predicted_next_days': predicted_days,
        'consistency_score': consistency_score,
        'total_intervals': len(intervals)
    }

def calculate_consistency_score(intervals):
    """Calcula un score de consistencia de publicación (0-100)"""
    if len(intervals) < 3:
        return 50  # Score neutral para pocos datos
    
    avg = sum(intervals) / len(intervals)
    variance = sum((x - avg) ** 2 for x in intervals) / len(intervals)
    std_dev = variance ** 0.5
    
    # Score basado en desviación estándar relativa
    coefficient_variation = std_dev / avg if avg > 0 else 1
    consistency = max(0, 100 - (coefficient_variation * 50))
    
    return min(100, consistency)

def get_sorted_videos(videos, sort_by='date', order='desc'):
    """Ordena videos según criterio especificado"""
    sort_functions = {
        'date': lambda x: x['published_at'],
        'views': lambda x: x['views'],
        'likes': lambda x: x['likes'],
        'comments': lambda x: x['comments'],
        'engagement': lambda x: x['engagement_rate'],
        'duration': lambda x: x['duration_seconds'],
        'growth': lambda x: x['views_per_day']
    }
    
    if sort_by not in sort_functions:
        sort_by = 'date'
    
    reverse = order == 'desc'
    return sorted(videos, key=sort_functions[sort_by], reverse=reverse)

def export_to_csv(result):
    """Genera datos para exportar a CSV"""
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Headers
    headers = [
        'Título', 'Fecha Publicación', 'Día Semana', 'Views', 'Likes', 'Comentarios',
        'Duración', 'Engagement %', 'Views/Día', 'Edad (días)', 'URL'
    ]
    writer.writerow(headers)
    
    # Data rows
    for video in result['videos']:
        row = [
            video['title'],
            video['published_at'].strftime('%Y-%m-%d'),
            video['weekday'],
            video['views'],
            video['likes'],
            video['comments'],
            video['duration_formatted'],
            f"{video['engagement_rate']:.2f}",
            int(video['views_per_day']),
            video['age_days'],
            video['video_url']
        ]
        writer.writerow(row)
    
    return output.getvalue()

def generate_chart_data(videos):
    """Genera datos para gráficos"""
    if not videos:
        return {}
    
    # Datos para gráfico de views por video
    views_data = {
        'labels': [f"Video {i+1}" for i in range(len(videos))],
        'views': [v['views'] for v in videos],
        'titles': [v['title'][:30] + '...' if len(v['title']) > 30 else v['title'] for v in videos]
    }
    
    # Datos para gráfico de engagement por video  
    engagement_data = {
        'labels': views_data['labels'],
        'engagement': [v['engagement_rate'] for v in videos],
        'titles': views_data['titles']
    }
    
    # Datos para timeline de publicaciones
    timeline_data = {
        'dates': [v['published_at'].strftime('%Y-%m-%d') for v in videos],
        'views': [v['views'] for v in videos],
        'titles': views_data['titles']
    }
    
    # Distribución de duración
    duration_ranges = {'0-5min': 0, '5-15min': 0, '15-30min': 0, '30min+': 0}
    for video in videos:
        seconds = video['duration_seconds']
        if seconds <= 300:
            duration_ranges['0-5min'] += 1
        elif seconds <= 900:
            duration_ranges['5-15min'] += 1
        elif seconds <= 1800:
            duration_ranges['15-30min'] += 1
        else:
            duration_ranges['30min+'] += 1
    
    return {
        'views_chart': views_data,
        'engagement_chart': engagement_data,
        'timeline_chart': timeline_data,
        'duration_distribution': duration_ranges
    }