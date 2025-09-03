#!/bin/bash

# Script to extract video assets for "The AI That Never Forgets" documentation
# Requires: ffmpeg (install with: brew install ffmpeg)

set -e

echo "🎬 Extracting video assets for documentation..."

# Check if ffmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ ffmpeg is not installed"
    echo "📦 Install with: brew install ffmpeg"
    exit 1
fi

# Check if video file exists
if [ ! -f "The_AI_That_Never_Forgets.mp4" ]; then
    echo "❌ Video file 'The_AI_That_Never_Forgets.mp4' not found in current directory"
    exit 1
fi

# Create directories if they don't exist
mkdir -p docs/assets/images

echo "📸 Extracting 'One Mind' frame at 4:03..."
ffmpeg -i The_AI_That_Never_Forgets.mp4 \
    -ss 00:04:03 \
    -vframes 1 \
    -q:v 2 \
    docs/assets/images/one-mind-thumbnail.png \
    -y -loglevel error

echo "🎞️ Creating animated GIF teaser (4:01-4:06)..."
ffmpeg -i The_AI_That_Never_Forgets.mp4 \
    -ss 00:04:01 \
    -t 5 \
    -vf "fps=10,scale=640:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" \
    -loop 0 \
    docs/assets/images/one-mind-teaser.gif \
    -y -loglevel error

# Optional: Create multiple resolution thumbnails
echo "🖼️ Creating responsive thumbnails..."
ffmpeg -i docs/assets/images/one-mind-thumbnail.png \
    -vf "scale=360:-1" \
    docs/assets/images/one-mind-thumbnail-small.png \
    -y -loglevel error

ffmpeg -i docs/assets/images/one-mind-thumbnail.png \
    -vf "scale=1280:-1" \
    docs/assets/images/one-mind-thumbnail-large.png \
    -y -loglevel error

echo "✅ Video assets extracted successfully!"
echo ""
echo "📁 Created files:"
echo "  - docs/assets/images/one-mind-thumbnail.png (main thumbnail)"
echo "  - docs/assets/images/one-mind-teaser.gif (animated teaser)"
echo "  - docs/assets/images/one-mind-thumbnail-small.png (360p)"
echo "  - docs/assets/images/one-mind-thumbnail-large.png (1280p)"
echo ""
echo "💡 Next step: Run 'make test' to verify all assets are properly linked"
