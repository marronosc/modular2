import requests
import json
import logging
from urllib.parse import quote
from datetime import datetime

def search_keyword_suggestions(keyword, max_retries=3):
    """
    Busca sugerencias de palabras clave usando la YouTube Suggest API
    
    Args:
        keyword (str): Palabra clave base para buscar sugerencias
        max_retries (int): Número máximo de reintentos en caso de fallo
    
    Returns:
        dict: Información sobre las sugerencias encontradas
    """
    try:
        if not keyword or not keyword.strip():
            raise Exception("La palabra clave no puede estar vacía")
        
        keyword = keyword.strip()
        logging.info(f"Buscando sugerencias para: {keyword}")
        
        # URL de la YouTube Suggest API (no oficial) - usando parámetros más simples
        base_url = "https://suggestqueries.google.com/complete/search"
        
        params = {
            'client': 'youtube',
            'ds': 'yt', 
            'q': keyword
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        }
        
        for attempt in range(max_retries):
            try:
                logging.info(f"Intento {attempt + 1} de búsqueda para: {keyword}")
                
                response = requests.get(base_url, params=params, headers=headers, timeout=15)
                response.raise_for_status()
                
                logging.info(f"Respuesta recibida. Status: {response.status_code}")
                logging.info(f"Primeros 200 caracteres de respuesta: {response.text[:200]}")
                
                # Procesar la respuesta
                content = response.text.strip()
                
                if not content:
                    logging.warning("Respuesta vacía del servidor")
                    if attempt == max_retries - 1:
                        return create_empty_result(keyword, "Respuesta vacía del servidor")
                    continue
                
                # Intentar parsear como JSON directo primero
                suggestions = []
                try:
                    data = json.loads(content)
                    suggestions = extract_suggestions_from_json(data, keyword)
                    logging.info(f"Parseado JSON directo exitoso, {len(suggestions)} sugerencias")
                except json.JSONDecodeError:
                    # Si falla, intentar limpiar respuesta JSONP
                    logging.info("JSON directo falló, intentando limpiar JSONP")
                    try:
                        # Buscar el inicio del array JSON
                        start_idx = content.find('[')
                        if start_idx == -1:
                            logging.warning("No se encontró inicio de array JSON")
                            if attempt == max_retries - 1:
                                return create_empty_result(keyword, "Formato de respuesta inválido")
                            continue
                        
                        # Buscar el final del array JSON
                        bracket_count = 0
                        end_idx = start_idx
                        for i, char in enumerate(content[start_idx:], start_idx):
                            if char == '[':
                                bracket_count += 1
                            elif char == ']':
                                bracket_count -= 1
                                if bracket_count == 0:
                                    end_idx = i + 1
                                    break
                        
                        if bracket_count != 0:
                            logging.warning("Array JSON malformado")
                            if attempt == max_retries - 1:
                                return create_empty_result(keyword, "Array JSON malformado")
                            continue
                        
                        json_content = content[start_idx:end_idx]
                        logging.info(f"JSON extraído: {json_content[:100]}...")
                        
                        data = json.loads(json_content)
                        suggestions = extract_suggestions_from_json(data, keyword)
                        logging.info(f"Parseado JSONP exitoso, {len(suggestions)} sugerencias")
                        
                    except Exception as parse_error:
                        logging.error(f"Error parseando respuesta: {str(parse_error)}")
                        if attempt == max_retries - 1:
                            return create_empty_result(keyword, f"Error parseando respuesta: {str(parse_error)}")
                        continue
                
                # Crear resultado exitoso
                logging.info(f"Búsqueda completada exitosamente: {len(suggestions)} sugerencias únicas")
                
                return {
                    'keyword': keyword,
                    'suggestions': suggestions,
                    'total_suggestions': len(suggestions),
                    'search_date': datetime.now(),
                    'has_suggestions': len(suggestions) > 0,
                    'status': 'success'
                }
                
            except requests.RequestException as e:
                logging.warning(f"Error de red en intento {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    return create_empty_result(keyword, f"Error de conexión: {str(e)}")
                continue
                
            except Exception as e:
                logging.error(f"Error inesperado en intento {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    return create_empty_result(keyword, f"Error inesperado: {str(e)}")
                continue
        
        # Si llegamos aquí, todos los intentos fallaron
        return create_empty_result(keyword, "Todos los intentos de búsqueda fallaron")
        
    except Exception as e:
        logging.error(f"Error crítico en search_keyword_suggestions: {str(e)}")
        return create_empty_result(keyword, f"Error crítico: {str(e)}")

def extract_suggestions_from_json(data, original_keyword):
    """
    Extrae sugerencias de la estructura JSON de respuesta
    """
    suggestions = []
    
    try:
        # La estructura típica es: [query, [suggestions], ...]
        if isinstance(data, list) and len(data) >= 2:
            suggestions_array = data[1]
            
            if isinstance(suggestions_array, list):
                for item in suggestions_array:
                    suggestion_text = None
                    
                    # Puede ser un string directo o un array con el string
                    if isinstance(item, str):
                        suggestion_text = item.strip()
                    elif isinstance(item, list) and len(item) > 0:
                        suggestion_text = str(item[0]).strip()
                    
                    # Validar y agregar sugerencia
                    if (suggestion_text and 
                        suggestion_text.lower() != original_keyword.lower() and
                        len(suggestion_text) > 1 and
                        len(suggestion_text) <= 200):
                        suggestions.append(suggestion_text)
        
        # Remover duplicados manteniendo orden
        unique_suggestions = []
        seen = set()
        for suggestion in suggestions:
            suggestion_lower = suggestion.lower()
            if suggestion_lower not in seen:
                seen.add(suggestion_lower)
                unique_suggestions.append(suggestion)
        
        return unique_suggestions[:50]  # Limitar a 50 sugerencias máximo
        
    except Exception as e:
        logging.error(f"Error extrayendo sugerencias: {str(e)}")
        return []

def create_empty_result(keyword, error_message="No se encontraron sugerencias"):
    """
    Crea un resultado vacío en caso de error o sin sugerencias
    """
    logging.info(f"Creando resultado vacío para '{keyword}': {error_message}")
    return {
        'keyword': keyword,
        'suggestions': [],
        'total_suggestions': 0,
        'search_date': datetime.now(),
        'has_suggestions': False,
        'status': 'no_results',
        'error_message': error_message
    }

def format_suggestions_for_export(suggestions, keyword):
    """
    Formatea las sugerencias para exportación
    
    Args:
        suggestions (list): Lista de sugerencias
        keyword (str): Palabra clave original
    
    Returns:
        dict: Datos formateados para diferentes tipos de exportación
    """
    try:
        # Formato texto plano
        text_format = f"Sugerencias de YouTube para: {keyword}\n"
        text_format += f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
        text_format += f"Total de sugerencias: {len(suggestions)}\n\n"
        
        for i, suggestion in enumerate(suggestions, 1):
            text_format += f"{i}. {suggestion}\n"
        
        # Formato CSV
        csv_format = "Número,Sugerencia\n"
        for i, suggestion in enumerate(suggestions, 1):
            # Escapar comillas en CSV
            escaped_suggestion = suggestion.replace('"', '""')
            csv_format += f'{i},"{escaped_suggestion}"\n'
        
        # Formato JSON
        json_format = {
            'keyword': keyword,
            'generated_date': datetime.now().isoformat(),
            'total_suggestions': len(suggestions),
            'suggestions': [
                {
                    'position': i,
                    'text': suggestion
                }
                for i, suggestion in enumerate(suggestions, 1)
            ]
        }
        
        return {
            'text': text_format,
            'csv': csv_format,
            'json': json.dumps(json_format, indent=2, ensure_ascii=False)
        }
        
    except Exception as e:
        logging.error(f"Error formateando sugerencias para exportación: {str(e)}")
        return {
            'text': f"Error formateando datos: {str(e)}",
            'csv': f"Error,{str(e)}",
            'json': json.dumps({'error': str(e)})
        }