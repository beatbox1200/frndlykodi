# Frndly TV for Kodi

**Version 1.0.0** | Developed by **Marcus Montgomery / BeatTLF Entertainment**

![Frndly TV for Kodi](resources/icon.png)

## What Is This Add-on?

**Frndly TV for Kodi** is a video streaming add-on that allows you to watch live television channels from your Frndly TV subscription directly within Kodi. This add-on eliminates the need for Docker containers, external servers, or additional hardware - everything runs directly on your device.

Whether you're using a Fire TV Stick, Android TV box, Windows PC, Mac, or any other Kodi-supported device, you can enjoy your Frndly TV channels without any complicated setup.

## Features

### Live TV Streaming
- Stream all your Frndly TV channels in real-time
- High-quality HLS streaming
- Works on all Kodi-supported devices

### Full EPG Support
- Complete Electronic Program Guide with detailed show information
- **Episode Thumbnails** - Visual previews for programs
- **Episode Titles & Info** - Season/episode numbers, descriptions
- **TV Parental Guidelines Ratings** - TV-Y, TV-G, TV-PG, TV-14, TV-MA
- **Movie Ratings** - G, PG, PG-13, R, NC-17
- **Now Playing & Next Up** - See what's on and what's coming next
- **Year, Genre, Cast** - Full metadata for all programs

### Channel Presentation
- **Channel Logos** - Official high-quality logos for all channels
- **Channel Numbers** - Proper numbering system
- **Current Show Info** - Hover over any channel to see detailed information

### PVR/DVR Integration
- Recording capability through Kodi's PVR system
- Full metadata support for recordings
- Integration with PVR IPTV Simple Client

### Built-in Web Server
- Optional server for IPTV client integration
- M3U playlist generation with channel logos
- XMLTV EPG with full metadata (ratings, thumbnails, episode info)
- Compatible with:
  - Channels DVR
  - TiviMate
  - IPTV Smarters
  - Perfect Player
  - Any M3U-compatible player

### Self-Contained Operation
- No Docker required
- No external server needed
- No separate computer required
- Everything runs on your device

## Requirements

- Kodi 19 (Matrix) or later
- Active Frndly TV subscription
- Internet connection

## Installation

### Method 1: Install from ZIP file

1. Download the `plugin.video.frndlytv.zip` file
2. In Kodi, go to **Add-ons** → **Install from zip file**
3. Navigate to and select the downloaded ZIP file
4. Wait for the "Add-on installed" notification

### Method 2: Manual Installation

1. Extract the `plugin.video.frndlytv` folder
2. Copy it to your Kodi addons directory:
   - **Windows**: `%APPDATA%\Kodi\addons\`
   - **Linux**: `~/.kodi/addons/`
   - **macOS**: `~/Library/Application Support/Kodi/addons/`
   - **Android/Fire TV**: `/sdcard/Android/data/org.xbmc.kodi/files/.kodi/addons/`
3. Restart Kodi

## Setup

1. Open the addon from **Add-ons** → **Video add-ons** → **Frndly TV**
2. Go to **Settings** and enter your Frndly TV email and password
3. Click OK and enjoy!

## Using the Built-in Web Server

### Enable the Server

1. Open addon **Settings**
2. Enable "Enable Built-in Web Server"
3. Set your preferred port (default: 8183)
4. Restart Kodi or the addon

### Access URLs

Once enabled, access the status page at `http://YOUR_DEVICE_IP:8183/`

**For Channels DVR / IPTV Clients:**

| Purpose | URL |
|---------|-----|
| Status Page | `http://YOUR_IP:8183/` |
| Playlist (Gracenote EPG) | `http://YOUR_IP:8183/playlist.m3u8?gracenote=include` |
| Playlist (Built-in EPG) | `http://YOUR_IP:8183/playlist.m3u8?gracenote=exclude` |
| EPG/XMLTV | `http://YOUR_IP:8183/epg.xml` |

### Playlist Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `start_chno` | Start channel numbering from N | `?start_chno=100` |
| `include` | Only include specific channel IDs | `?include=frndly-1,frndly-2` |
| `exclude` | Exclude specific channel IDs | `?exclude=frndly-10` |
| `gracenote` | Filter by Gracenote availability | `?gracenote=include` or `exclude` |
| `days` | EPG days to include (1-7) | `?days=5` |

## EPG Data Included

The enhanced EPG provides:

- **Program Title** - Main show/movie title
- **Episode Title** - Subtitle for episodes
- **Description** - Full program description
- **Season/Episode** - S01E05 format and XMLTV standard
- **Rating** - TV Parental Guidelines (TV-Y, TV-G, TV-PG, TV-14, TV-MA)
- **Year** - Release/air year
- **Genre** - Program categories
- **Thumbnails** - Program artwork
- **New/Premiere/Finale** - Special episode markers
- **Cast & Crew** - Actors and directors

## Troubleshooting

### No Channels Showing
- Verify your Frndly TV subscription is active
- Check your credentials in addon settings
- Frndly TV may not be available in your region

### Streams Not Playing
- Try disabling "Use InputStream Adaptive" in settings
- Check your internet connection
- Ensure inputstream.adaptive addon is installed

### Settings Empty
- Ensure you're using Kodi 19 or later
- Try reinstalling the addon

### Web Server Not Working
- Check if the port isn't blocked by your firewall
- Try a different port in settings
- Restart Kodi after enabling

## Credits

**Developed by:** Marcus Montgomery / BeatTLF Entertainment

**Based on:** [frndlytv-for-channels](https://github.com/matthuisman/frndlytv-for-channels) by Matt Huisman

## Version History

### v1.0.0 (January 2025)
**NEW FEATURES:**
- Initial public release
- Direct Frndly TV API integration for live streaming
- Full EPG with show info, ratings, thumbnails, and episode details
- PVR/DVR recording support with metadata
- Built-in web server for external IPTV clients
- Fire TV and Android TV optimized
- Channel logos and numbering system
- TV Parental Guidelines ratings display
- Auto session management and keep-alive

## Disclaimer

This add-on is not affiliated with or endorsed by Frndly TV. You must have a valid Frndly TV subscription to use this add-on. Use at your own risk.

## License

MIT License - See LICENSE file for details.
