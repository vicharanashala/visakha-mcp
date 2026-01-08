# GitHub Actions Setup Guide

## Overview

This guide walks you through setting up automated Docker Hub deployment for the FAQ MCP Server using GitHub Actions.

## Prerequisites

- GitHub repository: `vicharanashala/faq-mcp-server`
- Docker Hub account
- Docker Hub repository created: `vicharanashala/faq-mcp-server`

## Step 1: Create Docker Hub Access Token

1. Go to [Docker Hub Security Settings](https://hub.docker.com/settings/security)
2. Click **New Access Token**
3. Enter a description (e.g., "GitHub Actions - FAQ MCP Server")
4. Set permissions to **Read & Write**
5. Click **Generate**
6. **Copy the token immediately** (you won't be able to see it again)

## Step 2: Configure GitHub Secrets

1. Navigate to your GitHub repository
2. Go to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add the following secrets:

### DOCKERHUB_USERNAME
- **Name**: `DOCKERHUB_USERNAME`
- **Value**: Your Docker Hub username (e.g., `vicharanashala`)

### DOCKERHUB_TOKEN
- **Name**: `DOCKERHUB_TOKEN`
- **Value**: The access token you generated in Step 1

## Step 3: Push Workflow to GitHub

The workflow file has been created at `.github/workflows/docker-publish.yml`. Push it to your repository:

```bash
cd /home/ubuntu/Kshitij/Chat-bot/faq-mcp-server

# Add the workflow file
git add .github/workflows/docker-publish.yml

# Add updated README
git add README.md

# Commit the changes
git commit -m "Add GitHub Actions workflow for Docker Hub deployment"

# Push to GitHub
git push origin main
```

## Step 4: Trigger Your First Build

### Option A: Tag-based Release (Recommended)

```bash
# Create a version tag
git tag v1.0.0

# Push the tag to trigger the workflow
git push origin v1.0.0
```

### Option B: Manual Trigger

1. Go to your GitHub repository
2. Click on the **Actions** tab
3. Select **Docker Hub Publish** workflow
4. Click **Run workflow** button
5. Select the branch (usually `main`)
6. Click **Run workflow**

## Step 5: Monitor the Build

1. Go to the **Actions** tab in your GitHub repository
2. Click on the running workflow
3. Watch the build progress in real-time
4. Verify all steps complete successfully

## Step 6: Verify Deployment

### Check Docker Hub

1. Go to [Docker Hub](https://hub.docker.com)
2. Navigate to your repository: `vicharanashala/faq-mcp-server`
3. Verify the new image tags appear:
   - `latest`
   - `1.0.0` (or your version)
   - `main-<git-sha>`

### Test the Image

```bash
# Pull the image
docker pull vicharanashala/faq-mcp-server:latest

# Verify multi-platform support
docker buildx imagetools inspect vicharanashala/faq-mcp-server:latest

# Run the container
docker run -d \
  --name faq-mcp-test \
  -p 9010:9010 \
  -e MONGODB_URI="your-mongodb-uri" \
  vicharanashala/faq-mcp-server:latest

# Check logs
docker logs faq-mcp-test -f

# Clean up
docker stop faq-mcp-test
docker rm faq-mcp-test
```

## Troubleshooting

### Build Fails with Authentication Error

**Problem**: `Error: Cannot perform an interactive login from a non TTY device`

**Solution**: 
- Verify `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets are correctly set
- Ensure the Docker Hub token has Read & Write permissions
- Regenerate the token if needed

### Workflow Doesn't Trigger on Tag

**Problem**: Pushing a tag doesn't trigger the workflow

**Solution**:
- Ensure the tag follows the pattern `v*.*.*` (e.g., `v1.0.0`)
- Check that the workflow file is on the `main` branch
- Verify the workflow file syntax is correct

### Multi-platform Build Takes Too Long

**Problem**: Build times exceed 10 minutes

**Solution**:
- This is normal for the first build
- Subsequent builds will be faster due to layer caching
- Consider building only `linux/amd64` if ARM support isn't needed

### Image Not Appearing on Docker Hub

**Problem**: Build succeeds but image doesn't appear

**Solution**:
- Check the Docker Hub repository name matches: `vicharanashala/faq-mcp-server`
- Verify the repository exists and is public (or you have access)
- Check the workflow logs for push errors

## Regular Deployment Workflow

### For New Releases

1. Make your code changes
2. Commit and push to `main`
3. Create and push a version tag:
   ```bash
   git tag v1.1.0
   git push origin v1.1.0
   ```
4. Monitor the GitHub Actions workflow
5. Verify the new version on Docker Hub

### Semantic Versioning

Follow [Semantic Versioning](https://semver.org/):
- **MAJOR** version (v2.0.0): Incompatible API changes
- **MINOR** version (v1.1.0): New functionality, backwards compatible
- **PATCH** version (v1.0.1): Bug fixes, backwards compatible

## Security Best Practices

1. **Never commit secrets** to the repository
2. **Rotate tokens** periodically (every 6-12 months)
3. **Use minimal permissions** for Docker Hub tokens
4. **Review workflow logs** for sensitive information before sharing
5. **Enable 2FA** on your Docker Hub account

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Build Push Action](https://github.com/docker/build-push-action)
- [Docker Hub Documentation](https://docs.docker.com/docker-hub/)
- [Semantic Versioning](https://semver.org/)
