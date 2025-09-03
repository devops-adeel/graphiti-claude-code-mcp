#!/bin/bash

# Script to create GitHub release with "The AI That Never Forgets" video
# Requires: GitHub CLI (gh) - install with: brew install gh

set -e

echo "📦 Creating GitHub Release with Video Documentation"
echo ""

# Check if gh is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is not installed"
    echo "📦 Install with: brew install gh"
    echo "🔐 Then authenticate with: gh auth login"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Not authenticated with GitHub"
    echo "🔐 Run: gh auth login"
    exit 1
fi

# Check if video file exists
if [ ! -f "The_AI_That_Never_Forgets.mp4" ]; then
    echo "❌ Video file 'The_AI_That_Never_Forgets.mp4' not found"
    exit 1
fi

# Get the latest tag or suggest next version
LATEST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
echo "📌 Latest tag: $LATEST_TAG"

# Suggest next version
if [[ $LATEST_TAG =~ ^v([0-9]+)\.([0-9]+)\.([0-9]+) ]]; then
    MAJOR=${BASH_REMATCH[1]}
    MINOR=${BASH_REMATCH[2]}
    PATCH=${BASH_REMATCH[3]}

    # Increment minor version for feature addition
    NEXT_MINOR=$((MINOR + 1))
    SUGGESTED_TAG="v${MAJOR}.${NEXT_MINOR}.0"
else
    SUGGESTED_TAG="v3.3.0"
fi

echo "💡 Suggested version: $SUGGESTED_TAG (feature release)"
echo ""
echo "Enter release version (or press Enter for $SUGGESTED_TAG):"
read -r RELEASE_VERSION

if [ -z "$RELEASE_VERSION" ]; then
    RELEASE_VERSION=$SUGGESTED_TAG
fi

# Create release notes
RELEASE_NOTES=$(cat <<EOF
## 🎬 Conceptual Video: The AI That Never Forgets

This release includes our comprehensive conceptual overview video explaining how Graphiti creates persistent AI memory across sessions.

### Video Details
- **Duration**: 5:38
- **Format**: Conceptual Animation
- **Key Moment**: "One Mind" concept at 4:03

### What's Included
- 📹 **Full Video**: The_AI_That_Never_Forgets.mp4
- 📄 **Transcript**: Available at \`docs/video-transcripts/the-ai-that-never-forgets.md\`
- 🖼️ **Thumbnails**: Multiple resolutions in \`docs/assets/images/\`
- 🎞️ **GIF Teaser**: Animated preview in README

### How to Watch
1. **Download**: Click on "The_AI_That_Never_Forgets.mp4" below
2. **Stream**: Use the direct link in your browser
3. **Accessibility**: Full transcript with timestamps available

### Integration Points
The video has been integrated into our documentation at multiple touchpoints:
- README: Progressive disclosure with GIF teaser
- Quick Start: Developer-focused sections (2:30-4:00)
- Documentation: Research-oriented full analysis
- Memory Philosophy: Linked for visual learners

### Engagement Tracking
We have implemented Graphiti-based engagement tracking to learn from how users interact with this video documentation. See scripts/track_video_engagement.py for details.

---
*For the best experience, watch the video in full screen with audio enabled.*
EOF
)

echo "📝 Release notes prepared"
echo ""
echo "Creating release $RELEASE_VERSION..."

# Create the release with the video file
gh release create "$RELEASE_VERSION" \
    --title "🧠 $RELEASE_VERSION: The AI That Never Forgets" \
    --notes "$RELEASE_NOTES" \
    --draft \
    "The_AI_That_Never_Forgets.mp4#The AI That Never Forgets - Conceptual Overview (MP4)"

echo ""
echo "✅ Draft release created successfully!"
echo ""
echo "📎 Next steps:"
echo "  1. Review the draft release at: https://github.com/$(gh repo view --json nameWithOwner -q .nameWithOwner)/releases"
echo "  2. Edit if needed, then publish when ready"
echo "  3. Update README.md to replace placeholder username with actual GitHub username"
echo "  4. Test video links with: make test-video-links"
echo ""
echo "🔗 The video will be available at:"
echo "   https://github.com/$(gh repo view --json nameWithOwner -q .nameWithOwner)/releases/download/$RELEASE_VERSION/The_AI_That_Never_Forgets.mp4"
