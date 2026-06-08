# Deployment Plan

## Recommended target
Use Docker + Streamlit. This keeps the app portable and makes it easy to deploy to:
- Azure Container Apps
- Render
- Railway
- Streamlit Community Cloud

## What needs to be set
Environment variables:
- `Github_token` or `GITHUB_TOKEN`

Application files already included:
- `streamlit_app.py`
- `Dockerfile`

## Deployment steps
1. Build locally with Docker.
2. Verify the Streamlit app starts and can load the cached schema.
3. Push the image to a registry if the target needs one.
4. Deploy the container to the chosen platform.
5. Configure the model token as a secret or app setting.

## Best first deployment option
If you want the fastest shareable demo, deploy the Streamlit app first.

If you want the most production-like path, deploy the container to Azure Container Apps.
