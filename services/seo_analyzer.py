import os
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import isodate
from collections import Counter, defaultdict

# Configurar la API de YouTube
api_key = os.environ.get('YOUTUBE_API_KEY')
if api_key:
    youtube = build('youtube', 'v3', developerKey=api_key)
else:
    youtube = None

# Funciones auxiliares para formateo
def format_number(value):
    if isinstance(value, (int, float)):
        return f"{value:,.0f}"
    return str(value)

def format_date(value):
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    return str(value)

def format_duration(duration):
    if isinstance(duration, timedelta):
        hours, remainder = divmod(duration.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{int(hours)}:{int(minutes):02d}:{int(seconds):02d}"
        else:
            return f"{int(minutes):02d}:{int(seconds):02d}"
    return str(duration) if duration else "00:00"

def search_videos(keyword, max_results=20):
    if not youtube:
        raise Exception("API de YouTube no configurada. Verifica la variable YOUTUBE_API_KEY")
    
    try:
        videos = []
        next_page_token = None
        
        while len(videos) < max_results:
            request = youtube.search().list(
                q=keyword,
                type='video',
                part='id,snippet',
                maxResults=50,
                pageToken=next_page_token
            )
            response = request.execute()
            
            for item in response['items']:
                # Verificar que el item tiene la estructura correcta
                if 'id' not in item or 'videoId' not in item['id']:
                    continue
                
                video_id = item['id']['videoId']
                video_data = youtube.videos().list(part='contentDetails,statistics,snippet', id=video_id).execute()
                
                if 'items' not in video_data or len(video_data['items']) == 0:
                    continue
                
                video_item = video_data['items'][0]
                
                duration_str = video_item['contentDetails']['duration']
                duration = isodate.parse_duration(duration_str)
                
                # Filtrar videos que duran más de 1 minuto y 2 segundos
                if duration < timedelta(minutes=1, seconds=2):
                    continue
                
                published_at = datetime.strptime(item['snippet']['publishedAt'], "%Y-%m-%dT%H:%M:%SZ")
                day_of_week = published_at.strftime('%A')
                
                video_stats = video_item['statistics']
                
                views = int(video_stats.get('viewCount', 0))
                likes = int(video_stats.get('likeCount', 0))
                comments = int(video_stats.get('commentCount', 0))
                
                # Calcular engagement_rate
                total_engagement = likes + comments
                engagement_rate = (total_engagement / views * 100) if views > 0 else 0
                
                video_details = {
                    'title': item['snippet'].get('title', 'Sin título'),
                    'published_at': published_at,
                    'day_of_week': day_of_week,
                    'views': views,
                    'likes': likes,
                    'comments': comments,
                    'duration': duration,
                    'duration_seconds': int(duration.total_seconds()),
                    'video_url': f"https://www.youtube.com/watch?v={video_id}",
                    'thumbnail_url': item['snippet'].get('thumbnails', {}).get('medium', {}).get('url', ''),
                    'category': get_video_category(video_item['snippet'].get('categoryId', '')),
                    'channel_title': item['snippet'].get('channelTitle', 'Desconocido'),
                    'engagement_rate': engagement_rate
                }
                
                videos.append(video_details)
                
                if len(videos) == max_results:
                    break
            
            if len(videos) == max_results:
                break
            
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
        
        return videos
    except Exception as e:
        raise Exception(f"Error al buscar videos: {str(e)}")

def get_video_category(category_id):
    if not youtube:
        return "Desconocida"
    
    try:
        request = youtube.videoCategories().list(
            part='snippet',
            id=category_id
        )
        response = request.execute()
        if 'items' in response and len(response['items']) > 0:
            return response['items'][0]['snippet']['title']
        return "Desconocida"
    except Exception as e:
        return "Desconocida"

def calculate_average_duration(videos):
    if not videos:
        return timedelta()
    total_duration = sum((video['duration'] for video in videos), timedelta())
    return total_duration / len(videos)

def count_unique_channels(videos):
    return len(set(video['channel_title'] for video in videos))

def get_channel_stats(videos):
    channel_stats = defaultdict(lambda: {'videos': 0, 'views': 0, 'likes': 0, 'comments': 0, 'thumbnail': ''})
    for video in videos:
        channel = video['channel_title']
        channel_stats[channel]['videos'] += 1
        channel_stats[channel]['views'] += video['views']
        channel_stats[channel]['likes'] += video['likes']
        channel_stats[channel]['comments'] += video['comments']
        if not channel_stats[channel]['thumbnail']:
            channel_stats[channel]['thumbnail'] = video['thumbnail_url']
    return dict(channel_stats)

def categorize_videos_by_age(videos):
    now = datetime.now()
    six_months_ago = now - timedelta(days=180)
    one_year_ago = now - timedelta(days=365)
    
    last_6_months = []
    last_year = []
    older_than_year = []
    
    for video in videos:
        if video['published_at'] > six_months_ago:
            last_6_months.append(video)
        elif video['published_at'] > one_year_ago:
            last_year.append(video)
        else:
            older_than_year.append(video)
    
    return last_6_months, last_year, older_than_year

def calculate_total_stats(videos):
    return {
        'total_views': sum(video['views'] for video in videos),
        'total_likes': sum(video['likes'] for video in videos),
        'total_comments': sum(video['comments'] for video in videos)
    }