#!/usr/bin/env python3
"""
Cloudflare Turnstile API Integration Script
This script uses Cloudflare's API to:
1. Create Turnstile widgets for multiple Cloudflare accounts
2. Add specified hostnames to each widget
3. Fetch and save the site keys and secret keys

Based on Cloudflare API documentation:
https://developers.cloudflare.com/turnstile/get-started/server-side-validation/

Usage:
  python cloudflare_turnstile_api.py
"""

import requests
import json
import logging
import sys
import os
import argparse
import datetime
import random
import string

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
CONFIG_FILE = "config.txt"

def read_config(key):
    """Read a value from config.txt by key."""
    try:
        with open(CONFIG_FILE, "r") as f:
            for line in f:
                if line.startswith(f"{key}="):
                    return line.strip().split("=", 1)[1]
    except FileNotFoundError:
        logger.error(f"Config file {CONFIG_FILE} not found")
        return None
    return None

def save_config(key, value):
    """Save key=value to config.txt (update if exists, else append on a new line)."""
    lines = []
    try:
        with open(CONFIG_FILE, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        pass

    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            found = True
            break

    if not found:
        # Ensure the file ends with a newline before appending
        if lines and not lines[-1].endswith("\n"):
            lines[-1] = lines[-1] + "\n"
        lines.append(f"{key}={value}\n")

    with open(CONFIG_FILE, "w") as f:
        f.writelines(lines)

    logger.info(f"Saved {key}={value} to config.txt")


def generate_random_name(length=None):
    """Generate a random string of letters for widget names."""
    if length is None:
        # Random length between 8 and 10
        length = random.randint(8, 10)
    
    # Generate random string of letters
    letters = string.ascii_letters
    return ''.join(random.choice(letters) for _ in range(length))

def create_turnstile_widget(account_id, api_key, email, hostnames, widget_name=None, mode="invisible"):
    """
    Create a new Turnstile widget with the specified hostnames and return the site key and secret key.
    
    Per Cloudflare documentation:
    - Uses Bearer token authentication
    - Endpoint is /challenges/widgets
    - Global API key can be used but specific token is recommended
    
    Args:
        account_id: Cloudflare account ID
        api_key: Cloudflare API key
        email: Cloudflare account email
        hostnames: List of hostnames to add to the widget
        widget_name: Optional name for the widget, if not provided a random name will be generated
    
    Returns:
        Tuple of (site_key, secret_key) if successful, (None, None) otherwise
    """
    # Correct Cloudflare API endpoint (from documentation)
    base_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
    endpoint = f"{base_url}/challenges/widgets"
    
    # Generate a random name if not provided
    if widget_name is None:
        widget_name = generate_random_name()
    
    # Ensure hostnames is a list
    if isinstance(hostnames, str):
        hostnames = [hostnames]
    
    # Widget data to send (per Cloudflare documentation)
    new_widget = {
        "name": widget_name,
        "mode": mode,  # "invisible" or "managed" for visible checkbox
        "domains": hostnames
    }

   
    
    logger.info(f"Creating a new Turnstile widget for {', '.join(hostnames)}...")
    
    # Try first with Bearer token authentication (recommended)
    try:
        # Headers for Bearer token authentication
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Using Bearer token authentication with API endpoint: {endpoint}")
        
        # Make the API request
        create_response = requests.post(endpoint, headers=headers, json=new_widget)
        
        # Log the response status
        logger.info(f"Response status: {create_response.status_code}")
        
        # Check if the request was successful
        if create_response.status_code == 200 or create_response.status_code == 201:
            try:
                create_data = create_response.json()
                
                if create_data.get("success", False):
                    # Extract the keys from the response
                    site_key = create_data["result"]["sitekey"]
                    secret_key = create_data["result"]["secret"]
                    
                    logger.info(f"Successfully created Turnstile widget using Bearer authentication")
                    logger.info(f"Site Key: {site_key}")
                    logger.info(f"Secret Key: {secret_key}")
                    
                    return site_key, secret_key
            except json.JSONDecodeError:
                logger.warning("Response was not valid JSON")
        
        # If Bearer token failed, try with X-Auth headers as fallback
        if create_response.status_code >= 400:
            logger.warning(f"Bearer token authentication failed with status {create_response.status_code}. Trying X-Auth headers...")
            
            # Headers for X-Auth authentication (legacy)
            headers = {
                "X-Auth-Key": api_key,
                "X-Auth-Email": email,
                "Content-Type": "application/json"
            }
            
            # Make the API request with X-Auth headers
            create_response = requests.post(endpoint, headers=headers, json=new_widget)
            
            # Log the response status
            logger.info(f"X-Auth response status: {create_response.status_code}")
            
            # Check if the request was successful
            if create_response.status_code == 200 or create_response.status_code == 201:
                try:
                    create_data = create_response.json()
                    
                    if create_data.get("success", False):
                        # Extract the keys from the response
                        site_key = create_data["result"]["sitekey"]
                        secret_key = create_data["result"]["secret"]
                        
                        logger.info(f"Successfully created Turnstile widget using X-Auth authentication")
                        logger.info(f"Site Key: {site_key}")
                        logger.info(f"Secret Key: {secret_key}")
                        
                        return site_key, secret_key
                except json.JSONDecodeError:
                    logger.warning("Response was not valid JSON")
        
        # Log error details from response if available
        try:
            error_data = create_response.json()
            if 'errors' in error_data:
                error_details = error_data.get('errors', [])
                for error in error_details:
                    logger.error(f"API Error: {error.get('message', 'Unknown error')}")
        except json.JSONDecodeError:
            logger.error(f"Error response (not JSON): {create_response.text[:200]}")
                
    except requests.exceptions.RequestException as e:
        # Log any request exceptions
        logger.error(f"Request error when creating widget: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                logger.error(f"Error response details: {json.dumps(error_data, indent=2)}")
            except (json.JSONDecodeError, ValueError):
                logger.error(f"Error response text: {e.response.text[:500]}")
    
    # If we get here, widget creation failed
    logger.error("Failed to create Turnstile widget")
    
    # Suggest creating a dedicated API token
    logger.warning("NOTE: Cloudflare recommends using a dedicated API token with Account:Turnstile:Edit permissions.")
    logger.warning("      Consider creating a dedicated token in your Cloudflare dashboard if the global API key doesn't work.")
    
    return None, None

def main():
    """
    Main function to create Turnstile widgets for multiple Cloudflare accounts
    using hostnames from config.txt.
    """
    logger.info("Creating Cloudflare Turnstile widgets...")
    
    # Read hostnames from config.txt
    link_url_hostname = read_config("link_url_hostname")
    server_domain = read_config("server_domain")
    inbuilt_redirect_hostname = read_config("inbuilt_redirect_hostname")
    
    # Check if required hostnames exist
    if not link_url_hostname or not server_domain:
        logger.warning("link_url_hostname or server_domain not found in config.txt")
        link_url_hostname = link_url_hostname or "missing-link-url-hostname.com"
        server_domain = server_domain or "missing-server-domain.com"
    
    if not inbuilt_redirect_hostname:
        logger.warning("inbuilt_redirect_hostname not found in config.txt")
        inbuilt_redirect_hostname = "missing-redirect-hostname.com"
    
    # First account widget (uses link_url_hostname and server_domain)
    logger.info("Creating first Turnstile widget...")
    account_id = read_config("cloudflare_account_id")
    api_key = read_config("cloudflare_api_key")
    email = read_config("cloudflare_email")
    
    if account_id and api_key and email:
        logger.info(f"Using first Cloudflare account: {email}")
        # Create widget with both hostnames
        hostnames = [link_url_hostname, server_domain]
        logger.info(f"Adding hostnames to first widget: {', '.join(hostnames)}")
        
        # Generate random widget name
        widget_name = f"Widget_{generate_random_name()}"
        logger.info(f"Generated widget name: {widget_name}")
        
        site_key, secret_key = create_turnstile_widget(account_id, api_key, email, hostnames, widget_name)
        
        if site_key and secret_key:
            # Save keys to config.txt
            save_config("cloudflare_site_key", site_key)
            save_config("cloudflare_secret_key", secret_key)
            
            # Print for easy copying
            print("\n" + "="*60)
            print(f"FIRST WIDGET (for {', '.join(hostnames)})")
            print(f"SITE KEY: {site_key}")
            print(f"SECRET KEY: {secret_key}")
            print("="*60 + "\n")
            
            logger.info("First Turnstile widget created successfully and keys saved to config.txt")
        else:
            logger.error("Failed to create first Turnstile widget")
    else:
        logger.error("Missing credentials for first Cloudflare account")
    
    # Second account widget (uses inbuilt_redirect_hostname)
    logger.info("Creating second Turnstile widget...")
    account_id2 = read_config("cloudflare_account_id2")
    api_key2 = read_config("cloudflare_api_key2")
    email2 = read_config("cloudflare_email2")
    
    if account_id2 and api_key2 and email2:
        logger.info(f"Using second Cloudflare account: {email2}")
        # Create widget with redirect hostname
        logger.info(f"Adding hostname to second widget: {inbuilt_redirect_hostname}")
        
        # Generate random widget name
        widget_name = f"Widget_{generate_random_name()}"
        logger.info(f"Generated widget name: {widget_name}")
        
        # For the second widget, use managed mode (visible checkbox)
        site_key2, secret_key2 = create_turnstile_widget(account_id2, api_key2, email2, inbuilt_redirect_hostname, widget_name, mode="managed")
        
        if site_key2 and secret_key2:
            # Save keys to config.txt with different names
            save_config("cloudflare_site_key2", site_key2)
            save_config("cloudflare_secret_key2", secret_key2)
            
            # Print for easy copying
            print("\n" + "="*60)
            print(f"SECOND WIDGET (for {inbuilt_redirect_hostname})")
            print(f"SITE KEY: {site_key2}")
            print(f"SECRET KEY: {secret_key2}")
            print("="*60 + "\n")
            
            logger.info("Second Turnstile widget created successfully and keys saved to config.txt")
        else:
            logger.error("Failed to create second Turnstile widget")
    else:
        logger.error("Missing credentials for second Cloudflare account")
    
    logger.info("Turnstile widget creation process completed")

if __name__ == "__main__":
    main()