"""
Frndly TV API Library for Kodi
Enhanced with full EPG metadata, ratings, thumbnails, and episode info

Developed by Marcus Montgomery and BeatTLF Entertainment
Based on frndlytv-for-channels by Matt Huisman
"""

import time
import json
import os
import re

try:
    import requests
except ImportError:
    import xbmc
    xbmc.log("Frndly TV: requests module not available, using urllib", xbmc.LOGWARNING)
    import urllib.request
    import urllib.parse
    import urllib.error
    
    class RequestsCompat:
        """Simple requests-like interface using urllib"""
        @staticmethod
        def get(url, params=None, headers=None, timeout=15):
            if params:
                url = url + '?' + urllib.parse.urlencode(params)
            req = urllib.request.Request(url, headers=headers or {})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return RequestsCompat.Response(response.read(), response.getcode())
        
        @staticmethod
        def post(url, data=None, json_data=None, headers=None, timeout=15):
            headers = headers or {}
            if json_data:
                data = json.dumps(json_data).encode('utf-8')
                headers['Content-Type'] = 'application/json'
            elif data:
                data = urllib.parse.urlencode(data).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return RequestsCompat.Response(response.read(), response.getcode())
        
        class Response:
            def __init__(self, content, status_code):
                self.content = content
                self.status_code = status_code
            
            def json(self):
                return json.loads(self.content.decode('utf-8'))
    
    requests = RequestsCompat()

# Constants
BOX_ID = 'SHIELD30X8X4X0'
TENANT_CODE = 'frndlytv'
DEVICE_ID = 43
TIMEOUT = 15
LOGO_SIZE = 400
FORCE_LOGIN = 60 * 60 * 5  # Force login after 5 hours

HEADERS = {
    'user-agent': 'okhttp/3.12.5',
    'box-id': BOX_ID,
    'tenant-code': TENANT_CODE,
}

LOGO_URL = 'https://d229kpbsb5jevy.cloudfront.net/frndlytv/{size}/{size}/content/{bucket}/logos/{path}'
THUMB_URL = 'https://d229kpbsb5jevy.cloudfront.net/frndlytv/{size}/{size}/content/{bucket}/thumbnails/{path}'
IMAGE_URL = 'https://d229kpbsb5jevy.cloudfront.net/frndlytv/{size}/{size}/content/{bucket}/{path}'
DATA_URL = 'https://i.mjh.nz/frndly_tv/app.json'

# TV Parental Guidelines mapping
TV_RATINGS = {
    'tv-y': 'TV-Y',
    'tv-y7': 'TV-Y7', 
    'tv-y7-fv': 'TV-Y7-FV',
    'tv-g': 'TV-G',
    'tv-pg': 'TV-PG',
    'tv-14': 'TV-14',
    'tv-ma': 'TV-MA',
    'g': 'G',
    'pg': 'PG',
    'pg-13': 'PG-13',
    'r': 'R',
    'nc-17': 'NC-17',
    'nr': 'NR',
    'unrated': 'Unrated',
}


class FrndlyException(Exception):
    """Custom exception for Frndly TV errors"""
    pass


class Program:
    """Represents a TV program with full metadata"""
    
    def __init__(self, data, channel_id=None):
        self.raw = data
        self.channel_id = channel_id
        self._parse(data)
    
    def _parse(self, data):
        """Parse program data from API response"""
        display = data.get('display', {})
        metadata = data.get('metadata', {})
        markers = display.get('markers', {})
        
        # Basic info
        self.title = display.get('title', 'Unknown')
        self.description = display.get('description', '')
        self.subtitle = display.get('subtitle', '')
        
        # Times
        try:
            self.start_time = int(markers.get('startTime', {}).get('value', 0)) / 1000
            self.end_time = int(markers.get('endTime', {}).get('value', 0)) / 1000
            self.duration = int(self.end_time - self.start_time)
        except:
            self.start_time = 0
            self.end_time = 0
            self.duration = 0
        
        # Episode info
        self.season = metadata.get('seasonNumber') or metadata.get('season')
        self.episode = metadata.get('episodeNumber') or metadata.get('episode')
        self.episode_title = metadata.get('episodeTitle') or self.subtitle
        
        # Extract from title pattern (e.g., "S01E05")
        if not self.season or not self.episode:
            match = re.search(r'[Ss](\d+)[Ee](\d+)', str(self.title) + ' ' + str(self.subtitle))
            if match:
                self.season = int(match.group(1))
                self.episode = int(match.group(2))
        
        # Convert to int if present
        try:
            self.season = int(self.season) if self.season else None
        except:
            self.season = None
        try:
            self.episode = int(self.episode) if self.episode else None
        except:
            self.episode = None
        
        # Content type
        content_type = metadata.get('contentType', '') or metadata.get('type', '')
        self.content_type = content_type.lower() if content_type else 'show'
        self.is_movie = self.content_type in ('movie', 'film', 'feature')
        self.is_series = self.content_type in ('series', 'show', 'episode', 'tvshow')
        self.is_live = metadata.get('isLive', False) or metadata.get('live', False)
        self.is_new = metadata.get('isNew', False) or metadata.get('new', False)
        self.is_premiere = metadata.get('isPremiere', False)
        self.is_finale = metadata.get('isFinale', False)
        self.is_repeat = metadata.get('isRepeat', False)
        
        # Rating (TV Parental Guidelines)
        rating_str = str(metadata.get('rating') or metadata.get('tvRating') or 
                        metadata.get('contentRating') or '').lower().strip()
        self.rating = TV_RATINGS.get(rating_str, rating_str.upper() if rating_str else '')
        self.mpaa = self.rating
        
        # Year
        self.year = metadata.get('year') or metadata.get('releaseYear') or metadata.get('originalAirDate', '')[:4]
        try:
            self.year = int(self.year) if self.year and str(self.year).isdigit() else None
        except:
            self.year = None
        
        # Original air date
        self.original_air_date = metadata.get('originalAirDate', '')
        
        # Genre
        genres = metadata.get('genres') or metadata.get('genre') or []
        if isinstance(genres, str):
            genres = [g.strip() for g in genres.split(',')]
        self.genres = genres
        
        # Images/Thumbnails
        self.thumbnail = ''
        self.poster = ''
        self.fanart = ''
        self.icon = ''
        
        # Try multiple image sources
        img_sources = [
            display.get('imageUrl'),
            metadata.get('thumbnail'),
            metadata.get('image'),
            metadata.get('posterUrl'),
            metadata.get('backgroundUrl'),
        ]
        
        for img_url in img_sources:
            if img_url and not self.thumbnail:
                try:
                    if ',' in str(img_url):
                        bucket, path = str(img_url).split(',', 1)
                        self.thumbnail = IMAGE_URL.format(size=400, bucket=bucket, path=path)
                        self.poster = IMAGE_URL.format(size=600, bucket=bucket, path=path)
                        self.fanart = IMAGE_URL.format(size=1280, bucket=bucket, path=path)
                        self.icon = IMAGE_URL.format(size=200, bucket=bucket, path=path)
                    elif img_url.startswith('http'):
                        self.thumbnail = img_url
                        self.poster = img_url
                except:
                    pass
        
        # Cast and crew
        cast_data = metadata.get('cast') or metadata.get('actors') or []
        if isinstance(cast_data, str):
            cast_data = [c.strip() for c in cast_data.split(',')]
        self.cast = cast_data
        
        directors = metadata.get('directors') or metadata.get('director') or []
        if isinstance(directors, str):
            directors = [d.strip() for d in directors.split(',')]
        self.directors = directors
        
        # IDs
        self.program_id = data.get('id') or metadata.get('programId') or metadata.get('id')
        self.series_id = metadata.get('seriesId')
        
        # Path for playback
        self.path = None
        target = data.get('target', {})
        if target:
            self.path = target.get('path')
    
    def get_progress(self):
        """Get current playback progress (0-100)"""
        if not self.start_time or not self.end_time:
            return 0
        cur_time = time.time()
        if cur_time < self.start_time:
            return 0
        if cur_time > self.end_time:
            return 100
        return int((cur_time - self.start_time) / (self.end_time - self.start_time) * 100)
    
    def get_time_remaining(self):
        """Get minutes remaining"""
        remaining = self.end_time - time.time()
        return max(0, int(remaining / 60))
    
    def format_episode(self):
        """Format episode string like 'S01E05'"""
        if self.season and self.episode:
            return f"S{self.season:02d}E{self.episode:02d}"
        elif self.episode:
            return f"E{self.episode:02d}"
        return ""
    
    def to_kodi_info(self):
        """Convert to Kodi InfoLabel dict"""
        info = {
            'title': self.title,
            'plot': self.description,
            'plotoutline': self.subtitle or (self.description[:150] + '...' if len(self.description) > 150 else self.description),
            'mediatype': 'movie' if self.is_movie else 'episode',
        }
        
        if self.season:
            info['season'] = self.season
        if self.episode:
            info['episode'] = self.episode
        if self.episode_title:
            info['episodename'] = self.episode_title
        if self.year:
            info['year'] = self.year
        if self.rating:
            info['mpaa'] = self.rating
        if self.genres:
            info['genre'] = ', '.join(self.genres) if isinstance(self.genres, list) else self.genres
        if self.duration:
            info['duration'] = self.duration
        if self.cast:
            info['cast'] = self.cast[:10]
        if self.directors:
            info['director'] = ', '.join(self.directors) if isinstance(self.directors, list) else self.directors
        if self.original_air_date:
            info['aired'] = self.original_air_date
        
        # Tags for special markers
        tags = []
        if self.is_new:
            tags.append('New')
        if self.is_premiere:
            tags.append('Premiere')
        if self.is_finale:
            tags.append('Finale')
        if self.is_live:
            tags.append('Live')
        if tags:
            info['tag'] = tags
        
        return info
    
    def to_kodi_art(self):
        """Convert to Kodi art dict"""
        art = {}
        if self.thumbnail:
            art['thumb'] = self.thumbnail
        if self.poster:
            art['poster'] = self.poster
        if self.fanart:
            art['fanart'] = self.fanart
        if self.icon:
            art['icon'] = self.icon
        return art


class Channel:
    """Represents a TV channel with metadata"""
    
    def __init__(self, data, live_map=None):
        self.raw = data
        self._parse(data, live_map or {})
        self.current_program = None
        self.next_program = None
    
    def _parse(self, data, live_map):
        """Parse channel data"""
        display = data.get('display', {})
        metadata = data.get('metadata', {})
        
        # IDs
        self.id = str(data.get('id', ''))
        self.channel_id = f'frndly-{self.id}'
        
        # Get data from live map
        map_data = live_map.get(self.id, {})
        
        # Name
        self.name = display.get('title', 'Unknown Channel')
        
        # Number
        self.number = map_data.get('chno') or metadata.get('channelNumber') or self.id
        try:
            self.number = int(self.number)
        except:
            self.number = 0
        
        # Slug for playback
        self.slug = self.id
        if 'slug' in map_data:
            self.slug = f"{map_data['slug']}-{self.id}"
        
        # Logo
        self.logo = ''
        img_url = display.get('imageUrl', '')
        if img_url and ',' in img_url:
            try:
                bucket, path = img_url.split(',', 1)
                self.logo = LOGO_URL.format(size=LOGO_SIZE, bucket=bucket, path=path)
            except:
                pass
        
        # Gracenote ID (for external EPG)
        self.gracenote_id = map_data.get('gracenote', '')
        
        # Category/Group
        self.category = metadata.get('category', '') or metadata.get('group', '')
        
        # HD/SD
        self.is_hd = metadata.get('isHD', False) or 'hd' in self.name.lower()
    
    def to_kodi_info(self):
        """Convert to Kodi InfoLabel dict"""
        info = {
            'title': self.name,
            'mediatype': 'video',
        }
        
        # Add current program info if available
        if self.current_program:
            prog = self.current_program
            info['plot'] = f"NOW: {prog.title}"
            if prog.description:
                info['plot'] += f"\n\n{prog.description}"
            if prog.rating:
                info['mpaa'] = prog.rating
            if prog.episode_title:
                info['plot'] += f"\n{prog.episode_title}"
            
            # Add next program
            if self.next_program:
                info['plot'] += f"\n\nNEXT: {self.next_program.title}"
        
        return info
    
    def to_kodi_art(self):
        """Convert to Kodi art dict"""
        art = {'icon': self.logo, 'thumb': self.logo}
        
        # Use current program art if available
        if self.current_program and self.current_program.thumbnail:
            art['fanart'] = self.current_program.fanart or self.current_program.thumbnail
            art['poster'] = self.current_program.poster or self.current_program.thumbnail
        
        return art


class FrndlyTV:
    """Frndly TV API Client for Kodi"""
    
    def __init__(self, username=None, password=None, cache_path=None):
        self._username = username
        self._password = password
        self._cache_path = cache_path
        self._headers = dict(HEADERS)
        self._live_map = {}
        self._last_login = 0
        self._channels_cache = None
        self._channels_cache_time = 0
        self._epg_cache = {}
        self._epg_cache_time = 0
        self._session_id = None
        
        # Try to restore session from cache
        self._load_session()
    
    def _log(self, message, level='info'):
        """Log message"""
        try:
            import xbmc
            log_levels = {
                'debug': xbmc.LOGDEBUG,
                'info': xbmc.LOGINFO,
                'warning': xbmc.LOGWARNING,
                'error': xbmc.LOGERROR,
            }
            xbmc.log(f"[FrndlyTV] {message}", log_levels.get(level, xbmc.LOGINFO))
        except:
            print(f"[FrndlyTV] {message}")
    
    def _get_cache_file(self):
        """Get the cache file path"""
        if self._cache_path:
            return os.path.join(self._cache_path, 'frndly_session.json')
        return None
    
    def _save_session(self):
        """Save session to cache"""
        cache_file = self._get_cache_file()
        if cache_file:
            try:
                data = {
                    'session_id': self._headers.get('session-id'),
                    'last_login': self._last_login,
                }
                with open(cache_file, 'w') as f:
                    json.dump(data, f)
                self._log("Session saved to cache", 'debug')
            except Exception as e:
                self._log(f"Failed to save session: {e}", 'error')
    
    def _load_session(self):
        """Load session from cache"""
        cache_file = self._get_cache_file()
        if cache_file and os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                
                session_id = data.get('session_id')
                last_login = data.get('last_login', 0)
                
                if session_id and (time.time() - last_login) < FORCE_LOGIN:
                    self._headers['session-id'] = session_id
                    self._last_login = last_login
                    self._log("Session restored from cache", 'debug')
                    return True
            except Exception as e:
                self._log(f"Failed to load session: {e}", 'error')
        return False
    
    def set_credentials(self, username, password):
        """Update credentials"""
        self._username = username
        self._password = password
    
    def logo_url(self, img_url, size=LOGO_SIZE):
        """Get logo URL from image path"""
        try:
            if img_url and ',' in img_url:
                bucket, path = img_url.split(',', 1)
                return LOGO_URL.format(size=size, bucket=bucket, path=path)
        except:
            pass
        return ''
    
    def image_url(self, img_url, size=400):
        """Get image URL from image path"""
        try:
            if img_url and ',' in img_url:
                bucket, path = img_url.split(',', 1)
                return IMAGE_URL.format(size=size, bucket=bucket, path=path)
        except:
            pass
        return ''
    
    def _channel_path(self, channel_id):
        """Get the current program path for a channel"""
        cur_time = int(time.time())
        
        data = self.guide([channel_id])
        for row in data.get(channel_id, []):
            try:
                start_time = int(row['display']['markers']['startTime']['value']) / 1000
                end_time = int(row['display']['markers']['endTime']['value']) / 1000
                if start_time <= cur_time <= end_time:
                    return row['target']['path']
            except (KeyError, TypeError):
                continue
        
        raise FrndlyException(f'Unable to find live stream for channel: {channel_id}')
    
    def _get_play_url(self, path):
        """Get the playable stream URL"""
        params = {
            'path': path,
            'code': path,
            'include_ads': 'false',
            'is_casted': 'true',
        }
        
        data = self._request('https://frndlytv-api.revlet.net/service/api/v1/page/stream', params=params)
        
        try:
            stream = sorted(data['streams'], key=lambda x: x['keys'].get('licenseKey', ''))[0]
            url = stream['url']
            stream_type = stream.get('streamType', '')
        except (KeyError, IndexError, TypeError):
            raise FrndlyException(f'Unable to find stream for: {path}')
        
        try:
            start_time = int(int(data['playerSettings'][0]['value']) / 1000)
            url += f'&start={start_time}&startTime={start_time}'
        except:
            pass
        
        if stream_type.lower().strip() in ('widevine',):
            raise FrndlyException(f'Unsupported DRM stream type: {stream_type}')
        
        self._log(f"Stream URL obtained for: {path}", 'debug')
        
        try:
            poll_key = data.get('sessionInfo', {}).get('streamPollKey')
            if poll_key:
                requests.post(
                    'https://frndlytv-api.revlet.net/service/api/v1/stream/session/end',
                    data={'poll_key': poll_key},
                    headers=self._headers,
                    timeout=TIMEOUT
                )
        except:
            pass
        
        return url
    
    def play(self, slug):
        """Get playable URL for a channel"""
        if slug.isdigit():
            channel_id = slug
        else:
            parts = slug.rsplit('-', 1)
            if len(parts) == 2:
                slug_name, channel_id = parts
                try:
                    return self._get_play_url(f'channel/live/{slug_name}')
                except Exception as e:
                    self._log(f"Failed to play via slug {slug_name}, using ID: {e}", 'debug')
            else:
                channel_id = slug
        
        self._log(f"Playing channel ID: {channel_id}", 'debug')
        path = self._channel_path(channel_id)
        return self._get_play_url(path)
    
    def guide(self, channel_ids, start=None, days=1):
        """Get TV guide/EPG data for channels"""
        programs = {}
        
        for _ in range(days):
            params = {
                'channel_ids': ','.join(str(cid) for cid in channel_ids),
                'page': 0,
            }
            
            if start:
                end = start + 86400
                params['start_time'] = start * 1000
                params['end_time'] = end * 1000
                start = end
            
            try:
                data = self._request(
                    'https://frndlytv-tvguideapi.revlet.net/service/api/v1/static/tvguide',
                    params=params
                )
                
                for row in data.get('data', []):
                    channel_id = str(row['channelId'])
                    if channel_id not in programs:
                        programs[channel_id] = []
                    programs[channel_id].extend(row.get('programs', []))
            except Exception as e:
                self._log(f"Failed to get guide data: {e}", 'error')
        
        return programs
    
    def get_current_programs(self, channel_ids):
        """Get currently playing programs for channels"""
        current = {}
        next_up = {}
        cur_time = int(time.time())
        
        guide_data = self.guide(channel_ids)
        
        for channel_id, programs in guide_data.items():
            for i, prog_data in enumerate(programs):
                try:
                    prog = Program(prog_data, channel_id)
                    if prog.start_time <= cur_time <= prog.end_time:
                        current[channel_id] = prog
                        if i + 1 < len(programs):
                            next_up[channel_id] = Program(programs[i + 1], channel_id)
                        break
                except:
                    continue
        
        return current, next_up
    
    def get_epg_for_channel(self, channel_id, days=3):
        """Get detailed EPG for a single channel"""
        guide_data = self.guide([channel_id], start=int(time.time()), days=days)
        programs = []
        
        for prog_data in guide_data.get(channel_id, []):
            try:
                programs.append(Program(prog_data, channel_id))
            except:
                continue
        
        return programs
    
    def _request(self, url, params=None, retry_count=3):
        """Make API request with automatic retry and re-login"""
        for attempt in range(retry_count):
            try:
                self._log(f"Request: {url}", 'debug')
                response = requests.get(url, params=params, headers=self._headers, timeout=TIMEOUT)
                data = response.json()
                
                if 'response' in data:
                    return data['response']
                
                try:
                    error_code = data['error']['code']
                    error_msg = data['error'].get('message', 'Unknown error')
                    self._log(f"API Error {error_code}: {error_msg}")
                    
                    if error_code == 404:
                        raise FrndlyException(error_msg)
                except KeyError:
                    pass
                
                self.login()
                
            except FrndlyException:
                raise
            except Exception as e:
                self._log(f"Request error: {e}", 'error')
                if attempt < retry_count - 1:
                    time.sleep(1)
        
        raise FrndlyException(f'Failed to get response from: {url}')
    
    def keep_alive(self):
        """Keep session alive"""
        if (time.time() - self._last_login) > FORCE_LOGIN:
            self._log("Forcing re-login due to session timeout")
            self.login()
        else:
            self.channels(force_refresh=True)
    
    def channels(self, force_refresh=False):
        """Get list of available channels (raw data)"""
        if not force_refresh and self._channels_cache and (time.time() - self._channels_cache_time) < 300:
            return self._channels_cache
        
        rows = self._request('https://frndlytv-api.revlet.net/service/api/v1/tvguide/channels?skip_tabs=0')
        channels = rows.get('data', [])
        
        if not channels:
            raise FrndlyException(
                'No channels returned. This is likely due to your IP location. '
                'Frndly TV may not be available in your region.'
            )
        
        channels = [
            ch for ch in channels 
            if ch.get('metadata', {}).get('isChannelBanner', '').lower() != 'true'
        ]
        
        self._channels_cache = channels
        self._channels_cache_time = time.time()
        
        return channels
    
    def channels_detailed(self, force_refresh=False):
        """Get channels as Channel objects with current program info"""
        raw_channels = self.channels(force_refresh)
        live_map = self.live_map()
        
        channels = [Channel(ch, live_map) for ch in raw_channels]
        
        channel_ids = [ch.id for ch in channels]
        current_progs, next_progs = self.get_current_programs(channel_ids)
        
        for ch in channels:
            ch.current_program = current_progs.get(ch.id)
            ch.next_program = next_progs.get(ch.id)
        
        return channels
    
    def live_map(self):
        """Get channel mapping data"""
        try:
            response = requests.get(DATA_URL, timeout=TIMEOUT)
            self._live_map = response.json()
        except Exception as e:
            self._log(f'Failed to download live map: {e}', 'warning')
        
        return self._live_map
    
    def login(self):
        """Login to Frndly TV"""
        self._log("Logging in...")
        
        if not self._username or not self._password:
            raise FrndlyException('Username and password are required')
        
        params = {
            'box_id': BOX_ID,
            'device_id': DEVICE_ID,
            'tenant_code': TENANT_CODE,
            'device_sub_type': 'nvidia,8.1.0,7.4.4',
            'product': TENANT_CODE,
            'display_lang_code': 'eng',
            'timezone': 'America/New_York',
        }
        
        headers = {k: v for k, v in self._headers.items() if k != 'session-id'}
        
        try:
            response = requests.get(
                'https://frndlytv-api.revlet.net/service/api/v1/get/token',
                params=params,
                headers=headers,
                timeout=TIMEOUT
            )
            session_id = response.json()['response']['sessionId']
            headers['session-id'] = session_id
        except Exception as e:
            raise FrndlyException(f'Failed to get session token: {e}')
        
        payload = {
            "login_id": self._username,
            "login_key": self._password,
            "login_mode": 1,
            "os_version": "8.1.0",
            "app_version": "7.4.4",
            "manufacturer": "nvidia"
        }
        
        try:
            if hasattr(requests, 'Session'):
                response = requests.post(
                    'https://frndlytv-api.revlet.net/service/api/auth/signin',
                    json=payload,
                    headers=headers,
                    timeout=TIMEOUT
                )
            else:
                response = requests.post(
                    'https://frndlytv-api.revlet.net/service/api/auth/signin',
                    json_data=payload,
                    headers=headers,
                    timeout=TIMEOUT
                )
            data = response.json()
        except Exception as e:
            raise FrndlyException(f'Login request failed: {e}')
        
        if not data.get('status'):
            error_msg = data.get('error', {}).get('message', 'Unknown login error')
            raise FrndlyException(f'Login failed: {error_msg}')
        
        self._log("Login successful!")
        self._last_login = time.time()
        self._headers = headers
        self._save_session()
        
        return True
    
    def is_logged_in(self):
        """Check if we have a valid session"""
        return 'session-id' in self._headers and (time.time() - self._last_login) < FORCE_LOGIN
    
    def logout(self):
        """Clear session"""
        if 'session-id' in self._headers:
            del self._headers['session-id']
        self._last_login = 0
        self._channels_cache = None
        
        cache_file = self._get_cache_file()
        if cache_file and os.path.exists(cache_file):
            try:
                os.remove(cache_file)
            except:
                pass


# Singleton instance
_instance = None

def get_api(username=None, password=None, cache_path=None):
    """Get or create API instance"""
    global _instance
    if _instance is None:
        _instance = FrndlyTV(username, password, cache_path)
    elif username and password:
        _instance.set_credentials(username, password)
    return _instance
