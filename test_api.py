import requests

# Manually set the API token and site URL
api_token = "your_api_token_here"  # Replace with your actual API token
site_url = "http://localhost:8001"  # Server is running on port 8001

# Construct API URL
api_url = f"{site_url}/api/location-stats/"

# Set up headers with token authentication
headers = {"Authorization": f"Token {api_token}"}

print(f"Testing API connection to: {api_url}")
print(f"Using API token: {api_token[:5]}... (truncated for security)")

try:
    # Make the API request
    response = requests.get(api_url, headers=headers, timeout=10)

    # Print response status and content
    print(f"Status code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print("API connection successful!")
        print(f"Received data: {data}")
    else:
        print(f"API request failed with status code: {response.status_code}")
        print(f"Response content: {response.text}")

except requests.exceptions.ConnectionError as e:
    print(f"Connection error: {e}")
    print("Make sure your Django server is running.")

except Exception as e:
    print(f"Error: {e}")

print("\nPossible issues if the request failed:")
print("1. Django server is not running")
print("2. API_TOKEN in .env file is incorrect or not set")
print("3. SITE_URL in .env file is incorrect")
print("4. Token authentication is not properly configured")
