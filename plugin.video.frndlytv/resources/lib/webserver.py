"""
Built-in Web Server for Frndly TV Kodi Addon
Provides M3U playlist and enhanced XMLTV EPG for external IPTV clients

Developed by Marcus Montgomery and BeatTLF Entertainment
Based on frndlytv-for-channels by Matt Huisman
"""

import os
import time
import datetime
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qsl
from xml.sax.saxutils import escape

# Use absolute imports instead of relative
from frndly_api import get_api, FrndlyException, Program

# Server instance
_server = None
_server_thread = None


class FrndlyRequestHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler for Frndly TV"""
    
    api = None
    
    def log_message(self, format, *args):
        """Override to use Kodi logging"""
        try:
            import xbmc
            xbmc.log(f"[FrndlyTV Server] {format % args}", xbmc.LOGDEBUG)
        except:
            pass
    
    def _send_error(self, code, message):
        """Send error response"""
        self.send_response(code)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(f'Error: {message}'.encode('utf-8'))
    
    def _get_params(self):
        """Parse query parameters"""
        parsed = urlparse(self.path)
        return dict(parse_qsl(parsed.query, keep_blank_values=True))
    
    def do_GET(self):
        """Handle GET requests"""
        parsed = urlparse(self.path)
        path = parsed.path.strip('/')
        
        routes = {
            '': self._handle_status,
            'status': self._handle_status,
            'playlist.m3u8': self._handle_playlist,
            'playlist.m3u': self._handle_playlist,
            'epg.xml': self._handle_epg,
            'keep_alive': self._handle_keep_alive,
        }
        
        if path.startswith('play/'):
            self._handle_play()
            return
        
        handler = routes.get(path)
        if handler:
            try:
                handler()
            except Exception as e:
                self._send_error(500, str(e))
        else:
            self._send_error(404, 'Not Found')
    
    def _handle_status(self):
        """Display server status page"""
        host = self.headers.get('Host', 'localhost:8183')
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        
        html = f'''<!DOCTYPE html>
<html>
<head>
    <title>Frndly TV for Kodi</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {{ box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            max-width: 900px; 
            margin: 0 auto; 
            padding: 20px; 
            background: linear-gradient(135deg, #1DB954 0%, #191414 100%);
            min-height: 100vh;
            color: #fff;
        }}
        .header {{ text-align: center; padding: 30px 0; }}
        .header h1 {{ font-size: 2.5em; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
        .header p {{ opacity: 0.9; font-size: 1.1em; }}
        .card {{
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            margin: 20px 0;
            border: 1px solid rgba(255,255,255,0.2);
        }}
        .card h2 {{ margin-top: 0; color: #1DB954; border-bottom: 2px solid #1DB954; padding-bottom: 10px; }}
        .url-box {{
            background: rgba(0,0,0,0.3);
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
            word-break: break-all;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.9em;
        }}
        a {{ color: #1DB954; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .label {{ font-weight: 600; color: #fff; display: block; margin-bottom: 5px; }}
        .param {{ background: rgba(29, 185, 84, 0.2); padding: 8px 12px; border-radius: 5px; margin: 5px 0; }}
        code {{ background: rgba(0,0,0,0.3); padding: 2px 8px; border-radius: 4px; }}
        .credits {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid rgba(255,255,255,0.2);
            opacity: 0.8;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Frndly TV for Kodi</h1>
        <p>Your live TV streams are ready for IPTV clients!</p>
    </div>
    
    <div class="card">
        <h2>IPTV Source 1 (Gracenote EPG)</h2>
        <span class="label">Playlist URL:</span>
        <div class="url-box">
            <a href="http://{host}/playlist.m3u8?gracenote=include">http://{host}/playlist.m3u8?gracenote=include</a>
        </div>
        <span class="label">EPG URL:</span>
        <div class="url-box">(Leave Blank - uses Gracenote guide data)</div>
    </div>
    
    <div class="card">
        <h2>IPTV Source 2 (Full EPG with Metadata)</h2>
        <span class="label">Playlist URL:</span>
        <div class="url-box">
            <a href="http://{host}/playlist.m3u8?gracenote=exclude">http://{host}/playlist.m3u8?gracenote=exclude</a>
        </div>
        <span class="label">EPG URL:</span>
        <div class="url-box">
            <a href="http://{host}/epg.xml?gracenote=exclude">http://{host}/epg.xml?gracenote=exclude</a>
        </div>
        <p style="opacity:0.8;font-size:0.9em;">
            Includes: Ratings (TV-PG, TV-14, etc.), episode info, descriptions, thumbnails
        </p>
    </div>
    
    <div class="card">
        <h2>Playlist Parameters</h2>
        <div class="param"><code>start_chno=N</code> - Start channel numbering from N</div>
        <div class="param"><code>include=id1,id2</code> - Only include specific channels</div>
        <div class="param"><code>exclude=id1,id2</code> - Exclude specific channels</div>
        <div class="param"><code>gracenote=include|exclude</code> - Filter by Gracenote availability</div>
        <div class="param"><code>days=N</code> - EPG days to include (1-7, default: 3)</div>
    </div>
    
    <div class="card">
        <h2>Compatible Apps</h2>
        <ul>
            <li>Channels DVR</li>
            <li>TiviMate</li>
            <li>IPTV Smarters</li>
            <li>Perfect Player</li>
            <li>Kodi PVR IPTV Simple Client</li>
            <li>VLC Media Player</li>
        </ul>
    </div>
    
    <div class="credits">
        <p><strong>Frndly TV for Kodi v1.0.0</strong></p>
        <p>Developed by Marcus Montgomery / BeatTLF Entertainment</p>
        <p>Based on frndlytv-for-channels by Matt Huisman</p>
    </div>
</body>
</html>'''
        
        self.wfile.write(html.encode('utf-8'))
    
    def _handle_playlist(self):
        """Generate M3U playlist"""
        if not self.api:
            self._send_error(500, 'API not initialized')
            return
        
        params = self._get_params()
        host = self.headers.get('Host', 'localhost:8183')
        
        try:
            channels = self.api.channels()
            live_map = self.api.live_map()
        except FrndlyException as e:
            self._send_error(500, str(e))
            return
        
        start_chno = int(params.get('start_chno', 0)) if params.get('start_chno') else None
        include = [x.lower().strip() for x in params.get('include', '').split(',') if x.strip()]
        exclude = [x.lower().strip() for x in params.get('exclude', '').split(',') if x.strip()]
        gracenote = params.get('gracenote', '').lower().strip()
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/x-mpegURL; charset=utf-8')
        self.send_header('Content-Disposition', 'attachment; filename="frndlytv.m3u8"')
        self.end_headers()
        
        epg_url = f"http://{host}/epg.xml"
        if gracenote:
            epg_url += f'?gracenote={gracenote}'
        
        self.wfile.write(f'#EXTM3U x-tvg-url="{epg_url}"\n'.encode('utf-8'))
        
        for channel in channels:
            channel_id_num = str(channel['id'])
            channel_id = f'frndly-{channel_id_num}'
            data = live_map.get(channel_id_num, {})
            
            slug = channel_id_num
            if 'slug' in data:
                slug = f"{data['slug']}-{channel_id_num}"
            
            url = f'http://{host}/play/{slug}.m3u8'
            name = channel['display']['title']
            logo = self.api.logo_url(channel['display'].get('imageUrl', ''))
            gracenote_id = data.get('gracenote')
            chno = data.get('chno', '')
            
            if (include and channel_id.lower() not in include) or (exclude and channel_id.lower() in exclude):
                continue
            
            if (gracenote == 'include' and not gracenote_id) or (gracenote == 'exclude' and gracenote_id):
                continue
            
            attrs = [f'channel-id="{channel_id}"', f'tvg-id="{channel_id}"']
            if logo:
                attrs.append(f'tvg-logo="{logo}"')
            if gracenote_id:
                attrs.append(f'tvc-guide-stationid="{gracenote_id}"')
            
            if start_chno is not None and start_chno > 0:
                attrs.append(f'tvg-chno="{start_chno}"')
                start_chno += 1
            elif chno:
                attrs.append(f'tvg-chno="{chno}"')
            
            attrs.append(f'tvg-name="{name}"')
            attrs.append('radio="false"')
            
            line = f'#EXTINF:-1 {" ".join(attrs)},{name}\n{url}\n'
            self.wfile.write(line.encode('utf-8'))
    
    def _handle_epg(self):
        """Generate enhanced XMLTV EPG with full metadata"""
        if not self.api:
            self._send_error(500, 'API not initialized')
            return
        
        params = self._get_params()
        
        try:
            days = min(max(int(params.get('days', 3)), 1), 7)
        except:
            days = 3
        
        gracenote = params.get('gracenote', '').lower().strip()
        
        try:
            channels = self.api.channels()
            live_map = self.api.live_map()
        except FrndlyException as e:
            self._send_error(500, str(e))
            return
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/xml; charset=utf-8')
        self.send_header('Content-Disposition', 'attachment; filename="frndlytv-epg.xml"')
        self.end_headers()
        
        self.wfile.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        self.wfile.write(b'<!DOCTYPE tv SYSTEM "xmltv.dtd">\n')
        self.wfile.write(b'<tv source-info-name="Frndly TV" generator-info-name="FrndlyTV-Kodi">\n')
        
        channel_ids = []
        for channel in channels:
            channel_id_num = str(channel['id'])
            channel_id = f'frndly-{channel_id_num}'
            data = live_map.get(channel_id_num, {})
            gracenote_id = data.get('gracenote')
            name = escape(channel['display']['title'])
            logo = self.api.logo_url(channel['display'].get('imageUrl', ''))
            chno = data.get('chno', '')
            
            if (gracenote == 'include' and not gracenote_id) or (gracenote == 'exclude' and gracenote_id):
                continue
            
            channel_ids.append(channel_id_num)
            
            ch_xml = f'  <channel id="{channel_id}">\n'
            ch_xml += f'    <display-name>{name}</display-name>\n'
            if chno:
                ch_xml += f'    <display-name>{chno}</display-name>\n'
            if logo:
                ch_xml += f'    <icon src="{escape(logo)}"/>\n'
            ch_xml += '  </channel>\n'
            
            self.wfile.write(ch_xml.encode('utf-8'))
        
        if channel_ids:
            try:
                guide_data = self.api.guide(channel_ids, start=int(time.time()), days=days)
                
                for channel_id_num, programs in guide_data.items():
                    channel_id = f'frndly-{channel_id_num}'
                    
                    for prog_data in programs:
                        try:
                            prog = Program(prog_data, channel_id_num)
                            
                            start = datetime.datetime.utcfromtimestamp(prog.start_time).strftime("%Y%m%d%H%M%S +0000")
                            stop = datetime.datetime.utcfromtimestamp(prog.end_time).strftime("%Y%m%d%H%M%S +0000")
                            
                            prog_xml = f'  <programme start="{start}" stop="{stop}" channel="{channel_id}">\n'
                            prog_xml += f'    <title lang="en">{escape(prog.title)}</title>\n'
                            
                            if prog.episode_title and prog.episode_title != prog.title:
                                prog_xml += f'    <sub-title lang="en">{escape(prog.episode_title)}</sub-title>\n'
                            
                            if prog.description:
                                prog_xml += f'    <desc lang="en">{escape(prog.description)}</desc>\n'
                            
                            if prog.season and prog.episode:
                                ep_num = f'{prog.season - 1}.{prog.episode - 1}.0/1'
                                prog_xml += f'    <episode-num system="xmltv_ns">{ep_num}</episode-num>\n'
                                prog_xml += f'    <episode-num system="onscreen">S{prog.season:02d}E{prog.episode:02d}</episode-num>\n'
                            
                            if prog.genres:
                                genres = prog.genres if isinstance(prog.genres, list) else [prog.genres]
                                for genre in genres:
                                    prog_xml += f'    <category lang="en">{escape(str(genre))}</category>\n'
                            
                            if prog.rating:
                                prog_xml += f'    <rating system="VCHIP">\n'
                                prog_xml += f'      <value>{escape(prog.rating)}</value>\n'
                                prog_xml += f'    </rating>\n'
                            
                            if prog.year:
                                prog_xml += f'    <date>{prog.year}</date>\n'
                            
                            if prog.thumbnail:
                                prog_xml += f'    <icon src="{escape(prog.thumbnail)}"/>\n'
                            
                            if prog.is_new:
                                prog_xml += '    <new/>\n'
                            if prog.is_premiere:
                                prog_xml += '    <premiere/>\n'
                            
                            prog_xml += '  </programme>\n'
                            
                            self.wfile.write(prog_xml.encode('utf-8'))
                            
                        except:
                            continue
                            
            except:
                pass
        
        self.wfile.write(b'</tv>\n')
    
    def _handle_play(self):
        """Handle stream playback request"""
        if not self.api:
            self._send_error(500, 'API not initialized')
            return
        
        path = urlparse(self.path).path
        slug = path.split('/')[-1].split('.')[0]
        
        try:
            url = self.api.play(slug)
            self.send_response(302)
            self.send_header('Location', url)
            self.end_headers()
        except FrndlyException as e:
            self._send_error(500, str(e))
    
    def _handle_keep_alive(self):
        """Handle keep-alive request"""
        if self.api:
            try:
                self.api.keep_alive()
            except:
                pass
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'OK')


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Threaded HTTP Server"""
    daemon_threads = True
    allow_reuse_address = True


def start_server(port, api):
    """Start the web server"""
    global _server, _server_thread
    
    if _server is not None:
        stop_server()
    
    FrndlyRequestHandler.api = api
    
    try:
        _server = ThreadedHTTPServer(('0.0.0.0', port), FrndlyRequestHandler)
        _server_thread = threading.Thread(target=_server.serve_forever)
        _server_thread.daemon = True
        _server_thread.start()
        
        try:
            import xbmc
            xbmc.log(f"[FrndlyTV] Web server started on port {port}", xbmc.LOGINFO)
        except:
            print(f"[FrndlyTV] Web server started on port {port}")
        
        return True
    except Exception as e:
        try:
            import xbmc
            xbmc.log(f"[FrndlyTV] Failed to start web server: {e}", xbmc.LOGERROR)
        except:
            print(f"[FrndlyTV] Failed to start web server: {e}")
        return False


def stop_server():
    """Stop the web server"""
    global _server, _server_thread
    
    if _server:
        try:
            _server.shutdown()
            _server.server_close()
        except:
            pass
        _server = None
    
    _server_thread = None


def is_running():
    """Check if server is running"""
    return _server is not None and _server_thread is not None and _server_thread.is_alive()


def get_server_info():
    """Get server information"""
    if not is_running():
        return None
    
    return {
        'address': _server.server_address,
        'port': _server.server_address[1],
    }
