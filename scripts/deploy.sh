#!/bin/bash

# Helper script to trigger deployment after secrets are configured

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     FAQ MCP Server - Docker Hub Deployment Trigger          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check if we're in the right directory
if [ ! -f "faq.py" ]; then
    echo "❌ Error: Please run this script from the faq-mcp-server directory"
    exit 1
fi

echo "📋 Pre-deployment Checklist:"
echo ""
read -p "   Have you created a Docker Hub access token? (y/n): " token_created
if [ "$token_created" != "y" ]; then
    echo ""
    echo "   Please create one at: https://hub.docker.com/settings/security"
    echo "   - Click 'New Access Token'"
    echo "   - Description: 'GitHub Actions - FAQ MCP Server'"
    echo "   - Permissions: Read & Write"
    exit 1
fi

read -p "   Have you configured GitHub secrets (DOCKERHUB_USERNAME & DOCKERHUB_TOKEN)? (y/n): " secrets_configured
if [ "$secrets_configured" != "y" ]; then
    echo ""
    echo "   Please configure them at:"
    echo "   https://github.com/kshitijpandey3h/faq-mcp-server/settings/secrets/actions"
    echo ""
    echo "   Add these two secrets:"
    echo "   1. DOCKERHUB_USERNAME = vicharanashala"
    echo "   2. DOCKERHUB_TOKEN = <your Docker Hub access token>"
    exit 1
fi

echo ""
echo "✅ Prerequisites confirmed!"
echo ""

# Ask for version number
read -p "Enter version number (e.g., 1.0.0): " version

if [ -z "$version" ]; then
    echo "❌ Error: Version number cannot be empty"
    exit 1
fi

# Validate version format
if ! [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "❌ Error: Version must be in format X.Y.Z (e.g., 1.0.0)"
    exit 1
fi

tag="v$version"

echo ""
echo "🏷️  Creating and pushing tag: $tag"
echo ""

# Create and push tag
git tag "$tag"
git push origin "$tag"

echo ""
echo "✅ Tag pushed successfully!"
echo ""
echo "📊 Monitor the deployment:"
echo "   https://github.com/kshitijpandey3h/faq-mcp-server/actions"
echo ""
echo "⏱️  Build will take approximately 5-10 minutes"
echo ""
echo "After completion, verify at:"
echo "   https://hub.docker.com/r/kshitijpandey3h/faq-mcp-server"
echo ""
