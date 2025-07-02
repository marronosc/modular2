import os
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import logging
from collections import defaultdict

# Configurar la API de YouTube
api_key = os.environ.get('YOUTUBE_API_KEY')
if api_key:
    youtube = build('youtube', 'v3', developerKey=api_key)
else:
    youtube = None

def analyze_video_activity(video_id, period_days=30, max_comments=2000):
    """
    Analiza la actividad reciente de un video basándose en comentarios
    """
    if not youtube:
        raise Exception("API de YouTube no configurada")
    
    try:
        # Obtener información básica del video
        video_info = get_video_info(video_id)
        
        # Obtener comentarios con fechas
        comments = get_video_comments(video_id, max_comments)
        
        # Analizar distribución temporal de comentarios
        activity_analysis = analyze_comment_distribution(comments, video_info['published_at'])
        
        # Calcular métricas de actividad reciente
        recent_metrics = calculate_recent_activity(
            activity_analysis, 
            video_info['views'],
            video_info['comments'],
            period_days,
            video_info['published_at']
        )
        
        return {
            'video_info': video_info,
            'total_comments_analyzed': len(comments),
            'recent_metrics': recent_metrics,
            'period_days': period_days
        }
        
    except Exception as e:
        raise Exception(f"Error analizando actividad del video: {str(e)}")

def get_video_info(video_id):
    """Obtiene información básica del video"""
    request = youtube.videos().list(
        part='snippet,statistics',
        id=video_id
    )
    response = request.execute()
    
    if not response.get('items'):
        raise Exception("Video no encontrado")
    
    video = response['items'][0]
    snippet = video['snippet']
    stats = video['statistics']
    
    return {
        'title': snippet.get('title'),
        'channel_title': snippet.get('channelTitle'),
        'published_at': datetime.strptime(snippet['publishedAt'], "%Y-%m-%dT%H:%M:%SZ"),
        'views': int(stats.get('viewCount', 0)),
        'likes': int(stats.get('likeCount', 0)),
        'comments': int(stats.get('commentCount', 0)),
        'thumbnail': snippet.get('thumbnails', {}).get('high', {}).get('url', '')
    }

def get_video_comments(video_id, max_results=2000):
    """Obtiene comentarios del video con sus fechas"""
    comments = []
    next_page_token = None
    
    while len(comments) < max_results:
        try:
            request = youtube.commentThreads().list(
                part='snippet,replies',
                videoId=video_id,
                maxResults=100,
                pageToken=next_page_token,
                order='time'
            )
            response = request.execute()
            
            for item in response.get('items', []):
                # Comentario principal
                top_comment = item['snippet']['topLevelComment']['snippet']
                comments.append({
                    'published_at': datetime.strptime(top_comment['publishedAt'], "%Y-%m-%dT%H:%M:%SZ"),
                    'type': 'comment'
                })
                
                # Respuestas
                if 'replies' in item:
                    for reply in item['replies']['comments']:
                        reply_snippet = reply['snippet']
                        comments.append({
                            'published_at': datetime.strptime(reply_snippet['publishedAt'], "%Y-%m-%dT%H:%M:%SZ"),
                            'type': 'reply'
                        })
                
                if len(comments) >= max_results:
                    break
            
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
                
        except Exception as e:
            logging.warning(f"Error obteniendo comentarios: {e}")
            break
    
    return comments

def analyze_comment_distribution(comments, video_published_date):
    """Analiza la distribución temporal de comentarios"""
    now = datetime.now()
    
    # Inicializar contadores
    distribution = {
        'by_day': defaultdict(int),
        'last_30_days': 0
    }
    
    # Fecha límite (30 días)
    thirty_days_ago = now - timedelta(days=30)
    
    for comment in comments:
        date = comment['published_at']
        
        # Por día (últimos 90 días para tener contexto)
        if date >= now - timedelta(days=90):
            day_key = date.strftime('%Y-%m-%d')
            distribution['by_day'][day_key] += 1
        
        # Contador de últimos 30 días
        if date >= thirty_days_ago:
            distribution['last_30_days'] += 1
    
    # Calcular edad del video en días
    video_age_days = (now - video_published_date).days
    distribution['video_age_days'] = video_age_days
    
    return distribution

def calculate_view_estimates(total_views, total_comments, period_comments, video_age_days):
    """
    Calcula estimaciones de visualizaciones usando el método de 3 tasas
    """
    # Evitar división por cero
    if total_views == 0 or total_comments == 0 or period_comments == 0:
        return {
            'low': 0,
            'medium': 0,
            'high': 0,
            'confidence': 'low'
        }
    
    # 1. Calcular tasa histórica
    historical_rate = total_comments / total_views
    
    # 2. Ajustar tasas según la edad del video
    age_factor = get_age_factor(video_age_days)
    
    # 3. Definir las 3 tasas ajustadas
    if video_age_days < 60:  # Videos muy nuevos
        low_multiplier = 0.5
        medium_multiplier = 0.7
        high_multiplier = 0.9
    elif video_age_days < 180:  # Videos recientes
        low_multiplier = 0.75
        medium_multiplier = 1.0
        high_multiplier = 1.25
    elif video_age_days < 730:  # Videos maduros
        low_multiplier = 0.8
        medium_multiplier = 1.0
        high_multiplier = 1.2
    else:  # Videos antiguos
        low_multiplier = 1.2
        medium_multiplier = 1.5
        high_multiplier = 2.0
    
    # Aplicar multiplicadores
    low_rate = historical_rate * high_multiplier    # Más comentarios por vista = menos vistas
    medium_rate = historical_rate * medium_multiplier
    high_rate = historical_rate * low_multiplier    # Menos comentarios por vista = más vistas
    
    # 4. Calcular estimaciones
    low_estimate = int(period_comments / high_rate) if high_rate > 0 else 0
    medium_estimate = int(period_comments / medium_rate) if medium_rate > 0 else 0
    high_estimate = int(period_comments / low_rate) if low_rate > 0 else 0
    
    # 5. Determinar nivel de confianza
    if total_comments < 100:
        confidence = 'low'
    elif total_comments < 1000:
        confidence = 'medium'
    else:
        confidence = 'high'
    
    return {
        'low': low_estimate,
        'medium': medium_estimate,
        'high': high_estimate,
        'confidence': confidence
    }

def get_age_factor(video_age_days):
    """Retorna el factor de ajuste según la edad del video"""
    if video_age_days < 30:
        return 0.6
    elif video_age_days < 60:
        return 0.8
    elif video_age_days < 180:
        return 0.95
    elif video_age_days < 365:
        return 1.0
    elif video_age_days < 730:
        return 1.3
    else:
        return 1.8

def calculate_recent_activity(distribution, total_views, total_comments, period_days, published_at):
    """Calcula métricas de actividad reciente con el método de 3 tasas"""
    
    video_age_days = distribution['video_age_days']
    period_comments = distribution['last_30_days']
    
    # Calcular estimaciones usando el método de 3 tasas
    view_estimates = calculate_view_estimates(
        total_views, 
        total_comments, 
        period_comments,
        video_age_days
    )
    
    # Calcular porcentajes del total
    percent_low = (view_estimates['low'] / total_views * 100) if total_views > 0 else 0
    percent_medium = (view_estimates['medium'] / total_views * 100) if total_views > 0 else 0
    percent_high = (view_estimates['high'] / total_views * 100) if total_views > 0 else 0
    
    # Generar interpretación
    interpretation = get_interpretation(percent_medium, video_age_days)
    
    # Formatear edad del video
    if video_age_days < 30:
        age_text = f"{video_age_days} días"
    elif video_age_days < 365:
        months = video_age_days // 30
        age_text = f"{months} {'mes' if months == 1 else 'meses'}"
    else:
        years = video_age_days // 365
        age_text = f"{years} {'año' if years == 1 else 'años'}"
    
    return {
        'period_comments': period_comments,
        'estimates': view_estimates,
        'percentages': {
            'low': round(percent_low, 1),
            'medium': round(percent_medium, 1),
            'high': round(percent_high, 1)
        },
        'interpretation': interpretation,
        'video_age': age_text,
        'video_age_days': video_age_days
    }

def get_interpretation(percent_medium, video_age_days):
    """Genera una interpretación basada en el porcentaje de vistas recientes"""
    if percent_medium > 10:
        return {
            'title': 'Video muy activo',
            'icon': '🔥',
            'text': 'Está recibiendo una cantidad significativa de visualizaciones recientemente. Representa más del 10% de todas sus vistas históricas en solo 30 días.',
            'class': 'very-active'
        }
    elif percent_medium > 5:
        return {
            'title': 'Buen rendimiento',
            'icon': '📈',
            'text': 'El video mantiene un flujo constante de visualizaciones. Está performando por encima del promedio para su edad.',
            'class': 'good-performance'
        }
    elif percent_medium > 2:
        return {
            'title': 'Actividad moderada',
            'icon': '📊',
            'text': f'El video sigue atrayendo audiencia de forma estable, típico para un video de {video_age_days // 30} meses de antigüedad.',
            'class': 'moderate-activity'
        }
    else:
        return {
            'title': 'Actividad baja',
            'icon': '📉',
            'text': 'El video recibe pocas visualizaciones nuevas. Considera promocionarlo o crear contenido relacionado para reactivar el interés.',
            'class': 'low-activity'
        }