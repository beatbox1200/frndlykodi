"""
Enhanced PVR/DVR Helper for Frndly TV Kodi Addon
Automatic installation and configuration of PVR IPTV Simple Client

Developed by Marcus Montgomery and BeatTLF Entertainment
"""

import os
import json
import time

try:
    import xbmc
    import xbmcaddon
    import xbmcgui
    import xbmcvfs
except ImportError:
    # For testing outside Kodi
    pass


def get_local_ip():
    """Get the local IP address"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return '127.0.0.1'


def get_pvr_addon():
    """Check if IPTV Simple Client is installed and get its addon object"""
    try:
        addon = xbmcaddon.Addon('pvr.iptvsimple')
        return addon
    except:
        return None


def is_pvr_installed():
    """Check if PVR IPTV Simple Client is installed"""
    return xbmc.getCondVisibility('System.HasAddon(pvr.iptvsimple)')


def is_pvr_enabled():
    """Check if PVR is enabled in Kodi"""
    try:
        return xbmc.getCondVisibility('Pvr.HasTVChannels') or is_pvr_installed()
    except:
        return False


def install_pvr_addon():
    """
    Install PVR IPTV Simple Client addon
    Returns True if successful or already installed
    """
    if is_pvr_installed():
        return True
    
    try:
        # Show progress dialog
        dialog = xbmcgui.DialogProgress()
        dialog.create('Installing PVR IPTV Simple Client', 'Please wait...')
        
        # Install the addon using JSON-RPC
        xbmc.executebuiltin('InstallAddon(pvr.iptvsimple)', True)
        
        # Wait for installation (max 30 seconds)
        for i in range(30):
            if dialog.iscanceled():
                dialog.close()
                return False
            
            dialog.update(int((i / 30) * 100), 'Installing PVR IPTV Simple Client...')
            
            if is_pvr_installed():
                dialog.update(100, 'Installation complete!')
                time.sleep(1)
                dialog.close()
                return True
            
            time.sleep(1)
        
        dialog.close()
        return is_pvr_installed()
        
    except Exception as e:
        xbmc.log(f"[FrndlyTV] Failed to install PVR addon: {e}", xbmc.LOGERROR)
        return False


def configure_pvr_simple(playlist_url, epg_url):
    """
    Configure IPTV Simple Client with Frndly TV URLs
    Returns (success, message)
    """
    pvr_addon = get_pvr_addon()
    
    if not pvr_addon:
        return False, "IPTV Simple Client is not installed."
    
    try:
        # Set M3U playlist
        pvr_addon.setSetting('m3uPathType', '1')  # Remote path
        pvr_addon.setSetting('m3uUrl', playlist_url)
        pvr_addon.setSetting('m3uRefreshMode', '1')  # Repeated refresh
        pvr_addon.setSetting('m3uRefreshIntervalMins', '60')  # Refresh every hour
        pvr_addon.setSetting('m3uRefreshHour', '4')  # Refresh at 4 AM
        
        # Set EPG
        pvr_addon.setSetting('epgPathType', '1')  # Remote path
        pvr_addon.setSetting('epgUrl', epg_url)
        pvr_addon.setSetting('epgTimeShift', '0')  # No time shift
        
        # Enable logos from M3U
        pvr_addon.setSetting('logoFromEpg', '1')  # Use logos from EPG
        pvr_addon.setSetting('logoPathType', '1')  # Remote path
        
        # Cache settings
        pvr_addon.setSetting('m3uCache', 'true')
        pvr_addon.setSetting('epgCache', 'true')
        
        # Channel settings
        pvr_addon.setSetting('startNum', '1')
        pvr_addon.setSetting('numberByOrder', 'false')
        
        return True, "PVR IPTV Simple Client configured successfully!"
    except Exception as e:
        return False, f"Failed to configure IPTV Simple Client: {str(e)}"


def enable_pvr_in_kodi():
    """Enable PVR in Kodi settings"""
    try:
        # Enable PVR addon
        xbmc.executebuiltin('EnableAddon(pvr.iptvsimple)', True)
        time.sleep(2)
        
        return True
    except Exception as e:
        xbmc.log(f"[FrndlyTV] Failed to enable PVR: {e}", xbmc.LOGERROR)
        return False


def restart_pvr():
    """Restart the PVR to load new settings"""
    try:
        xbmc.executebuiltin('UpdateLibrary(video)')
        # Give it a moment to process
        time.sleep(2)
        return True
    except:
        return False


def setup_pvr_automatic():
    """
    Fully automatic PVR setup workflow
    Returns (success, message)
    """
    try:
        addon = xbmcaddon.Addon()
        
        # Step 1: Check if web server is enabled
        enable_server = addon.getSetting('enable_server') == 'true'
        port = addon.getSetting('server_port') or '8183'
        
        if not enable_server:
            # Ask user if they want to enable the web server
            dialog = xbmcgui.Dialog()
            result = dialog.yesno(
                'Enable Web Server?',
                'To use PVR/DVR features with Frndly TV, the built-in web server must be enabled.\n\n'
                'This will allow Kodi\'s PVR system to access your Frndly TV channels and guide data.\n\n'
                'Would you like to enable the web server now?'
            )
            
            if not result:
                return False, "Web server must be enabled for PVR functionality."
            
            # Enable the web server
            addon.setSetting('enable_server', 'true')
            
            # Wait for server to start
            progress = xbmcgui.DialogProgress()
            progress.create('Starting Web Server', 'Please wait...')
            
            from webserver import is_running
            
            # Wait up to 10 seconds for server to start
            for i in range(10):
                if progress.iscanceled():
                    progress.close()
                    return False, "Setup canceled by user."
                
                progress.update(int((i / 10) * 100), 'Starting web server...')
                time.sleep(1)
                
                if is_running():
                    break
            
            progress.close()
            
            if not is_running():
                # Try restarting the service
                xbmc.executebuiltin('XBMC.NotifyAll(plugin.video.frndlytv, restart_service)')
                time.sleep(3)
        
        # Step 2: Get server URLs
        local_ip = get_local_ip()
        playlist_url = f'http://{local_ip}:{port}/playlist.m3u8?gracenote=exclude'
        epg_url = f'http://{local_ip}:{port}/epg.xml?gracenote=exclude'
        
        # Step 3: Check if PVR IPTV Simple Client is installed
        if not is_pvr_installed():
            dialog = xbmcgui.Dialog()
            result = dialog.yesno(
                'Install PVR IPTV Simple Client?',
                'The PVR IPTV Simple Client addon is required for DVR functionality.\n\n'
                'Would you like to install it now?\n\n'
                '(This will download and install the addon from the Kodi repository)'
            )
            
            if not result:
                return False, "PVR IPTV Simple Client is required for DVR functionality."
            
            # Install the addon
            if not install_pvr_addon():
                return False, "Failed to install PVR IPTV Simple Client. Please install it manually from the Kodi addon repository."
        
        # Step 4: Configure PVR IPTV Simple Client
        progress = xbmcgui.DialogProgress()
        progress.create('Configuring PVR', 'Setting up Frndly TV channels...')
        
        progress.update(25, 'Configuring IPTV Simple Client...')
        success, message = configure_pvr_simple(playlist_url, epg_url)
        
        if not success:
            progress.close()
            return False, message
        
        # Step 5: Enable PVR
        progress.update(50, 'Enabling PVR system...')
        enable_pvr_in_kodi()
        
        # Step 6: Restart PVR to apply changes
        progress.update(75, 'Reloading channels...')
        restart_pvr()
        
        progress.update(100, 'Setup complete!')
        time.sleep(1)
        progress.close()
        
        # Step 7: Show success message with instructions
        dialog = xbmcgui.Dialog()
        dialog.ok(
            'PVR Setup Complete!',
            'Your Frndly TV channels are now available in Kodi\'s Live TV section!\n\n'
            f'Playlist URL: {playlist_url}\n'
            f'EPG URL: {epg_url}\n\n'
            'Please restart Kodi for all changes to take effect.\n\n'
            'You can now access Live TV from the main menu!'
        )
        
        # Ask if user wants to restart Kodi now
        restart = dialog.yesno(
            'Restart Kodi?',
            'Would you like to restart Kodi now to complete the setup?'
        )
        
        if restart:
            xbmc.executebuiltin('RestartApp')
        
        return True, "PVR setup completed successfully!"
        
    except Exception as e:
        xbmc.log(f"[FrndlyTV] Auto PVR setup failed: {e}", xbmc.LOGERROR)
        return False, f"Setup failed: {str(e)}"


def show_pvr_setup_wizard():
    """
    Show the PVR setup wizard with step-by-step guidance
    """
    dialog = xbmcgui.Dialog()
    
    # Welcome screen
    result = dialog.yesno(
        'Frndly TV PVR Setup Wizard',
        'This wizard will automatically set up DVR functionality for Frndly TV.\n\n'
        'The setup will:\n'
        '1. Enable the built-in web server\n'
        '2. Install PVR IPTV Simple Client (if needed)\n'
        '3. Configure your Frndly TV channels\n'
        '4. Set up the TV guide (EPG)\n\n'
        'Would you like to continue?'
    )
    
    if not result:
        return False
    
    # Run automatic setup
    success, message = setup_pvr_automatic()
    
    if not success:
        dialog.ok('Setup Failed', message)
    
    return success


def show_pvr_status():
    """Show current PVR status and configuration"""
    try:
        addon = xbmcaddon.Addon()
        enable_server = addon.getSetting('enable_server') == 'true'
        port = addon.getSetting('server_port') or '8183'
        local_ip = get_local_ip()
        
        pvr_installed = is_pvr_installed()
        pvr_enabled = is_pvr_enabled()
        
        status_lines = ['[B]Frndly TV PVR Status[/B]\n']
        
        # Web server status
        status_lines.append('[B]Web Server:[/B]')
        if enable_server:
            from webserver import is_running
            if is_running():
                status_lines.append('✓ Running on port ' + port)
                status_lines.append(f'  URL: http://{local_ip}:{port}')
            else:
                status_lines.append('✗ Enabled but not running')
                status_lines.append('  Try restarting Kodi')
        else:
            status_lines.append('✗ Disabled')
        
        status_lines.append('')
        
        # PVR addon status
        status_lines.append('[B]PVR IPTV Simple Client:[/B]')
        if pvr_installed:
            status_lines.append('✓ Installed')
            
            pvr_addon = get_pvr_addon()
            if pvr_addon:
                m3u_url = pvr_addon.getSetting('m3uUrl')
                epg_url = pvr_addon.getSetting('epgUrl')
                
                if 'frndlytv' in m3u_url.lower() or local_ip in m3u_url:
                    status_lines.append('✓ Configured for Frndly TV')
                    status_lines.append(f'  Playlist: {m3u_url}')
                    status_lines.append(f'  EPG: {epg_url}')
                else:
                    status_lines.append('⚠ Not configured for Frndly TV')
        else:
            status_lines.append('✗ Not installed')
        
        status_lines.append('')
        
        # PVR system status
        status_lines.append('[B]Kodi PVR System:[/B]')
        if pvr_enabled:
            status_lines.append('✓ Enabled')
        else:
            status_lines.append('✗ Disabled')
        
        status_lines.append('')
        status_lines.append('[B]Quick Actions:[/B]')
        status_lines.append('• Run Setup Wizard - Configure PVR automatically')
        status_lines.append('• View in Live TV - Access Frndly TV channels')
        status_lines.append('• Manual Configuration - Advanced setup')
        
        dialog = xbmcgui.Dialog()
        dialog.textviewer('PVR Status', '\n'.join(status_lines))
        
    except Exception as e:
        xbmcgui.Dialog().ok('Error', f'Failed to show PVR status: {str(e)}')


def generate_manual_instructions():
    """Generate manual setup instructions"""
    try:
        addon = xbmcaddon.Addon()
        port = addon.getSetting('server_port') or '8183'
        local_ip = get_local_ip()
        
        instructions = f'''[B]Manual PVR/DVR Setup Instructions[/B]

[B]Step 1: Enable Web Server[/B]
1. Open Frndly TV addon settings
2. Enable "Enable Web Server"
3. Set port to {port} (or your preferred port)
4. Save settings and restart Kodi

[B]Step 2: Install PVR IPTV Simple Client[/B]
1. Go to Add-ons > Install from repository
2. Select "Kodi Add-on repository"
3. Select "PVR clients"
4. Install "PVR IPTV Simple Client"

[B]Step 3: Configure IPTV Simple Client[/B]
1. Go to Add-ons > My add-ons > PVR clients
2. Select "PVR IPTV Simple Client"
3. Click "Configure"

[B]General Settings:[/B]
- Location: Remote Path (Internet address)
- M3U Playlist URL:
  http://{local_ip}:{port}/playlist.m3u8?gracenote=exclude

[B]EPG Settings:[/B]
- XMLTV URL:
  http://{local_ip}:{port}/epg.xml?gracenote=exclude
- EPG Time Shift: 0

[B]Step 4: Enable PVR in Kodi[/B]
1. Go to Settings > PVR & Live TV
2. Enable "Enable Live TV"
3. Select "Guide" as the startup window (optional)

[B]Step 5: Restart Kodi[/B]
Restart Kodi for all changes to take effect

[B]Step 6: Access Live TV[/B]
- Go to "TV" in the main menu
- Your Frndly TV channels will appear
- Use "Guide" to view the TV schedule
- Right-click on programs to set recordings

[B]URLs for Reference:[/B]
Playlist: http://{local_ip}:{port}/playlist.m3u8?gracenote=exclude
EPG: http://{local_ip}:{port}/epg.xml?gracenote=exclude
Server Status: http://{local_ip}:{port}/
'''
        
        return instructions
        
    except Exception as e:
        return f'Error generating instructions: {str(e)}'


def open_live_tv():
    """Open Kodi's Live TV interface"""
    try:
        xbmc.executebuiltin('ActivateWindow(TVChannels)')
    except:
        xbmcgui.Dialog().ok(
            'Live TV Not Available',
            'Live TV is not available. Please complete the PVR setup first.'
        )


def open_tv_guide():
    """Open Kodi's TV Guide"""
    try:
        xbmc.executebuiltin('ActivateWindow(TVGuide)')
    except:
        xbmcgui.Dialog().ok(
            'TV Guide Not Available',
            'TV Guide is not available. Please complete the PVR setup first.'
        )
