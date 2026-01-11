"""
Frndly TV Kodi Addon - Background Service
Manages the built-in web server and session keep-alive

Developed by Marcus Montgomery and BeatTLF Entertainment
Based on frndlytv-for-channels by Matt Huisman
"""

import os
import sys
import time
import threading

import xbmc
import xbmcaddon
import xbmcvfs
import xbmcgui

# Addon info
ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
ADDON_DATA = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))

# Ensure addon data directory exists
if not os.path.exists(ADDON_DATA):
    os.makedirs(ADDON_DATA)

# Add lib to path
sys.path.insert(0, os.path.join(ADDON_PATH, 'resources', 'lib'))


def log(message, level=xbmc.LOGINFO):
    """Log message to Kodi log"""
    xbmc.log(f'[{ADDON_ID}] {message}', level)


def get_setting(key):
    """Get addon setting"""
    return ADDON.getSetting(key)


class FrndlyService(xbmc.Monitor):
    """Background service for Frndly TV"""
    
    def __init__(self):
        super().__init__()
        self.api = None
        self.server_running = False
        self.last_keep_alive = 0
        
        log(f"Frndly TV for Kodi v{ADDON_VERSION} - Service initialized")
        log("Developed by Marcus Montgomery and BeatTLF Entertainment")
    
    def get_api(self):
        """Get or create API instance"""
        if self.api is None:
            from frndly_api import FrndlyTV
            
            username = get_setting('username')
            password = get_setting('password')
            
            if username and password:
                self.api = FrndlyTV(username, password, ADDON_DATA)
        
        return self.api
    
    def start_server(self):
        """Start the web server if enabled"""
        if get_setting('enable_server') != 'true':
            log("Web server is disabled in settings")
            return False
        
        api = self.get_api()
        if not api:
            log("Cannot start server - no credentials configured")
            return False
        
        # Try to login first
        try:
            if not api.is_logged_in():
                api.login()
        except Exception as e:
            log(f"Failed to login for server: {e}", xbmc.LOGERROR)
            return False
        
        # Start server
        try:
            port = int(get_setting('server_port') or 8183)
        except:
            port = 8183
        
        from webserver import start_server, is_running
        
        if is_running():
            log("Server already running")
            return True
        
        if start_server(port, api):
            self.server_running = True
            log(f"Web server started on port {port}")
            
            # Get IP for notification
            import socket
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(('8.8.8.8', 80))
                local_ip = s.getsockname()[0]
                s.close()
            except:
                local_ip = 'localhost'
            
            # Show notification
            xbmcgui.Dialog().notification(
                ADDON_NAME,
                f'Server: http://{local_ip}:{port}',
                xbmcgui.NOTIFICATION_INFO,
                5000
            )
            return True
        else:
            log("Failed to start web server", xbmc.LOGERROR)
            return False
    
    def stop_server(self):
        """Stop the web server"""
        from webserver import stop_server, is_running
        
        if is_running():
            stop_server()
            self.server_running = False
            log("Web server stopped")
    
    def keep_alive(self):
        """Keep the session alive"""
        api = self.get_api()
        if not api:
            return
        
        try:
            keep_alive_mins = int(get_setting('keep_alive_mins') or 30)
        except:
            keep_alive_mins = 30
        
        if keep_alive_mins <= 0:
            return
        
        current_time = time.time()
        interval = keep_alive_mins * 60
        
        if (current_time - self.last_keep_alive) >= interval:
            try:
                api.keep_alive()
                self.last_keep_alive = current_time
                log("Keep-alive successful", xbmc.LOGDEBUG)
            except Exception as e:
                log(f"Keep-alive failed: {e}", xbmc.LOGWARNING)
    
    def onSettingsChanged(self):
        """Called when addon settings change"""
        log("Settings changed, reloading...")
        
        # Reload API with new credentials
        self.api = None
        
        # Handle server setting changes
        enable_server = get_setting('enable_server') == 'true'
        
        from webserver import is_running
        
        if enable_server and not is_running():
            self.start_server()
        elif not enable_server and is_running():
            self.stop_server()
    
    def run(self):
        """Main service loop"""
        log("Service starting...")
        
        # Wait for Kodi to fully start
        xbmc.sleep(5000)
        
        # Start server if enabled
        self.start_server()
        
        # Main loop
        while not self.abortRequested():
            # Keep session alive
            self.keep_alive()
            
            # Check if server should be running
            if get_setting('enable_server') == 'true':
                from webserver import is_running
                if not is_running() and self.server_running:
                    log("Server stopped unexpectedly, restarting...")
                    self.start_server()
            
            # Wait before next iteration
            if self.waitForAbort(60):  # Check every minute
                break
        
        # Cleanup
        log("Service stopping...")
        self.stop_server()
        log("Service stopped")


def main():
    """Service entry point"""
    service = FrndlyService()
    service.run()


if __name__ == '__main__':
    main()
