from config.tools import TOOLS_CONFIG, ICONS, get_active_tools, get_coming_soon_tools

def inject_tools():
    return {
        'tools_config': TOOLS_CONFIG,
        'icons': ICONS,
        'active_tools': get_active_tools(),
        'coming_soon_tools': get_coming_soon_tools()
    }
