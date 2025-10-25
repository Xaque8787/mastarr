# Blueprint Images

This directory contains images for app blueprints displayed in the UI.

## Structure

```
static/images/
├── jellyfin.png          # Jellyfin app icon
├── placeholder.png       # Fallback for missing icons
└── README.md            # This file
```

## Adding New Blueprint Images

When creating a new blueprint, add its image here:

1. **Create/download the image** (PNG format recommended, 200x200px ideal)
2. **Name it** to match the blueprint name: `{blueprint_name}.png`
3. **Place it** in `static/images/`
4. **Reference it** in the blueprint JSON:
   ```json
   {
     "icon_url": "/static/images/myapp.png"
   }
   ```

## Image Guidelines

- **Format**: PNG (supports transparency)
- **Size**: 200x200px recommended
- **File size**: Keep under 100KB for fast loading
- **Naming**: Use lowercase, match blueprint name

## Examples

- `jellyfin.png` → Jellyfin app
- `radarr.png` → Radarr app
- `sonarr.png` → Sonarr app
- `prowlarr.png` → Prowlarr app

## Fallback

If an image is missing, the UI will use `placeholder.png` or show a default icon.

## Creating Placeholder Images

Need to create placeholder images? Run:

```bash
docker exec -it mastarr python3 create_placeholders.py
```

This will generate 1x1 transparent PNG files for jellyfin.png and placeholder.png.

## Important Notes

- Images are served at `/static/images/{filename}`
- FastAPI mounts the `static/` directory automatically
- Changes to images don't require restarting the app (just refresh browser)
