#!/usr/bin/env python3
"""
Helper script to update OAuth2 configurations with ngrok URL
"""
import os
import json
import requests
import sys
from urllib.parse import urlparse

def get_ngrok_url():
    """Get the current ngrok public URL"""
    try:
        response = requests.get("http://localhost:4040/api/tunnels")
        data = response.json()
        
        for tunnel in data['tunnels']:
            if tunnel['proto'] == 'https':
                return tunnel['public_url']
        
        return None
    except Exception as e:
        print(f"Error getting ngrok URL: {e}")
        return None

def update_env_file(ngrok_url):
    """Update .env file with ngrok URL"""
    env_file = ".env"
    
    if not os.path.exists(env_file):
        print("❌ .env file not found!")
        return False
    
    # Read current .env file
    with open(env_file, 'r') as f:
        lines = f.readlines()
    
    # Update BACKEND_URL
    updated = False
    for i, line in enumerate(lines):
        if line.startswith('BACKEND_URL='):
            lines[i] = f"BACKEND_URL={ngrok_url}\n"
            updated = True
            break
    
    # Add BACKEND_URL if not found
    if not updated:
        lines.append(f"BACKEND_URL={ngrok_url}\n")
    
    # Write back to file
    with open(env_file, 'w') as f:
        f.writelines(lines)
    
    return True

def generate_oauth_config(ngrok_url):
    """Generate OAuth2 provider configuration"""
    base_url = ngrok_url.rstrip('/')
    
    config = {
        "google": {
            "client_id": "YOUR_GOOGLE_CLIENT_ID",
            "client_secret": "YOUR_GOOGLE_CLIENT_SECRET",
            "redirect_uri": f"{base_url}/api/v1/auth/google/callback",
            "console_url": "https://console.developers.google.com/",
            "setup_instructions": [
                "1. Go to Google Cloud Console",
                "2. Create or select a project",
                "3. Enable Google+ API",
                "4. Create OAuth 2.0 credentials",
                f"5. Add '{base_url}/api/v1/auth/google/callback' to Authorized redirect URIs",
                "6. Copy Client ID and Client Secret to your .env file"
            ]
        },
        "github": {
            "client_id": "YOUR_GITHUB_CLIENT_ID", 
            "client_secret": "YOUR_GITHUB_CLIENT_SECRET",
            "redirect_uri": f"{base_url}/api/v1/auth/github/callback",
            "console_url": "https://github.com/settings/applications/new",
            "setup_instructions": [
                "1. Go to GitHub Developer Settings",
                "2. Click 'New OAuth App'",
                "3. Fill in application details:",
                f"   - Homepage URL: {base_url}",
                f"   - Authorization callback URL: {base_url}/api/v1/auth/github/callback",
                "4. Register application",
                "5. Copy Client ID and Client Secret to your .env file"
            ]
        }
    }
    
    return config

def print_setup_instructions(ngrok_url):
    """Print setup instructions for OAuth2 providers"""
    config = generate_oauth_config(ngrok_url)
    
    print("🔧 OAuth2 Provider Setup Instructions")
    print("=" * 50)
    
    for provider, settings in config.items():
        print(f"\n📱 {provider.upper()} OAUTH2 SETUP:")
        print(f"Console URL: {settings['console_url']}")
        print(f"Callback URL: {settings['redirect_uri']}")
        print("\nSteps:")
        for instruction in settings['setup_instructions']:
            print(f"  {instruction}")
    
    print(f"\n✅ Your ngrok URL: {ngrok_url}")
    print(f"📄 API Documentation: {ngrok_url}/docs")
    print(f"🔍 Test Endpoints:")
    print(f"   - Google Login: {ngrok_url}/api/v1/auth/google/login")
    print(f"   - GitHub Login: {ngrok_url}/api/v1/auth/github/login")

def save_config_file(ngrok_url):
    """Save OAuth2 configuration to a JSON file"""
    config = generate_oauth_config(ngrok_url)
    
    with open('oauth2-config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"💾 OAuth2 configuration saved to oauth2-config.json")

def main():
    print("🔧 OAuth2 Configuration Helper")
    print("=" * 40)
    
    # Check if ngrok is running
    ngrok_url = get_ngrok_url()
    
    if not ngrok_url:
        print("❌ Ngrok tunnel not found!")
        print("💡 Please start ngrok first: ./start-ngrok.sh")
        sys.exit(1)
    
    print(f"✅ Found ngrok URL: {ngrok_url}")
    
    # Update .env file
    if update_env_file(ngrok_url):
        print("✅ Updated .env file with ngrok URL")
    else:
        print("❌ Failed to update .env file")
    
    # Save configuration
    save_config_file(ngrok_url)
    
    # Print setup instructions
    print_setup_instructions(ngrok_url)
    
    print(f"\n🚀 Next steps:")
    print("1. Configure OAuth2 providers using the URLs above")
    print("2. Update your .env file with the client IDs and secrets")
    print("3. Restart your FastAPI server to use the new configuration")
    print("4. Test the OAuth2 flow!")

if __name__ == "__main__":
    main()