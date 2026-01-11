"""
PVR/DVR Helper for Frndly TV Kodi Addon
Helps integrate with Kodi's PVR system for recording capabilities

Developed by Marcus Montgomery and BeatTLF Entertainment
"""

import os
import json

try:
    import xbmc
    import xbmcaddon
    import xbmcgui
    import xbmcvfs
except ImportError:
    # For testing outside Kodi
    pass


def get_pvr_addon():
    """Check if IPTV Simple Client is installed and get its addon object"""
    try:
        addon = xbmcaddon.Addon('pvr.iptvsimple')
        return addon
    except:
        return None


def is_pvr_enabled():
    """Check if PVR is enabled in Kodi"""
    try:
        return xbmc.getCondVisibility('Pvr.HasTVChannels') or xbmc.getCondVisibility('System.HasAddon(pvr.iptvsimple)')
    except:
        return False


def configure_pvr_simple(playlist_url, epg_url):
    """
    Configure IPTV Simple Client with Frndly TV URLs
    Returns True if successful, False otherwise
    """
    pvr_addon = get_pvr_addon()
    
    if not pvr_addon:
        return False, "IPTV Simple Client is not installed. Please install it from the Kodi addon repository."
    
    try:
        # Set M3U playlist
        pvr_addon.setSetting('m3uPathType', '1')  # Remote path
        pvr_addon.setSetting('m3uUrl', playlist_url)
        
        # Set EPG
        pvr_addon.setSetting('epgPathType', '1')  # Remote path
        pvr_addon.setSetting('epgUrl', epg_url)
        
        # Enable logos from M3U
        pvr_addon.setSetting('logoFromEpg', '1')
        pvr_addon.setSetting('logoPathType', '1')
        
        # Cache settings
        pvr_addon.setSetting('m3uCache', 'true')
        pvr_addon.setSetting('epgCache', 'true')
        
        return True, "IPTV Simple Client configured successfully! Please restart Kodi for changes to take effect."
    except Exception as e:
        return False, f"Failed to configure IPTV Simple Client: {str(e)}"


def generate_pvr_config_instructions(server_ip, server_port):
    """Generate instructions for manual PVR setup"""
    instructions = f"""
[B]PVR/DVR Setup Instructions[/B]

To enable DVR recording with Frndly TV, follow these steps:

[B]Step 1: Install IPTV Simple Client[/B]
1. Go to Add-ons > Install from repository
2. Select "Kodi Add-on repository"
3. Select "PVR clients"
4. Install "PVR IPTV Simple Client"

[B]Step 2: Configure IPTV Simple Client[/B]
1. Go to Add-ons > My add-ons > PVR clients
2. Select "PVR IPTV Simple Client"
3. Click "Configure"

[B]Step 3: Set M3U Playlist[/B]
- Location: Remote Path (Internet address)
- M3U Playlist URL:
  http://{server_ip}:{server_port}/playlist.m3u8

[B]Step 4: Set EPG Source[/B]
- XMLTV URL:
  http://{server_ip}:{server_port}/epg.xml
- EPG Time Shift: 0

[B]Step 5: Enable PVR[/B]
1. Go to Settings > PVR & Live TV
2. Enable "PVR Manager"
3. Restart Kodi

[B]Step 6: Access Live TV[/B]
- Go to TV in main menu
- Your Frndly TV channels will appear
- Use Guide for EPG view
- Set up recordings from Guide

[B]DVR Recording Notes:[/B]
- Recording requires backend support (like TVHeadend or similar)
- Basic PVR features work with IPTV Simple Client alone
- For full DVR, consider Channels DVR or similar
- The built-in web server enables easy integration

[B]Frndly TV URLs:[/B]
Playlist: http://{server_ip}:{server_port}/playlist.m3u8
EPG: http://{server_ip}:{server_port}/epg.xml
"""
    return instructions


def show_pvr_setup_dialog():
    """Show PVR setup dialog"""
    try:
        import xbmcaddon
        addon = xbmcaddon.Addon()
        enable_server = addon.getSetting('enable_server') == 'true'
        port = addon.getSetting('server_port') or '8183'
        
        if not enable_server:
            xbmcgui.Dialog().ok(
                'PVR Setup',
                'Please enable the built-in web server first.\n\n'
                'Go to Settings > Web Server > Enable Built-in Web Server'
            )
            return
        
        # Get local IP
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
            s.close()
        except:
            local_ip = '127.0.0.1'
        
        instructions = generate_pvr_config_instructions(local_ip, port)
        xbmcgui.Dialog().textviewer('PVR/DVR Setup Guide', instructions)
        
    except Exception as e:
        xbmcgui.Dialog().ok('Error', f'Failed to show PVR setup: {str(e)}')


def auto_configure_pvr():
    """Attempt to automatically configure PVR Simple Client"""
    try:
        import xbmcaddon
        addon = xbmcaddon.Addon()
        enable_server = addon.getSetting('enable_server') == 'true'
        port = addon.getSetting('server_port') or '8183'
        
        if not enable_server:
            return False, "Web server is not enabled"
        
        # Get local IP
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
            s.close()
        except:
            local_ip = '127.0.0.1'
        
        playlist_url = f'http://{local_ip}:{port}/playlist.m3u8'
        epg_url = f'http://{local_ip}:{port}/epg.xml'
        
        return configure_pvr_simple(playlist_url, epg_url)
        
    except Exception as e:
        return False, str(e)
