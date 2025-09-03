#!/bin/bash

# Test script to verify video documentation integration
# Checks that all assets exist and links are properly configured

set -e

echo "🧪 Testing Video Documentation Integration"
echo "=========================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
WARNINGS=0

# Test function
test_file() {
    local file=$1
    local description=$2

    if [ -f "$file" ]; then
        echo -e "${GREEN}✅${NC} $description exists"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}❌${NC} $description missing: $file"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Test directory function
test_dir() {
    local dir=$1
    local description=$2

    if [ -d "$dir" ]; then
        echo -e "${GREEN}✅${NC} $description exists"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}❌${NC} $description missing: $dir"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Test file size
test_file_size() {
    local file=$1
    local min_size=$2
    local description=$3

    if [ -f "$file" ]; then
        size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
        if [ "$size" -gt "$min_size" ]; then
            echo -e "${GREEN}✅${NC} $description ($(( size / 1024 ))KB)"
            ((TESTS_PASSED++))
            return 0
        else
            echo -e "${YELLOW}⚠️${NC} $description exists but seems small ($(( size / 1024 ))KB)"
            ((WARNINGS++))
            return 1
        fi
    else
        echo -e "${RED}❌${NC} $description missing"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Check README contains video references
test_readme_content() {
    local pattern=$1
    local description=$2

    if grep -q "$pattern" README.md 2>/dev/null; then
        echo -e "${GREEN}✅${NC} README contains $description"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}❌${NC} README missing $description"
        ((TESTS_FAILED++))
        return 1
    fi
}

echo "1️⃣  Testing Directory Structure"
echo "---------------------------------"
test_dir "docs/assets/images" "Image assets directory"
test_dir "docs/video-transcripts" "Transcript directory"
test_dir "scripts" "Scripts directory"
echo ""

echo "2️⃣  Testing Video Assets"
echo "------------------------"
test_file_size "docs/assets/images/one-mind-thumbnail.png" 10000 "Main thumbnail"
test_file_size "docs/assets/images/one-mind-teaser.gif" 50000 "Animated GIF teaser"
test_file "docs/assets/images/one-mind-thumbnail-small.png" "Small thumbnail (360p)"
test_file "docs/assets/images/one-mind-thumbnail-large.png" "Large thumbnail (1280p)"
echo ""

echo "3️⃣  Testing Documentation Files"
echo "--------------------------------"
test_file "docs/video-transcripts/the-ai-that-never-forgets.md" "Video transcript"
test_file "scripts/extract-video-assets.sh" "Asset extraction script"
test_file "scripts/track_video_engagement.py" "Engagement tracking script"
test_file "scripts/create-video-release.sh" "Release creation script"
echo ""

echo "4️⃣  Testing README Integration"
echo "-------------------------------"
test_readme_content "one-mind-teaser.gif" "GIF teaser"
test_readme_content "Watch the Full Concept Video" "Video section"
test_readme_content "Read Transcript" "Transcript link"
test_readme_content "For Engineering Leaders" "CTO touchpoint"
test_readme_content "For Developers" "Developer touchpoint"
test_readme_content "For Researchers" "Researcher touchpoint"
echo ""

echo "5️⃣  Testing File Permissions"
echo "-----------------------------"
if [ -x "scripts/extract-video-assets.sh" ]; then
    echo -e "${GREEN}✅${NC} extract-video-assets.sh is executable"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌${NC} extract-video-assets.sh is not executable"
    ((TESTS_FAILED++))
fi

if [ -x "scripts/create-video-release.sh" ]; then
    echo -e "${GREEN}✅${NC} create-video-release.sh is executable"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌${NC} create-video-release.sh is not executable"
    ((TESTS_FAILED++))
fi
echo ""

echo "6️⃣  Testing Transcript Quality"
echo "------------------------------"
if grep -q "\[00:00\]" docs/video-transcripts/the-ai-that-never-forgets.md 2>/dev/null; then
    echo -e "${GREEN}✅${NC} Transcript has timestamps"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌${NC} Transcript missing timestamps"
    ((TESTS_FAILED++))
fi

if grep -q "04:03" docs/video-transcripts/the-ai-that-never-forgets.md 2>/dev/null; then
    echo -e "${GREEN}✅${NC} Transcript includes 'One Mind' timestamp"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌${NC} Transcript missing key timestamp"
    ((TESTS_FAILED++))
fi

if grep -q "Visual:" docs/video-transcripts/the-ai-that-never-forgets.md 2>/dev/null; then
    echo -e "${GREEN}✅${NC} Transcript includes visual descriptions"
    ((TESTS_PASSED++))
else
    echo -e "${YELLOW}⚠️${NC} Transcript might lack visual descriptions"
    ((WARNINGS++))
fi
echo ""

echo "7️⃣  Testing Memory Philosophy Integration"
echo "-----------------------------------------"
if grep -q "Visual Learner" docs/explanation/memory-philosophy.md 2>/dev/null; then
    echo -e "${GREEN}✅${NC} Memory philosophy links to video"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌${NC} Memory philosophy missing video link"
    ((TESTS_FAILED++))
fi
echo ""

echo "8️⃣  Checking for Common Issues"
echo "-------------------------------"
if grep -q "placeholder-username" README.md 2>/dev/null; then
    echo -e "${YELLOW}⚠️${NC} README still contains placeholder username"
    ((WARNINGS++))
else
    echo -e "${GREEN}✅${NC} No placeholder usernames found"
    ((TESTS_PASSED++))
fi

if [ -f "The_AI_That_Never_Forgets.mp4" ]; then
    echo -e "${YELLOW}⚠️${NC} Video file still in root directory (should be in GitHub Release)"
    ((WARNINGS++))
else
    echo -e "${GREEN}✅${NC} Video file not in root (good for repository size)"
    ((TESTS_PASSED++))
fi
echo ""

echo "=========================================="
echo "📊 Test Results Summary"
echo "=========================================="
echo -e "${GREEN}Passed:${NC} $TESTS_PASSED"
echo -e "${RED}Failed:${NC} $TESTS_FAILED"
echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All critical tests passed!${NC}"
    echo ""
    echo "✅ Ready to create GitHub Release with:"
    echo "   ./scripts/create-video-release.sh"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Please fix issues before proceeding.${NC}"
    exit 1
fi
