OCS PWA Icon Pack (transparent/maskable-friendly)

Files:
- icon-192-maskable.png
- icon-512-maskable.png
- apple-touch-icon.png
- favicon-16.png
- favicon-32.png
- favicon.ico
- icon-1024.png (extra, for stores or future use)

Placement (Flask):
- Put all PNG/ICO files into: static/icons/
  e.g., static/icons/icon-192-maskable.png

Manifest snippet:
{
  "icons": [
    {"src": "/static/icons/icon-192-maskable.png", "sizes": "192x192", "type": "image/png", "purpose": "maskable any"},
    {"src": "/static/icons/icon-512-maskable.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable any"}
  ]
}

Head snippet:
<link rel="apple-touch-icon" href="{{ url_for('static', filename='icons/apple-touch-icon.png') }}">
<link rel="icon" type="image/png" sizes="32x32" href="{{ url_for('static', filename='icons/favicon-32.png') }}">
<link rel="icon" type="image/png" sizes="16x16" href="{{ url_for('static', filename='icons/favicon-16.png') }}">
<link rel="icon" href="{{ url_for('static', filename='icons/favicon.ico') }}">

Service worker: unchanged.

Notes:
- These icons are transparent so they adapt to OS shapes (maskable).
- The 1024px image is a master source for future exports.
