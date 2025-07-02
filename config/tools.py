# config/tools.py
"""
Configuración centralizada de todas las herramientas de TubeTools
"""

TOOLS_CONFIG = {
    # Herramientas activas
    'extractor': {
        'name': 'Extractor de ID',
        'description': 'Obtén el ID único de cualquier canal de YouTube',
        'url': '/extractor',
        'icon': 'document',
        'category': 'utility',
        'color': '#667eea',
        'status': 'active',
        'tags': ['Utilidades', 'Instantáneo', 'URLs múltiples']
    },
    'seo': {
        'name': 'Análisis SEO',
        'description': 'Analiza los primeros 20 resultados de búsqueda',
        'url': '/seo',
        'icon': 'search',
        'category': 'seo',
        'color': '#4caf50',
        'status': 'active',
        'tags': ['SEO', 'Keywords', '20 resultados']
    },
    'keyword_position': {
        'name': 'Verificador Posición',
        'description': 'Descubre si videos aparecen en los primeros 200 resultados',
        'url': '/keyword-position',
        'icon': 'check-circle',
        'category': 'analysis',
        'color': '#ff9800',
        'status': 'active',
        'tags': ['Análisis', '200 resultados', 'Posicionamiento']
    },
    'thumbnail_comparison': {
        'name': 'Comparador Miniaturas',
        'description': 'Compara tu miniatura con los videos mejor posicionados',
        'url': '/thumbnail-comparison',
        'icon': 'image',
        'category': 'design',
        'color': '#e91e63',
        'status': 'active',
        'tags': ['Diseño', 'Vista desktop', 'Vista móvil']
    },
    'video_activity': {
        'name': 'Análisis Actividad',
        'description': 'Estima visualizaciones recientes basado en comentarios',
        'url': '/video-activity',
        'icon': 'trending-up',
        'category': 'analytics',
        'color': '#3f51b5',
        'status': 'active',
        'tags': ['Analytics', '30 días', '3 estimaciones']
    },
    'keyword_research': {
        'name': 'Investigador Keywords',
        'description': 'Descubre sugerencias reales de YouTube',
        'url': '/keyword-research',
        'icon': 'search-plus',
        'category': 'research',
        'color': '#9c27b0',
        'status': 'active',
        'tags': ['Keywords', 'Sugerencias reales', 'Exportación']
    },
    'competitor_report': {
        'name': 'Informe Competencias',
        'description': 'Análisis completo del rendimiento de canales competidores',
        'url': '/competitor-report',
        'icon': 'bar-chart',
        'category': 'analytics',
        'color': '#9e9e9e',
        'status': 'active',
        'tags': ['Competencia', 'Informes']
    },
    'top_videos': {
        'name': 'TOP 20 Videos',
        'description': 'Descubre los videos más exitosos de tus competidores',
        'url': '/top-videos',
        'icon': 'star',
        'category': 'analytics',
        'color': '#9e9e9e',
        'status': 'active',
        'tags': ['Competencia', 'Rankings']
    },
    'recent_videos': {
        'name': 'Últimos 20 Videos',
        'description': 'Monitorea la actividad reciente de tus competidores (solo videos regulares)',
        'url': '/recent-videos',
        'icon': 'clock',
        'category': 'analytics',
        'color': '#9e9e9e',
        'status': 'active',
        'tags': ['Competencia', 'Recientes', 'Sin Shorts']
    }
}

ICONS = {
    'document': '<path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z" />',
    'search': '<path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z" />',
    'check-circle': '<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />',
    'image': '<path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z" />',
    'trending-up': '<path d="M16,6L18.29,8.29L13.41,13.17L9.41,9.17L2,16.59L3.41,18L9.41,12L13.41,16L19.71,9.71L22,12V6H16Z" />',
    'search-plus': '<path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z" /><path d="M12 10h-2v2H8v-2H6V8h2V6h2v2h2v2z" />',
    'bar-chart': '<path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z" />',
    'star': '<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />',
    'clock': '<path d="M12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12.5,7V12.25L17,14.92L16.25,16.15L11,13V7H12.5Z" />',
    'home': '<path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z" />',
    'settings': '<path d="M19.14,12.94c0.04-0.3,0.06-0.61,0.06-0.94c0-0.32-0.02-0.64-0.07-0.94l2.03-1.58c0.18-0.14,0.23-0.41,0.12-0.61 l-1.92-3.32c-0.12-0.22-0.37-0.29-0.59-0.22l-2.39,0.96c-0.5-0.38-1.03-0.7-1.62-0.94L14.4,2.81c-0.04-0.24-0.24-0.41-0.48-0.41 h-3.84c-0.24,0-0.43,0.17-0.47,0.41L9.25,5.35C8.66,5.59,8.12,5.92,7.63,6.29L5.24,5.33c-0.22-0.08-0.47,0-0.59,0.22L2.74,8.87 C2.62,9.08,2.66,9.34,2.86,9.48l2.03,1.58C4.84,11.36,4.82,11.69,4.82,12s0.02,0.64,0.07,0.94l-2.03,1.58 c-0.18,0.14-0.23,0.41-0.12,0.61l1.92,3.32c0.12,0.22,0.37,0.29,0.59,0.22l2.39-0.96c0.5,0.38,1.03,0.7,1.62,0.94l0.36,2.54 c0.05,0.24,0.24,0.41,0.48,0.41h3.84c0.24,0,0.44-0.17,0.47-0.41l0.36-2.54c0.59-0.24,1.13-0.56,1.62-0.94l2.39,0.96 c0.22,0.08,0.47,0,0.59-0.22l1.92-3.32c0.12-0.22,0.07-0.47-0.12-0.61L19.14,12.94z M12,15.6c-1.98,0-3.6-1.62-3.6-3.6 s1.62-3.6,3.6-3.6s3.6,1.62,3.6,3.6S13.98,15.6,12,15.6z" />',
    'help': '<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 17h-2v-2h2v2zm2.07-7.75l-.9.92C13.45 12.9 13 13.5 13 15h-2v-.5c0-1.1.45-2.1 1.17-2.83l1.24-1.26c.37-.36.59-.86.59-1.41 0-1.1-.9-2-2-2s-2 .9-2 2H8c0-2.21 1.79-4 4-4s4 1.79 4 4c0 .88-.36 1.68-.93 2.25z" />'
}

def get_active_tools():
    return {k: v for k, v in TOOLS_CONFIG.items() if v['status'] == 'active'}

def get_coming_soon_tools():
    return {k: v for k, v in TOOLS_CONFIG.items() if v['status'] == 'coming_soon'}

def get_tool_by_id(tool_id):
    return TOOLS_CONFIG.get(tool_id)

def get_tools_by_category(category):
    return {k: v for k, v in TOOLS_CONFIG.items() if v['category'] == category}
