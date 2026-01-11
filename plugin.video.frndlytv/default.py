"""
Frndly TV for Kodi - Main Entry Point
Watch Frndly TV channels directly in Kodi with full EPG support

Developed by Marcus Montgomery and BeatTLF Entertainment
Based on frndlytv-for-channels by Matt Huisman
"""

import sys
import os
import time
import datetime
from urllib.parse import parse_qsl, urlencode

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs

# Addon info
ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
ADDON_DATA = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
ADDON_ICON = os.path.join(ADDON_PATH, 'resources', 'icon.png')
ADDON_FANART = os.path.join(ADDON_PATH, 'resources', 'fanart.jpg')

# Ensure addon data directory exists
if not os.path.exists(ADDON_DATA):
    os.makedirs(ADDON_DATA)

# Add lib to path
sys.path.insert(0, os.path.join(ADDON_PATH, 'resources', 'lib'))

from frndly_api import FrndlyTV, FrndlyException, Program

# Plugin handle
HANDLE = int(sys.argv[1]) if len(sys.argv) > 1 else -1
BASE_URL = sys.argv[0] if len(sys.argv) > 0 else ''


def log(message, level=xbmc.LOGDEBUG):
    xbmc.log('[{}] {}'.format(ADDON_ID, message), level)


def notify(message, heading=None, icon=xbmcgui.NOTIFICATION_INFO, time=5000):
    heading = heading or ADDON_NAME
    xbmcgui.Dialog().notification(heading, message, icon, time)


def get_setting(key):
    return ADDON.getSetting(key)


def set_setting(key, value):
    ADDON.setSetting(key, str(value))


def build_url(action, **kwargs):
    query = {'action': action}
    query.update(kwargs)
    return '{}?{}'.format(BASE_URL, urlencode(query))


def get_api():
    username = get_setting('username')
    password = get_setting('password')
    
    if not username or not password:
        return None
    
    api = FrndlyTV(username, password, ADDON_DATA)
    return api


def ensure_login(api):
    if not api:
        notify('Please configure your Frndly TV credentials in settings', 
               'Login Required', xbmcgui.NOTIFICATION_WARNING)
        ADDON.openSettings()
        return False
    
    if not api.is_logged_in():
        dialog = xbmcgui.DialogProgress()
        dialog.create(ADDON_NAME, 'Logging in...')
        
        try:
            api.login()
            dialog.close()
            notify('Login Successful')
            return True
        except FrndlyException as e:
            dialog.close()
            notify(str(e), 'Login Failed', xbmcgui.NOTIFICATION_ERROR)
            return False
    
    return True


def format_time(timestamp):
    try:
        dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.strftime('%I:%M %p').lstrip('0')
    except:
        return ''


def format_duration(seconds):
    try:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        if hours > 0:
            return '{}h {}m'.format(hours, minutes)
        return '{}m'.format(minutes)
    except:
        return ''


def main_menu():
    items = [
        ('Live Channels', 'channels', 'DefaultTVShows.png'),
        ('TV Guide', 'guide', 'DefaultTVGuide.png'),
        ('DVR Recordings', 'dvr', 'DefaultVideo.png'),
        ('Server Status', 'server_status', 'DefaultNetwork.png'),
        ('Settings', 'settings', 'DefaultAddonProgram.png'),
    ]
    
    for title, action, icon in items:
        li = xbmcgui.ListItem(title)
        li.setArt({'icon': icon, 'thumb': icon, 'fanart': ADDON_FANART})
        
        url = build_url(action)
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    
    xbmcplugin.setContent(HANDLE, 'files')
    xbmcplugin.endOfDirectory(HANDLE)


def list_channels():
    api = get_api()
    if not ensure_login(api):
        return
    
    dialog = xbmcgui.DialogProgress()
    dialog.create(ADDON_NAME, 'Loading channels...')
    
    try:
        channels = api.channels()
        live_map = api.live_map()
        
        # Get current programs
        channel_ids = [str(ch['id']) for ch in channels]
        current_progs, next_progs = api.get_current_programs(channel_ids)
    except FrndlyException as e:
        dialog.close()
        notify(str(e), 'Error', xbmcgui.NOTIFICATION_ERROR)
        return
    
    dialog.close()
    
    if not channels:
        notify('No channels available. Check your subscription.', 'No Channels', xbmcgui.NOTIFICATION_WARNING)
        return
    
    for channel in channels:
        channel_id = str(channel['id'])
        name = channel['display']['title']
        
        # Get logo
        logo = ''
        img_url = channel['display'].get('imageUrl', '')
        if img_url:
            logo = api.logo_url(img_url)
        
        # Get slug for playback
        data = live_map.get(channel_id, {})
        slug = channel_id
        if 'slug' in data:
            slug = '{}-{}'.format(data['slug'], channel_id)
        
        # Channel number
        chno = data.get('chno', '')
        if chno:
            title = '{}. {}'.format(chno, name)
        else:
            title = name
        
        # Current program info
        current_prog = current_progs.get(channel_id)
        next_prog = next_progs.get(channel_id)
        
        if current_prog:
            now_playing = current_prog.title
            if current_prog.episode_title and current_prog.episode_title != current_prog.title:
                now_playing = '{}: {}'.format(current_prog.title, current_prog.episode_title)
            title = '{} - {}'.format(title, now_playing)
        
        li = xbmcgui.ListItem(title)
        
        # Set art
        art = {'icon': logo, 'thumb': logo, 'fanart': ADDON_FANART}
        if current_prog:
            if current_prog.fanart:
                art['fanart'] = current_prog.fanart
            if current_prog.poster:
                art['poster'] = current_prog.poster
            if current_prog.thumbnail:
                art['landscape'] = current_prog.thumbnail
        li.setArt(art)
        
        # Build info
        info = {'title': title, 'mediatype': 'video'}
        
        if current_prog:
            plot_lines = []
            
            # Now playing
            time_str = format_time(current_prog.start_time)
            end_str = format_time(current_prog.end_time)
            plot_lines.append('[B]NOW PLAYING ({} - {})[/B]'.format(time_str, end_str))
            plot_lines.append('[B]{}[/B]'.format(current_prog.title))
            
            # Episode info
            if current_prog.season and current_prog.episode:
                plot_lines.append('Season {}, Episode {}'.format(current_prog.season, current_prog.episode))
            if current_prog.episode_title and current_prog.episode_title != current_prog.title:
                plot_lines.append('"{}"'.format(current_prog.episode_title))
            
            # Rating
            if current_prog.rating:
                plot_lines.append('Rating: {}'.format(current_prog.rating))
                info['mpaa'] = current_prog.rating
            
            # Year
            if current_prog.year:
                plot_lines.append('Year: {}'.format(current_prog.year))
                info['year'] = current_prog.year
            
            # Genre
            if current_prog.genres:
                genre_str = ', '.join(current_prog.genres) if isinstance(current_prog.genres, list) else current_prog.genres
                plot_lines.append('Genre: {}'.format(genre_str))
            
            # Duration
            duration_str = format_duration(current_prog.duration)
            remaining = current_prog.get_time_remaining()
            if duration_str:
                plot_lines.append('Duration: {} ({}m remaining)'.format(duration_str, remaining))
            
            # Description
            if current_prog.description:
                plot_lines.append('')
                plot_lines.append(current_prog.description)
            
            # Special markers
            markers = []
            if current_prog.is_new:
                markers.append('[NEW]')
            if current_prog.is_live:
                markers.append('[LIVE]')
            if current_prog.is_premiere:
                markers.append('[PREMIERE]')
            if current_prog.is_finale:
                markers.append('[FINALE]')
            if markers:
                plot_lines.insert(0, ' '.join(markers))
            
            # Next up
            if next_prog:
                plot_lines.append('')
                next_time = format_time(next_prog.start_time)
                plot_lines.append('[B]NEXT ({}):[/B] {}'.format(next_time, next_prog.title))
            
            info['plot'] = '\n'.join(plot_lines)
            
            if current_prog.season:
                info['season'] = current_prog.season
            if current_prog.episode:
                info['episode'] = current_prog.episode
            if current_prog.duration:
                info['duration'] = current_prog.duration
        
        li.setInfo('video', info)
        li.setProperty('IsPlayable', 'true')
        
        # Context menu
        context_items = [
            ('Channel Info', 'Action(Info)'),
        ]
        li.addContextMenuItems(context_items)
        
        url = build_url('play', slug=slug)
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    
    xbmcplugin.setContent(HANDLE, 'tvshows')
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.endOfDirectory(HANDLE)


def show_guide():
    list_channels()


def show_dvr():
    li = xbmcgui.ListItem('[B]DVR Recording Information[/B]')
    li.setInfo('video', {
        'plot': 'DVR Recording requires Kodi PVR backend integration.\n\n'
                'For full DVR functionality:\n'
                '1. Enable the built-in web server in addon settings\n'
                '2. Configure an IPTV PVR client (like PVR IPTV Simple Client)\n'
                '3. Point it to the addon playlist and EPG URLs\n'
                '4. Use Kodi native PVR recording features\n\n'
                'The built-in server provides:\n'
                '- M3U Playlist: http://YOUR_IP:8183/playlist.m3u8\n'
                '- EPG/XMLTV: http://YOUR_IP:8183/epg.xml'
    })
    li.setArt({'icon': 'DefaultAddonInfo.png', 'fanart': ADDON_FANART})
    xbmcplugin.addDirectoryItem(HANDLE, '', li, isFolder=False)
    
    xbmcplugin.endOfDirectory(HANDLE)


def play_channel(slug):
    api = get_api()
    if not ensure_login(api):
        return
    
    log('Playing channel: {}'.format(slug))
    
    try:
        stream_url = api.play(slug)
    except FrndlyException as e:
        notify(str(e), 'Stream Error', xbmcgui.NOTIFICATION_ERROR)
        return
    
    log('Stream URL obtained')
    
    li = xbmcgui.ListItem(path=stream_url)
    li.setProperty('IsPlayable', 'true')
    
    use_inputstream = get_setting('use_inputstream') == 'true'
    
    if use_inputstream and '.m3u8' in stream_url:
        try:
            if xbmc.getCondVisibility('System.HasAddon(inputstream.adaptive)'):
                li.setProperty('inputstream', 'inputstream.adaptive')
                li.setProperty('inputstream.adaptive.manifest_type', 'hls')
                log('Using inputstream.adaptive for playback')
        except:
            pass
    
    li.setMimeType('application/x-mpegURL')
    li.setContentLookup(False)
    
    xbmcplugin.setResolvedUrl(HANDLE, True, li)


def show_server_status():
    from webserver import is_running
    
    enable_server = get_setting('enable_server') == 'true'
    port = get_setting('server_port') or '8183'
    
    # Get local IP
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = '127.0.0.1'
    
    if not enable_server:
        text = '[B]Built-in Web Server: DISABLED[/B]\n\n'
        text += 'Enable it in Settings to use Frndly TV with external IPTV clients like:\n'
        text += '- TiviMate\n'
        text += '- Channels DVR\n'
        text += '- Perfect Player\n'
        text += '- Any M3U compatible player\n\n'
        text += 'The server provides:\n'
        text += '- M3U Playlist for channel list\n'
        text += '- XMLTV EPG with full program info\n'
        text += '- Direct stream access'
    elif is_running():
        text = '[B]Built-in Web Server: RUNNING[/B]\n\n'
        text += 'Server Address: {}:{}\n\n'.format(local_ip, port)
        text += '[B]URLs for IPTV Clients:[/B]\n\n'
        text += 'Status Page:\nhttp://{}:{}/\n\n'.format(local_ip, port)
        text += 'Playlist (with Gracenote EPG):\nhttp://{}:{}/playlist.m3u8?gracenote=include\n\n'.format(local_ip, port)
        text += 'Playlist (with built-in EPG):\nhttp://{}:{}/playlist.m3u8?gracenote=exclude\n\n'.format(local_ip, port)
        text += 'EPG/XMLTV:\nhttp://{}:{}/epg.xml\n\n'.format(local_ip, port)
        text += '[B]For Channels DVR:[/B]\n'
        text += 'Stream Format: HLS\n'
        text += 'Source: http://{}:{}/playlist.m3u8?gracenote=include'.format(local_ip, port)
    else:
        text = '[B]Built-in Web Server: NOT RUNNING[/B]\n\n'
        text += 'Server is enabled but not currently running.\n'
        text += 'Please restart the addon or Kodi.'
    
    xbmcgui.Dialog().textviewer('Frndly TV Server Status', text)


def open_settings():
    ADDON.openSettings()


def router():
    params = dict(parse_qsl(sys.argv[2][1:])) if len(sys.argv) > 2 else {}
    action = params.get('action', '')
    
    log('Router: action={}, params={}'.format(action, params), xbmc.LOGDEBUG)
    
    if not action:
        main_menu()
    elif action == 'channels':
        list_channels()
    elif action == 'guide':
        show_guide()
    elif action == 'dvr':
        show_dvr()
    elif action == 'play':
        play_channel(params.get('slug', ''))
    elif action == 'server_status':
        show_server_status()
    elif action == 'settings':
        open_settings()
    elif action == 'refresh':
        xbmc.executebuiltin('Container.Refresh')
    elif action in ('dvr_scheduled', 'dvr_rules', 'dvr_settings', 'record'):
        notify('DVR feature requires PVR backend setup. See DVR menu for details.', 'DVR Info')
    else:
        log('Unknown action: {}'.format(action), xbmc.LOGWARNING)
        main_menu()


if __name__ == '__main__':
    router()
