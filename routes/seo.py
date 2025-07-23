from flask import Blueprint, request, render_template, redirect, url_for
from services.seo_analyzer import search_videos, calculate_average_duration, count_unique_channels
from services.seo_analyzer import get_channel_stats, categorize_videos_by_age, calculate_total_stats
from services.seo_analyzer import format_number, format_date, format_duration, analyze_data_insights
from services.recent_videos import generate_chart_data

seo_bp = Blueprint('seo', __name__, url_prefix='/seo')

@seo_bp.route('/', methods=['GET', 'POST'])
def seo():
    if request.method == 'POST':
        keyword = request.form['keyword']
        return redirect(url_for('seo.generate_report', keyword=keyword))
    
    return render_template('seo/index.html')

@seo_bp.route('/report/<keyword>')
def generate_report(keyword):
    try:
        videos = search_videos(keyword, max_results=20)
        
        if videos:
            avg_views = sum(video['views'] for video in videos) / len(videos)
            avg_likes = sum(video['likes'] for video in videos) / len(videos)
            avg_comments = sum(video['comments'] for video in videos) / len(videos)
            avg_duration = calculate_average_duration(videos)
            unique_channels_count = count_unique_channels(videos)
            channel_stats = get_channel_stats(videos)
            last_6_months, last_year, older_than_year = categorize_videos_by_age(videos)
            total_stats = calculate_total_stats(videos)
            chart_data = generate_chart_data(videos)
            data_insights = analyze_data_insights(videos)
        else:
            avg_views = avg_likes = avg_comments = 0
            avg_duration = None
            unique_channels_count = 0
            channel_stats = {}
            last_6_months = last_year = older_than_year = []
            total_stats = {'total_views': 0, 'total_likes': 0, 'total_comments': 0}
            chart_data = {}
            data_insights = {}

        return render_template('seo/report.html',
            keyword=keyword,
            videos=videos,
            avg_views_videos=avg_views,
            avg_likes_videos=avg_likes,
            avg_comments_videos=avg_comments,
            avg_duration=avg_duration,
            unique_channels_count=unique_channels_count,
            channel_stats=channel_stats,
            last_6_months=last_6_months,
            last_year=last_year,
            older_than_year=older_than_year,
            total_stats=total_stats,
            chart_data=chart_data,
            data_insights=data_insights,
            format_number=format_number,
            format_date=format_date,
            format_duration=format_duration
        )
    except Exception as e:
        error_message = f"Error al generar el informe: {str(e)}"
        return render_template('seo/error.html', error=error_message, keyword=keyword)