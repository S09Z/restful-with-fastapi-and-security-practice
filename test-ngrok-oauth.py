#!/usr/bin/env python3
"""
Test script for OAuth2 flow with ngrok
"""
import asyncio
import json
import requests
import webbrowser
from datetime import datetime

def get_ngrok_url():
    """Get the current ngrok public URL"""
    try:
        response = requests.get("http://localhost:4040/api/tunnels", timeout=5)
        data = response.json()
        
        for tunnel in data['tunnels']:
            if tunnel['proto'] == 'https':
                return tunnel['public_url']
        
        return None
    except Exception as e:
        print(f"Error getting ngrok URL: {e}")
        return None

def test_api_endpoints(base_url):
    """Test basic API endpoints"""
    print(f"🧪 Testing API endpoints...")
    
    endpoints = [
        "/",
        "/docs",
        "/api/v1/auth/google/login",
        "/api/v1/auth/github/login"
    ]
    
    results = {}
    
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        try:
            response = requests.get(url, allow_redirects=False, timeout=10)
            results[endpoint] = {
                "status": response.status_code,
                "success": response.status_code in [200, 307, 302]
            }
            
            if endpoint == "/":
                try:
                    data = response.json()
                    print(f"✅ Root endpoint: {data.get('message', 'OK')}")
                except:
                    pass
        except Exception as e:
            results[endpoint] = {
                "status": "error",
                "error": str(e),
                "success": False
            }
    
    return results

def test_oauth_redirect(base_url, provider="google"):
    """Test OAuth2 redirect"""
    print(f"🔐 Testing {provider} OAuth2 redirect...")
    
    url = f"{base_url}/api/v1/auth/{provider}/login"
    
    try:
        response = requests.get(url, allow_redirects=False, timeout=10)
        
        if response.status_code in [302, 307]:
            redirect_url = response.headers.get('location', '')
            print(f"✅ OAuth2 redirect working: {redirect_url[:50]}...")
            return True, redirect_url
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            return False, None
    except Exception as e:
        print(f"❌ OAuth2 redirect failed: {e}")
        return False, None

def print_test_results(results, ngrok_url):
    """Print formatted test results"""
    print("\n📊 API Test Results:")
    print("=" * 50)
    
    for endpoint, result in results.items():
        status = "✅" if result['success'] else "❌"
        status_code = result.get('status', 'unknown')
        print(f"{status} {endpoint}: {status_code}")
        
        if 'error' in result:
            print(f"    Error: {result['error']}")
    
    print(f"\n🌐 Ngrok URLs:")
    print(f"   Public URL:    {ngrok_url}")
    print(f"   Local URL:     http://localhost:8000")
    print(f"   Ngrok Dashboard: http://localhost:4040")
    
    print(f"\n🔗 Quick Links:")
    print(f"   API Docs:      {ngrok_url}/docs")
    print(f"   Google Login:  {ngrok_url}/api/v1/auth/google/login")
    print(f"   GitHub Login:  {ngrok_url}/api/v1/auth/github/login")

def interactive_oauth_test(ngrok_url):
    """Interactive OAuth2 test"""
    print(f"\n🧪 Interactive OAuth2 Test")
    print("=" * 40)
    
    providers = ["google", "github"]
    
    for provider in providers:
        answer = input(f"\nTest {provider.upper()} OAuth2? (y/n): ").lower()
        
        if answer == 'y':
            success, redirect_url = test_oauth_redirect(ngrok_url, provider)
            
            if success:
                open_browser = input(f"Open {provider} login in browser? (y/n): ").lower()
                if open_browser == 'y':
                    login_url = f"{ngrok_url}/api/v1/auth/{provider}/login"
                    print(f"🌐 Opening: {login_url}")
                    webbrowser.open(login_url)
                    print(f"💡 Complete the OAuth2 flow in your browser")
                    print(f"   You should be redirected back to: {ngrok_url}/api/v1/auth/{provider}/callback")

def check_oauth_config():
    """Check OAuth2 configuration"""
    print("⚙️  Checking OAuth2 configuration...")
    
    try:
        with open('.env', 'r') as f:
            env_content = f.read()
        
        google_configured = 'GOOGLE_CLIENT_ID' in env_content and 'your_google_client_id' not in env_content
        github_configured = 'GITHUB_CLIENT_ID' in env_content and 'your_github_client_id' not in env_content
        
        print(f"   Google OAuth2: {'✅ Configured' if google_configured else '❌ Not configured'}")
        print(f"   GitHub OAuth2: {'✅ Configured' if github_configured else '❌ Not configured'}")
        
        if not google_configured or not github_configured:
            print(f"\n💡 To configure OAuth2 providers:")
            print(f"   1. Run: python update-oauth-config.py")
            print(f"   2. Follow the setup instructions")
            print(f"   3. Update your .env file with client IDs and secrets")
        
        return google_configured, github_configured
    
    except FileNotFoundError:
        print("❌ .env file not found")
        return False, False

def main():
    print("🚀 Ngrok OAuth2 Test Suite")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if ngrok is running
    ngrok_url = get_ngrok_url()
    
    if not ngrok_url:
        print("❌ Ngrok tunnel not found!")
        print("💡 Please start ngrok first:")
        print("   ./start-ngrok.sh")
        return
    
    print(f"✅ Ngrok URL found: {ngrok_url}")
    
    # Check OAuth2 configuration
    google_config, github_config = check_oauth_config()
    
    # Test API endpoints
    results = test_api_endpoints(ngrok_url)
    
    # Print results
    print_test_results(results, ngrok_url)
    
    # Interactive testing
    if any(results[endpoint]['success'] for endpoint in results):
        print(f"\n🎯 Basic API tests passed!")
        
        if google_config or github_config:
            test_interactive = input("\nRun interactive OAuth2 tests? (y/n): ").lower()
            if test_interactive == 'y':
                interactive_oauth_test(ngrok_url)
        else:
            print(f"\n⚠️  OAuth2 providers not configured")
            print(f"   Run 'python update-oauth-config.py' to set them up")
    else:
        print(f"\n❌ API tests failed. Please check your FastAPI server.")
    
    print(f"\n✅ Testing complete!")

if __name__ == "__main__":
    main()