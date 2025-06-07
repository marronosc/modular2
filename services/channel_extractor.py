import os
import re
import requests
from urllib.parse import urlparse, parse_qs
import logging
import json

def obtener_id_canal(url):
    """
    Extrae el ID del canal de YouTube desde cualquier URL relacionada
    """
    logging.info(f"Procesando URL: {url}")
    
    if not url or not url.strip():
        logging.error("URL vacía o None")
        return None
    
    # Normaliza la URL
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    try:
        parsed_url = urlparse(url)
    except Exception as e:
        logging.error(f"Error al parsear URL: {e}")
        return None
    
    # Comprueba si es una URL de YouTube válida
    if not any(domain in parsed_url.netloc.lower() for domain in ['youtube.com', 'youtu.be', 'm.youtube.com']):
        logging.warning(f"URL no válida de YouTube: {parsed_url.netloc}")
        return None

    # Intenta extraer el ID del canal directamente de la URL
    path_parts = [part for part in parsed_url.path.strip('/').split('/') if part]
    logging.debug(f"Partes de la ruta: {path_parts}")

    # Caso 1: URL directa del canal (/channel/UCxxxxx)
    if len(path_parts) >= 2 and path_parts[0] == 'channel':
        channel_id = path_parts[1]
        if es_channel_id_valido(channel_id):
            logging.info(f"ID de canal encontrado en la URL: {channel_id}")
            return channel_id
    
    # Caso 2: URLs cortas de youtu.be (youtu.be/video_id)
    if 'youtu.be' in parsed_url.netloc and path_parts:
        video_id = path_parts[0].split('?')[0]  # Remover parámetros de query
        if video_id:
            logging.info(f"Video ID encontrado en youtu.be: {video_id}")
            return obtener_id_desde_video(video_id)
    
    # Caso 3: URLs de vídeo (youtube.com/watch?v=...)
    if 'watch' in path_parts and parsed_url.query:
        video_id = parse_qs(parsed_url.query).get('v', [None])[0]
        if video_id:
            logging.info(f"Video ID encontrado en watch: {video_id}")
            return obtener_id_desde_video(video_id)
    
    # Caso 4: URLs de usuario personalizado
    if path_parts:
        # @usuario, /c/usuario, /user/usuario
        if path_parts[0].startswith('@'):
            handle = path_parts[0]
            logging.info(f"Handle encontrado: {handle}")
            # Primero intentar con API si está disponible
            channel_id = obtener_id_desde_handle_api(handle)
            if channel_id:
                return channel_id
            # Fallback a scraping
            return obtener_id_desde_contenido_pagina(url)
        elif len(path_parts) >= 2 and path_parts[0] in ['c', 'user']:
            custom_name = path_parts[1]
            logging.info(f"Nombre personalizado encontrado: {custom_name}")
            return obtener_id_desde_contenido_pagina(url)
        elif len(path_parts) == 1:
            # Podría ser un nombre de usuario directo como youtube.com/nombreusuario
            logging.info(f"Posible nombre de usuario: {path_parts[0]}")
            return obtener_id_desde_contenido_pagina(url)
    
    # Si todo lo demás falla, intenta obtener el ID de la página
    logging.info("Intentando obtener ID del contenido de la página")
    return obtener_id_desde_contenido_pagina(url)

def es_channel_id_valido(channel_id):
    """Verifica si un string tiene el formato de un channel ID válido"""
    return bool(re.match(r'^UC[a-zA-Z0-9_-]{22}$', channel_id))

def obtener_id_desde_video(video_id):
    """Obtiene el channel ID desde un video ID usando la API de YouTube"""
    api_key = os.environ.get('YOUTUBE_API_KEY')
    
    if api_key:
        try:
            from googleapiclient.discovery import build
            youtube = build('youtube', 'v3', developerKey=api_key)
            
            request = youtube.videos().list(
                part='snippet',
                id=video_id
            )
            response = request.execute()
            
            if 'items' in response and len(response['items']) > 0:
                channel_id = response['items'][0]['snippet']['channelId']
                logging.info(f"Channel ID obtenido desde API para video {video_id}: {channel_id}")
                return channel_id
            else:
                logging.warning(f"No se encontró video con ID: {video_id}")
        except Exception as e:
            logging.error(f"Error usando YouTube API: {e}")
    
    # Fallback: obtener desde la página del video
    url = f'https://www.youtube.com/watch?v={video_id}'
    logging.info(f"Fallback: obteniendo desde página del video: {url}")
    return obtener_id_desde_contenido_pagina(url)

def obtener_id_desde_handle_api(handle):
    """Obtiene el channel ID desde un handle (@usuario) usando la API de YouTube"""
    api_key = os.environ.get('YOUTUBE_API_KEY')
    
    if not api_key:
        logging.warning("API Key no disponible para resolver handle")
        return None
    
    try:
        from googleapiclient.discovery import build
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # Buscar canal por handle/custom URL
        request = youtube.search().list(
            q=handle,
            type='channel',
            part='id',
            maxResults=1
        )
        response = request.execute()
        
        if 'items' in response and len(response['items']) > 0:
            channel_id = response['items'][0]['id']['channelId']
            logging.info(f"Channel ID obtenido desde API para handle {handle}: {channel_id}")
            return channel_id
        else:
            logging.warning(f"No se encontró canal con handle: {handle}")
            return None
            
    except Exception as e:
        logging.error(f"Error usando YouTube API para handle {handle}: {e}")
        return None

def obtener_id_desde_contenido_pagina(url):
    """Extrae el channel ID del HTML de la página"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        logging.info(f"Solicitando contenido de: {url}")
        respuesta = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        respuesta.raise_for_status()
        
        contenido = respuesta.text
        logging.debug(f"Contenido obtenido, longitud: {len(contenido)}")
        
        # Lista de patrones ordenados por probabilidad de éxito
        patrones = [
            # Patrón más común en el JSON de la página
            r'"channelId":"(UC[a-zA-Z0-9_-]{22})"',
            # En metadatos
            r'<meta property="og:url" content="https://www\.youtube\.com/channel/(UC[a-zA-Z0-9_-]{22})"',
            # En enlaces canónicos
            r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[a-zA-Z0-9_-]{22})"',
            # En browse endpoints
            r'"browseEndpoint":{"browseId":"(UC[a-zA-Z0-9_-]{22})"',
            # En datos estructurados
            r'"externalId":"(UC[a-zA-Z0-9_-]{22})"',
            # En URLs de suscripción
            r'channel/(UC[a-zA-Z0-9_-]{22})',
            # En configuración del cliente
            r'"CHANNEL_ID":"(UC[a-zA-Z0-9_-]{22})"',
            # En metadatos adicionales
            r'"channelMetadataRenderer":{"title":"[^"]*","description":"[^"]*","rssUrl":"[^"]*","externalId":"(UC[a-zA-Z0-9_-]{22})"',
        ]
        
        for i, patron in enumerate(patrones):
            try:
                coincidencias = re.findall(patron, contenido)
                if coincidencias:
                    # Tomar la primera coincidencia válida
                    for coincidencia in coincidencias:
                        channel_id = coincidencia if isinstance(coincidencia, str) else coincidencia[0]
                        if es_channel_id_valido(channel_id):
                            logging.info(f"Channel ID encontrado con patrón {i+1}: {channel_id}")
                            return channel_id
            except Exception as e:
                logging.warning(f"Error con patrón {i+1}: {e}")
                continue
        
        # Búsqueda adicional en JSON embebido
        try:
            # Buscar bloques de JSON en el HTML
            json_matches = re.findall(r'var ytInitialData = ({.*?});', contenido)
            for json_str in json_matches:
                try:
                    data = json.loads(json_str)
                    channel_id = extraer_channel_id_de_json(data)
                    if channel_id:
                        logging.info(f"Channel ID encontrado en ytInitialData: {channel_id}")
                        return channel_id
                except:
                    continue
        except Exception as e:
            logging.warning(f"Error procesando JSON embebido: {e}")
        
        logging.warning("No se encontró el ID del canal en el contenido de la página")
        return None
        
    except requests.RequestException as e:
        logging.error(f"Error de red al obtener el contenido: {e}")
        return None
    except Exception as e:
        logging.error(f"Error inesperado procesando página: {e}")
        return None

def extraer_channel_id_de_json(data, visited=None):
    """Extrae recursivamente el channel ID de estructuras JSON complejas"""
    if visited is None:
        visited = set()
    
    # Evitar bucles infinitos
    if id(data) in visited:
        return None
    visited.add(id(data))
    
    try:
        if isinstance(data, dict):
            # Buscar directamente channelId
            if 'channelId' in data:
                channel_id = data['channelId']
                if isinstance(channel_id, str) and es_channel_id_valido(channel_id):
                    return channel_id
            
            # Buscar en browseId
            if 'browseId' in data:
                browse_id = data['browseId']
                if isinstance(browse_id, str) and es_channel_id_valido(browse_id):
                    return browse_id
            
            # Buscar recursivamente en todos los valores
            for value in data.values():
                result = extraer_channel_id_de_json(value, visited)
                if result:
                    return result
                    
        elif isinstance(data, list):
            for item in data:
                result = extraer_channel_id_de_json(item, visited)
                if result:
                    return result
    except:
        pass
    
    return None