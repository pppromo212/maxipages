#!/usr/bin/env python3
"""
Email Verification Script for Ubuntu VPS
This script automates email verification on emaillistverify.com using PyAutoGUI
and a virtual display on Ubuntu 20.04.
"""

# Import everything except PyAutoGUI first
import time
import subprocess
import random
import string
import requests
import logging
import cv2
import numpy as np
import os
import re
import traceback
import sys
import pyperclip
import tempfile
import shutil
import json
import threading
from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pytesseract
from PIL import Image
import platform
from rapidfuzz import fuzz

# Import getemail module for email generation
import getemail

# Set up logging first
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


CONFIG_FILE = "config.txt"

# Generate a unique ID for this instance
def generate_instance_id(length=8):
    """Generate a random instance ID"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# Set up virtual display before importing PyAutoGUI
logging.info("Setting up virtual display using Xvfb...")
try:
    # Create a virtual display with Xvfb
    display = Display(visible=0, size=(1920, 1080))
    display.start()
    
    if display.is_alive():
        display_num = display.display
        logging.info(f"Virtual display created successfully on display {display_num}")
        # Set DISPLAY environment variable to the actual display created
        os.environ['DISPLAY'] = f":{display_num}"
        
        # Print VNC connection instructions
        logging.info("\n=== VNC CONNECTION INSTRUCTIONS ===")
        logging.info(f"To view the virtual display, install x11vnc and run:")
        logging.info(f"sudo apt-get install x11vnc")
        logging.info(f"x11vnc -display :{display_num} -rfbport {5900 + display_num} -forever -passwd YOUR_PASSWORD")
        logging.info(f"Then connect to your VPS IP on port {5900 + display_num} using a VNC viewer")
        logging.info(f"IMPORTANT: Use display :{display_num} (not :99 or other numbers)")
        logging.info("===============================\n")
    else:
        logging.error("Failed to create virtual display")
        logging.error("\nTROUBLESHOOTING TIPS:")
        logging.error("1. Ensure Xvfb is installed: sudo apt-get install xvfb")
        logging.error("2. Make sure you have the necessary permissions")
        logging.error("3. Check if another Xvfb instance is already using the display")
        sys.exit(1)
except Exception as e:
    logging.error(f"Error setting up virtual display: {str(e)}")
    logging.error(traceback.format_exc())
    logging.error("Virtual display is required. Exiting.")
    sys.exit(1)

# Create an empty .Xauthority file if it doesn't exist
# This prevents Xlib.error.XauthError when importing PyAutoGUI
try:
    xauth_path = os.path.expanduser("~/.Xauthority")
    if not os.path.exists(xauth_path):
        logging.info(f"Creating empty .Xauthority file at {xauth_path}")
        with open(xauth_path, 'wb') as f:
            pass  # Create an empty file
    else:
        logging.info(f".Xauthority file already exists at {xauth_path}")
except Exception as e:
    logging.warning(f"Could not create .Xauthority file: {str(e)}")
    logging.warning("This might cause issues with PyAutoGUI")

# Now import PyAutoGUI after setting up the virtual display
import pyautogui

# URLs and paths - Explicitly set hardcoded signup URL
SIGNUP_URL = "https://dash.cloudflare.com/sign-up"  # Main signup URL - use uppercase for constants
debug_port = 9222  # Port for Firefox debugging (used only temporarily for success sign detection)

def get_progress_stats():
    """Get the current progress statistics"""
    stats = {}
    
    # Count emails in valid.txt
    try:
        if os.path.exists('valid.txt'):
            with open('valid.txt', 'r') as f:
                stats['valid'] = len(f.readlines())
        else:
            stats['valid'] = 0
    except Exception as e:
        logging.error(f"Error counting valid emails: {str(e)}")
        stats['valid'] = 0
    
    # Count emails in invalid.txt
    try:
        if os.path.exists('invalid.txt'):
            with open('invalid.txt', 'r') as f:
                stats['invalid'] = len(f.readlines())
        else:
            stats['invalid'] = 0
    except Exception as e:
        logging.error(f"Error counting invalid emails: {str(e)}")
        stats['invalid'] = 0
    
    # Count emails in unknown.txt
    try:
        if os.path.exists('unknown.txt'):
            with open('unknown.txt', 'r') as f:
                stats['unknown'] = len(f.readlines())
        else:
            stats['unknown'] = 0
    except Exception as e:
        logging.error(f"Error counting unknown emails: {str(e)}")
        stats['unknown'] = 0
    
    # Count emails in bouncework.txt
    try:
        if os.path.exists('bouncework.txt'):
            with open('bouncework.txt', 'r') as f:
                stats['bouncework'] = len(f.readlines())
        else:
            stats['bouncework'] = 0
    except Exception as e:
        logging.error(f"Error counting bouncework emails: {str(e)}")
        stats['bouncework'] = 0
    
    return stats

def create_test_files():
    """Create test files if they don't exist"""
    if not os.path.exists('bouncework.txt'):
        with open('bouncework.txt', 'w') as f:
            f.write("test1@example.com\n")
            f.write("test2@example.com\n")
            f.write("test3@example.com\n")
        logging.info("Created bouncework.txt with test emails")
    
    if not os.path.exists('valid.txt'):
        with open('valid.txt', 'w') as f:
            pass
        logging.info("Created empty valid.txt file")
    
    if not os.path.exists('invalid.txt'):
        with open('invalid.txt', 'w') as f:
            pass
        logging.info("Created empty invalid.txt file")
    
    if not os.path.exists('unknown.txt'):
        with open('unknown.txt', 'w') as f:
            pass
        logging.info("Created empty unknown.txt file")

def check_image_files():
    """Check if required image files exist and are readable"""
    required_images = [
        'email_input_field.png',
        'verify_button.png',
        'verify_human_button.png',
        'success_sign.png'
    ]
    
    missing_images = []
    for img_file in required_images:
        if not os.path.exists(img_file):
            missing_images.append(img_file)
        else:
            # Try to open the image to verify it's valid
            try:
                img = cv2.imread(img_file)
                if img is None:
                    missing_images.append(img_file)
            except Exception:
                missing_images.append(img_file)
    
    if missing_images:
        logging.error("The following required image files are missing or invalid:")
        for img in missing_images:
            logging.error(f"  - {img}")
        
        logging.error("\nPlease create these image files using screenshots from the website.")
        logging.error("You can use the following commands on your VPS:")
        logging.error("1. Install a VNC server to view the display: sudo apt-get install x11vnc")
        logging.error("2. Start the VNC server: x11vnc -display :99 -forever -passwd YOUR_PASSWORD")
        logging.error("3. Connect to the VPS using a VNC client and take screenshots")
        
        return False
    
    logging.info("All required image files found and valid")
    return True



def quit_firefox():
    """Quit all Firefox processes only."""
    logging.info("Quitting all Firefox processes...")

    system = platform.system()

    try:
        if system == "Windows":
            subprocess.call(["taskkill", "/IM", "firefox.exe", "/F"])
        elif system == "Darwin":  # macOS
            subprocess.call(["pkill", "-f", "Firefox"])
        else:  # Linux / Unix
            subprocess.call(["pkill", "firefox"])
        logging.info("Firefox closed successfully.")
    except Exception as e:
        logging.error(f"Failed to quit Firefox: {e}")



def launch_browser_in_virtual_display(display, url=None, max_retries=3):
    """
    Launch a browser within the virtual display with retry mechanism
    Always force the SIGNUP_URL regardless of input to ensure proper navigation
    """
    # Always use the signup URL - override any provided URL to ensure consistency
    url = SIGNUP_URL
    """
    Launch a browser within the virtual display with retry mechanism
    """
    try:
        if not display:
            logging.error("Cannot launch browser without virtual display")
            return None
        
        # Check if Firefox is installed, if not install it
        try:
            subprocess.run(["which", "firefox"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logging.info("Firefox is already installed")
        except subprocess.CalledProcessError:
            logging.info("Firefox not found, installing...")
            subprocess.run(["sudo", "apt-get", "update"], check=True)
            subprocess.run(["sudo", "apt-get", "install", "-y", "firefox"], check=True)
            logging.info("Firefox installed successfully")
        time.sleep(1)  # Give it time to settle
        
        # Kill any existing Firefox processes to ensure a clean start
        try:
            subprocess.run(["pkill", "firefox"], stderr=subprocess.PIPE)
            logging.info("Killed any existing Firefox processes")
            time.sleep(2)  # Give it time to fully terminate
        except Exception as e:
            logging.warning(f"Error killing existing Firefox processes: {str(e)}")
        
        # Configure Firefox to use the virtual display
        env = os.environ.copy()
        env["DISPLAY"] = f":{display.display}"
        
        # Add Firefox preferences for stability
        firefox_profile_dir = os.path.join(tempfile.gettempdir(), "firefox_profile")
        os.makedirs(firefox_profile_dir, exist_ok=True)
        
        # Create a preferences file with settings for better stability
        prefs_file = os.path.join(firefox_profile_dir, "user.js")
        with open(prefs_file, "w") as f:
            # Disable multi-process mode (e10s) for better stability
            f.write('user_pref("browser.tabs.remote.autostart", false);\n')
            f.write('user_pref("browser.tabs.remote.autostart.2", false);\n')
            
            # Disable session restore after crashes
            f.write('user_pref("browser.sessionstore.resume_from_crash", false);\n')
            f.write('user_pref("browser.sessionstore.max_resumed_crashes", 0);\n')
            f.write('user_pref("toolkit.startup.max_resumed_crashes", -1);\n')
            
            # Disable automatic updates and background tasks
            f.write('user_pref("app.update.enabled", false);\n')
            f.write('user_pref("app.update.auto", false);\n')
            f.write('user_pref("browser.search.update", false);\n')
            
            # Disable hardware acceleration (can cause issues in headless environments)
            f.write('user_pref("layers.acceleration.disabled", true);\n')
            
            # Disable WebGL (can cause crashes in headless environments)
            f.write('user_pref("webgl.disabled", true);\n')
            
            # Reduce memory usage
            f.write('user_pref("browser.cache.disk.enable", false);\n')
            f.write('user_pref("browser.cache.memory.enable", true);\n')
            f.write('user_pref("browser.cache.memory.capacity", 256000);\n')  # 256MB memory cache
            
            # Disable unnecessary features
            f.write('user_pref("browser.newtabpage.enabled", false);\n')
            f.write('user_pref("browser.startup.homepage", "about:blank");\n')
            f.write('user_pref("browser.shell.checkDefaultBrowser", false);\n')
            
            # Disable media features that might cause issues
            f.write('user_pref("media.hardware-video-decoding.enabled", false);\n')
            f.write('user_pref("media.ffmpeg.vaapi.enabled", false);\n')
            
            # Removed remote debugging preferences to avoid "browser under remote control" flag
        
        # Launch Firefox with minimal flags and the custom profile
        for attempt in range(max_retries):
            try:
                cmd = [
                    "firefox",
                    "--private-window",  # Equivalent to incognito in Chrome
                    "--new-instance",
                    "-profile", firefox_profile_dir,
                    # Removed "--kiosk" flag to avoid full screen mode that hides address bar
                    "-no-remote",  # Ensure a new instance
                    "-width", "1600",  # Reduced width to ensure full display in VNC
                    "-height", "900",  # Reduced height to ensure full display in VNC
                    "--new-window",  # Force new window
                    SIGNUP_URL  # Always use the hardcoded signup URL
                ]
                
                logging.info(f"Launching Firefox within virtual display (DISPLAY=:{display.display}) - Attempt {attempt+1}/{max_retries}")
                process = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # Wait for the browser to start - longer delay for proper initialization
                logging.info("Waiting for Firefox to initialize...")
                time.sleep(10)  # Increased from 5 to 10 seconds
                
                # Check if the process is still running
                if process.poll() is None:
                    logging.info("Firefox started successfully")
                    
                    # Add explicit navigation to ensure the URL is loaded
                    logging.info(f"Ensuring navigation to URL: {SIGNUP_URL}")
                    time.sleep(3)  # Short pause before navigation attempt
                    
                    # Use PyAutoGUI to ensure navigation to the URL
                    try:
                        # First, make sure we're in the address bar
                        logging.info("Navigating to URL with browser session...")
                        pyautogui.hotkey('ctrl', 'l')
                        time.sleep(1)
                        
                        # Clear any existing URL
                        pyautogui.hotkey('ctrl', 'a')
                        time.sleep(0.5)
                        pyautogui.press('delete')
                        time.sleep(0.5)
                        
                        # Type the URL manually
                        pyautogui.typewrite(SIGNUP_URL)
                        time.sleep(1)
                        pyautogui.press('enter')
                        time.sleep(1)
                        logging.info("Explicit navigation to URL completed")


                        quit_firefox()
                        logging.info("Closed Firefox browser")



                             ########################################################################

                          # Open the browser in the virtual display with the SIGNUP_URL
                        browser_process = launch_browser_in_virtual_display4(display)
                        if not browser_process:
                            logging.error("Failed to launch browser in virtual display")
                            return False

                        
                        # Additional delay to allow page to load
                        time.sleep(7)
                    except Exception as nav_error:
                        logging.warning(f"Explicit navigation attempt failed: {nav_error}")
                        logging.warning("Continuing with process, will check URL later")
                    
                    # Start the email generator in a separate thread
                    logging.info("Starting email generator process...")
                    email_thread = threading.Thread(target=getemail.run_as_thread)
                    email_thread.daemon = True  # Make thread a daemon so it exits when main thread exits
                    email_thread.start()
                    logging.info("Email generator process started in background")
                    
                    return process
                else:
                    stderr = process.stderr.read().decode('utf-8', errors='ignore')
                    stdout = process.stdout.read().decode('utf-8', errors='ignore')
                    logging.error(f"Firefox process exited with code {process.returncode}")
                    if stderr:
                        logging.error(f"Firefox STDERR: {stderr}")
                    if stdout:
                        logging.error(f"Firefox STDOUT: {stdout}")
                    
                    if attempt < max_retries - 1:
                        logging.info(f"Retrying Firefox launch in 5 seconds...")
                        time.sleep(5)
                    else:
                        logging.error("Maximum retries reached. Firefox could not be started.")
                        return None
            except Exception as e:
                logging.error(f"Error launching Firefox (attempt {attempt+1}/{max_retries}): {str(e)}")
                logging.error(traceback.format_exc())
                if attempt < max_retries - 1:
                    logging.info(f"Retrying Firefox launch in 5 seconds...")
                    time.sleep(5)
                else:
                    logging.error("Maximum retries reached. Firefox could not be started.")
                    return None
        
        return None  # Should not reach here, but just in case
    except Exception as e:
        logging.error(f"Error in launch_browser_in_virtual_display: {str(e)}")
        logging.error(traceback.format_exc())
        return None






def launch_browser_in_virtual_display4(display, url=None, max_retries=3):
    """
    Launch a browser within the virtual display with retry mechanism
    Always force the SIGNUP_URL regardless of input to ensure proper navigation
    """
    # Always use the signup URL - override any provided URL to ensure consistency
    url = SIGNUP_URL
    """
    Launch a browser within the virtual display with retry mechanism
    """
    try:
        if not display:
            logging.error("Cannot launch browser without virtual display")
            return None
        
        # Check if Firefox is installed, if not install it
        try:
            subprocess.run(["which", "firefox"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logging.info("Firefox is already installed")
        except subprocess.CalledProcessError:
            logging.info("Firefox not found, installing...")
            subprocess.run(["sudo", "apt-get", "update"], check=True)
            subprocess.run(["sudo", "apt-get", "install", "-y", "firefox"], check=True)
            logging.info("Firefox installed successfully")
        time.sleep(1)  # Give it time to settle
        
        # Kill any existing Firefox processes to ensure a clean start
        try:
            subprocess.run(["pkill", "firefox"], stderr=subprocess.PIPE)
            logging.info("Killed any existing Firefox processes")
            time.sleep(2)  # Give it time to fully terminate
        except Exception as e:
            logging.warning(f"Error killing existing Firefox processes: {str(e)}")
        
        # Configure Firefox to use the virtual display
        env = os.environ.copy()
        env["DISPLAY"] = f":{display.display}"
        
        # Add Firefox preferences for stability
        firefox_profile_dir = os.path.join(tempfile.gettempdir(), "firefox_profile")
        os.makedirs(firefox_profile_dir, exist_ok=True)
        
        # Create a preferences file with settings for better stability
        prefs_file = os.path.join(firefox_profile_dir, "user.js")
        with open(prefs_file, "w") as f:
            # Disable multi-process mode (e10s) for better stability
            f.write('user_pref("browser.tabs.remote.autostart", false);\n')
            f.write('user_pref("browser.tabs.remote.autostart.2", false);\n')
            
            # Disable session restore after crashes
            f.write('user_pref("browser.sessionstore.resume_from_crash", false);\n')
            f.write('user_pref("browser.sessionstore.max_resumed_crashes", 0);\n')
            f.write('user_pref("toolkit.startup.max_resumed_crashes", -1);\n')
            
            # Disable automatic updates and background tasks
            f.write('user_pref("app.update.enabled", false);\n')
            f.write('user_pref("app.update.auto", false);\n')
            f.write('user_pref("browser.search.update", false);\n')
            
            # Disable hardware acceleration (can cause issues in headless environments)
            f.write('user_pref("layers.acceleration.disabled", true);\n')
            
            # Disable WebGL (can cause crashes in headless environments)
            f.write('user_pref("webgl.disabled", true);\n')
            
            # Reduce memory usage
            f.write('user_pref("browser.cache.disk.enable", false);\n')
            f.write('user_pref("browser.cache.memory.enable", true);\n')
            f.write('user_pref("browser.cache.memory.capacity", 256000);\n')  # 256MB memory cache
            
            # Disable unnecessary features
            f.write('user_pref("browser.newtabpage.enabled", false);\n')
            f.write('user_pref("browser.startup.homepage", "about:blank");\n')
            f.write('user_pref("browser.shell.checkDefaultBrowser", false);\n')
            
            # Disable media features that might cause issues
            f.write('user_pref("media.hardware-video-decoding.enabled", false);\n')
            f.write('user_pref("media.ffmpeg.vaapi.enabled", false);\n')
            
            # Removed remote debugging preferences to avoid "browser under remote control" flag
        
        # Launch Firefox with minimal flags and the custom profile
        for attempt in range(max_retries):
            try:
                cmd = [
                    "firefox",
                    "--private-window",  # Equivalent to incognito in Chrome
                    "--new-instance",
                    "-profile", firefox_profile_dir,
                    # Removed "--kiosk" flag to avoid full screen mode that hides address bar
                    "-no-remote",  # Ensure a new instance
                    "-width", "1600",  # Reduced width to ensure full display in VNC
                    "-height", "900",  # Reduced height to ensure full display in VNC
                    "--new-window",  # Force new window
                    SIGNUP_URL  # Always use the hardcoded signup URL
                ]
                
                logging.info(f"Launching Firefox within virtual display (DISPLAY=:{display.display}) - Attempt {attempt+1}/{max_retries}")
                process = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # Wait for the browser to start - longer delay for proper initialization
                logging.info("Waiting for Firefox to initialize...")
                time.sleep(10)  # Increased from 5 to 10 seconds
                
                # Check if the process is still running
                if process.poll() is None:
                    logging.info("Firefox started successfully")
                    
                    # Add explicit navigation to ensure the URL is loaded
                    logging.info(f"Ensuring navigation to URL: {SIGNUP_URL}")
                    time.sleep(3)  # Short pause before navigation attempt
                    
                    # Use PyAutoGUI to ensure navigation to the URL
                    try:
                        # First, make sure we're in the address bar
                        logging.info("Navigating to URL with browser session...")
                        pyautogui.hotkey('ctrl', 'l')
                        time.sleep(1)
                        
                        # Clear any existing URL
                        pyautogui.hotkey('ctrl', 'a')
                        time.sleep(0.5)
                        pyautogui.press('delete')
                        time.sleep(0.5)
                        
                        # Type the URL manually
                        pyautogui.typewrite(SIGNUP_URL)
                        time.sleep(1)
                        pyautogui.press('enter')
                        time.sleep(1)
                        logging.info("Explicit navigation to URL completed")


                        

                        
                        # Additional delay to allow page to load
                        time.sleep(7)
                    except Exception as nav_error:
                        logging.warning(f"Explicit navigation attempt failed: {nav_error}")
                        logging.warning("Continuing with process, will check URL later")
                 
                    
                    return process
                else:
                    stderr = process.stderr.read().decode('utf-8', errors='ignore')
                    stdout = process.stdout.read().decode('utf-8', errors='ignore')
                    logging.error(f"Firefox process exited with code {process.returncode}")
                    if stderr:
                        logging.error(f"Firefox STDERR: {stderr}")
                    if stdout:
                        logging.error(f"Firefox STDOUT: {stdout}")
                    
                    if attempt < max_retries - 1:
                        logging.info(f"Retrying Firefox launch in 5 seconds...")
                        time.sleep(5)
                    else:
                        logging.error("Maximum retries reached. Firefox could not be started.")
                        return None
            except Exception as e:
                logging.error(f"Error launching Firefox (attempt {attempt+1}/{max_retries}): {str(e)}")
                logging.error(traceback.format_exc())
                if attempt < max_retries - 1:
                    logging.info(f"Retrying Firefox launch in 5 seconds...")
                    time.sleep(5)
                else:
                    logging.error("Maximum retries reached. Firefox could not be started.")
                    return None
        
        return None  # Should not reach here, but just in case
    except Exception as e:
        logging.error(f"Error in launch_browser_in_virtual_display: {str(e)}")
        logging.error(traceback.format_exc())
        return None








def launch_browser_in_virtual_display2(display, url=None, max_retries=3):
    """
    Launch a completely fresh browser instance with no previous history or details remembered.
    Uses a unique profile for each launch and ensures private browsing mode.
    """
    try:
        # Always use the signup URL - override any provided URL to ensure consistency
        url = SIGNUP_URL
        
        if not display:
            logging.error("Cannot launch browser without virtual display")
            return None
        
        # Check if Firefox is installed, if not install it
        try:
            subprocess.run(["which", "firefox"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logging.info("Firefox is already installed")
        except subprocess.CalledProcessError:
            logging.info("Firefox not found, installing...")
            subprocess.run(["sudo", "apt-get", "update"], check=True)
            subprocess.run(["sudo", "apt-get", "install", "-y", "firefox"], check=True)
            logging.info("Firefox installed successfully")
        
        # Force kill any existing Firefox processes to ensure a clean start
        try:
            # Use pkill -9 for forceful termination
            subprocess.run(["pkill", "-9", "firefox"], stderr=subprocess.PIPE)
            logging.info("Forcefully terminated any existing Firefox processes")
            time.sleep(3)  # Give more time to fully terminate
        except Exception as e:
            logging.warning(f"Error terminating existing Firefox processes: {str(e)}")
        
        # Configure Firefox to use the virtual display
        env = os.environ.copy()
        env["DISPLAY"] = f":{display.display}"
        
        # Create a unique profile directory with a random ID for this launch
        profile_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
        firefox_profile_dir = os.path.join(tempfile.gettempdir(), f"firefox_fresh_profile_{profile_id}")
        logging.info(f"Creating fresh Firefox profile at: {firefox_profile_dir}")
        
        # Remove any existing profile with this name (shouldn't exist but just in case)
        if os.path.exists(firefox_profile_dir):
            try:
                shutil.rmtree(firefox_profile_dir)
                logging.info(f"Removed existing profile directory: {firefox_profile_dir}")
            except Exception as e:
                logging.warning(f"Error removing profile directory: {str(e)}")
        
        # Create a fresh profile directory
        os.makedirs(firefox_profile_dir, exist_ok=True)
        
        # Create a preferences file with enhanced privacy settings
        prefs_file = os.path.join(firefox_profile_dir, "user.js")
        with open(prefs_file, "w") as f:
            # Force private browsing mode
            f.write('user_pref("browser.privatebrowsing.autostart", true);\n')
            
            # Disable all browsing history
            f.write('user_pref("privacy.history.custom", true);\n')
            f.write('user_pref("privacy.clearOnShutdown.history", true);\n')
            f.write('user_pref("privacy.clearOnShutdown.cookies", true);\n')
            f.write('user_pref("privacy.clearOnShutdown.cache", true);\n')
            f.write('user_pref("privacy.clearOnShutdown.downloads", true);\n')
            f.write('user_pref("privacy.clearOnShutdown.formdata", true);\n')
            f.write('user_pref("privacy.clearOnShutdown.sessions", true);\n')
            f.write('user_pref("privacy.clearOnShutdown.siteSettings", true);\n')
            f.write('user_pref("privacy.sanitize.sanitizeOnShutdown", true);\n')
            
            # Disable session restore completely
            f.write('user_pref("browser.sessionstore.enabled", false);\n')
            f.write('user_pref("browser.sessionstore.resume_from_crash", false);\n')
            f.write('user_pref("browser.sessionstore.max_resumed_crashes", 0);\n')
            f.write('user_pref("toolkit.startup.max_resumed_crashes", -1);\n')
            
            # Disable automatic updates and background tasks
            f.write('user_pref("app.update.enabled", false);\n')
            f.write('user_pref("app.update.auto", false);\n')
            f.write('user_pref("browser.search.update", false);\n')
            
       
            
               # Disable DOM storage
      
            
            # Disable unnecessary features
            f.write('user_pref("browser.newtabpage.enabled", false);\n')
            f.write('user_pref("browser.startup.homepage", "about:blank");\n')
            f.write('user_pref("browser.shell.checkDefaultBrowser", false);\n')
            
            # Disable media features that might cause issues
            f.write('user_pref("media.hardware-video-decoding.enabled", false);\n')
            f.write('user_pref("media.ffmpeg.vaapi.enabled", false);\n')
            
            # Extra privacy settings
            f.write('user_pref("privacy.trackingprotection.enabled", true);\n')  # Enable tracking protection
            f.write('user_pref("browser.safebrowsing.enabled", false);\n')        # Disable safebrowsing (sends data)
            f.write('user_pref("browser.safebrowsing.malware.enabled", false);\n')
            f.write('user_pref("browser.safebrowsing.phishing.enabled", false);\n')
            f.write('user_pref("browser.formfill.enable", false);\n')             # Disable form fill
            f.write('user_pref("signon.rememberSignons", false);\n')              # Disable password manager
            
            # Disable telemetry and data collection
            f.write('user_pref("toolkit.telemetry.enabled", false);\n')
            f.write('user_pref("toolkit.telemetry.unified", false);\n')
            f.write('user_pref("datareporting.healthreport.uploadEnabled", false);\n')
            f.write('user_pref("datareporting.policy.dataSubmissionEnabled", false);\n')
            
            # Disable first run and welcome pages
            f.write('user_pref("browser.startup.homepage_override.mstone", "ignore");\n')
            f.write('user_pref("startup.homepage_welcome_url", "");\n')
            f.write('user_pref("startup.homepage_welcome_url.additional", "");\n')
            f.write('user_pref("browser.startup.firstrunSkipsHomepage", true);\n')
        
        # Launch Firefox with enhanced privacy flags and the fresh profile
        for attempt in range(max_retries):
            try:
                cmd = [
                    "firefox",
                    "--private-window",     # Force private browsing mode
                    "--new-instance",       # Force completely new instance
                    "-profile", firefox_profile_dir,  # Use the unique profile directory
                    "-no-remote",           # Don't connect to existing Firefox instances
                    "-width", "1600",       # Reduced width to ensure full display in VNC
                    "-height", "900",       # Reduced height to ensure full display in VNC
                    "--new-window",         # Force new window
                    "-private",             # Extra private mode flag for redundancy
                    "--no-first-run",       # Skip first run dialogs
                    "--no-default-browser-check",  # Skip default browser check
                    SIGNUP_URL              # Always use the hardcoded signup URL
                ]
                
                logging.info(f"Launching fresh Firefox within virtual display (DISPLAY=:{display.display}) - Attempt {attempt+1}/{max_retries}")
                logging.info(f"Using fresh profile: {firefox_profile_dir}")
                process = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # Wait for the browser to start - longer delay for proper initialization
                logging.info("Waiting for Firefox to initialize...")
                time.sleep(10)  # Increased from 5 to 10 seconds
                
                # Check if the process is still running
                if process.poll() is None:
                    logging.info("Fresh Firefox started successfully")
                    
                    # Add explicit navigation to ensure the URL is loaded
                    logging.info(f"Ensuring navigation to URL: {SIGNUP_URL}")
                    time.sleep(3)  # Short pause before navigation attempt
                    
                    # Use PyAutoGUI to ensure navigation to the URL
                    try:
                        logging.info("Navigating to URL with fresh browser session...")
                        
                        # First, make sure we're in the address bar
                        pyautogui.hotkey('ctrl', 'l')
                        time.sleep(1)
                        
                        # Clear any existing URL
                        pyautogui.hotkey('ctrl', 'a')
                        time.sleep(0.5)
                        pyautogui.press('delete')
                        time.sleep(0.5)
                        
                        # Type the URL manually
                        pyautogui.typewrite(SIGNUP_URL)
                        time.sleep(0.5)
                        pyautogui.press('enter')
                        logging.info("Explicit navigation to URL completed in fresh browser")
                        
                        # Additional delay to allow page to load
                        time.sleep(5)
                    except Exception as nav_error:
                        logging.warning(f"Explicit navigation attempt failed: {nav_error}")
                        logging.warning("Continuing with process, will check URL later")
                    
                    return process
                else:
                    stderr = process.stderr.read().decode('utf-8', errors='ignore')
                    stdout = process.stdout.read().decode('utf-8', errors='ignore')
                    logging.error(f"Firefox process exited with code {process.returncode}")
                    if stderr:
                        logging.error(f"Firefox STDERR: {stderr}")
                    if stdout:
                        logging.error(f"Firefox STDOUT: {stdout}")
                    
                    if attempt < max_retries - 1:
                        logging.info(f"Retrying Firefox launch in 5 seconds...")
                        time.sleep(5)
                    else:
                        logging.error("Maximum retries reached. Firefox could not be started.")
                        return None
            except Exception as e:
                logging.error(f"Error launching Firefox (attempt {attempt+1}/{max_retries}): {str(e)}")
                logging.error(traceback.format_exc())
                if attempt < max_retries - 1:
                    logging.info(f"Retrying Firefox launch in 5 seconds...")
                    time.sleep(5)
                else:
                    logging.error("Maximum retries reached. Firefox could not be started.")
                    return None
        
        return None  # Should not reach here, but just in case
    except Exception as e:
        logging.error(f"Error in launch_browser_in_virtual_display2: {str(e)}")
        logging.error(traceback.format_exc())
        return None





def save_config(key, value):
    """Save key=value to config.txt (appends if exists)."""
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
        lines.append(f"{key}={value}\n")

    with open(CONFIG_FILE, "w") as f:
        f.writelines(lines)




def generate_password():
    letters = string.ascii_letters
    digits = string.digits
    specials = "!@#$%&"
    password = ''.join(random.choice(letters) for _ in range(16))
    password += random.choice(digits)
    password += random.choice(specials)
    return ''.join(random.sample(password, len(password)))  # shuffle



def load_config():
    """Load key=value pairs from config.txt into a dict."""
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r") as f:
        return dict(line.strip().split("=", 1) for line in f if "=" in line)






def generate_subdomain(length=None):
    """Generate a random subdomain string of 14–16 letters."""
    if length is None:
        length = random.randint(14, 16)
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(length))


# Function to get Heroku URL from user
def get_heroku_url():
    """Prompt the user for their Heroku URL and return it."""
    print("\n" + "="*60)
    print("Please enter your Heroku URL (e.g., https://your-app.herokuapp.com)")
    print("="*60)
    heroku_url = input("Heroku URL: ").strip()
    
    # Basic validation
    while not (heroku_url.startswith("http://") or heroku_url.startswith("https://")):
        print("Invalid URL. URL must start with http:// or https://")
        heroku_url = input("Heroku URL: ").strip()
    
    print(f"Using Heroku URL: {heroku_url}")
    return heroku_url

# Function to extract domain from URL
def extract_domain(url):
    """Extract domain name from URL."""
    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    return parsed_url.netloc

def main_process(display):
    # Get Heroku URL from user
    heroku_url = get_heroku_url()
    
    # Check if required image files exist before starting
    if not check_image_files():
        logging.error("Cannot proceed without required image files")
        return False
    
    # Open the browser in the virtual display with the SIGNUP_URL
    browser_process = launch_browser_in_virtual_display(display)
    if not browser_process:
        logging.error("Failed to launch browser in virtual display")
        return False
        
    # Wait for browser to initialize but don't force full screen mode
    time.sleep(4)
    try:
        # Ensure we're NOT in full screen mode (press ESC to exit if we are)
        pyautogui.press('escape')
        logging.info("Ensured browser is not in full screen mode")
        time.sleep(2)
        
        # Take a screenshot showing the full browser window including address bar
        screenshot_path = os.path.join(os.getcwd(), "browser_startup.png")
        try:
            pyautogui.screenshot(screenshot_path)
            logging.info(f"Saved initial browser screenshot to {screenshot_path}")
        except Exception as ss_err:
            logging.warning(f"Failed to save initial screenshot: {ss_err}")
    except Exception as e:
        logging.warning(f"Error setting browser window mode: {str(e)}")

    # Page loading retry loop
    
    page_load_attempts = 0
    max_page_load_attempts = 3
    
    while page_load_attempts < max_page_load_attempts:
            logging.info(f"Page load attempt {page_load_attempts + 1}/{max_page_load_attempts}")


            verify_human_button_found = False
            confidence_levels = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4]  # Added even lower confidence level
                
            for confidence in confidence_levels:
                try:
                    logging.info(f"Looking for verify human button1 with confidence {confidence}...")
                    verify_human_button_position = pyautogui.locateOnScreen('verify_human_button2.png', confidence=confidence)
                    if verify_human_button_position:
                        logging.info(f"Verify human button found with confidence {confidence}")
                        

                        # Before clicking, verify the text on the button using OCR
                        try:
                            # Make sure pytesseract is installed
                            try:
                                import pytesseract
                            except ImportError:
                                logging.info("pytesseract not found, installing...")
                                subprocess.run(["pip", "install", "pytesseract"], check=True)
                                import pytesseract
                                
                            # Log the type and value of verify_human_button_position for debugging
                            logging.info(f"Button position type: {type(verify_human_button_position)}")
                            logging.info(f"Button position value: {verify_human_button_position}")
                            
                            # Extract coordinates from button position
                            try:
                                # Try to access as a Box object with attributes
                                x = verify_human_button_position.left
                                y = verify_human_button_position.top
                                width = verify_human_button_position.width
                                height = verify_human_button_position.height
                                logging.info(f"Accessed button position as Box object: {x}, {y}, {width}, {height}")
                            except AttributeError:
                                # If that fails, try to unpack as a tuple
                                try:
                                    x, y, width, height = verify_human_button_position
                                    logging.info(f"Unpacked button position as tuple: {x}, {y}, {width}, {height}")
                                except (ValueError, TypeError):
                                    # If both methods fail, log the error and fall back to clicking without OCR
                                    logging.error(f"Could not extract coordinates from button position: {verify_human_button_position}")
                                    pyautogui.click(verify_human_button_position)
                                    logging.info("Clicked verify human button (skipped OCR due to coordinate extraction error)")
                                    verify_human_button_found = True
                                    break
                            
                            # Ensure all values are integers
                            x = int(x)
                            y = int(y)
                            width = int(width)
                            height = int(height)
                            
                            # Add padding around the button (20 pixels on each side)
                            x_expanded = max(0, x - 20)
                            y_expanded = max(0, y - 20)
                            width_expanded = width + 40
                            height_expanded = height + 40
                            
                            # Take a screenshot of the expanded button area
                            # PyAutoGUI screenshot region must be (left, top, width, height)
                            logging.info("Taking screenshot of button area for OCR verification...")
                            logging.info(f"Screenshot region: {x_expanded}, {y_expanded}, {width_expanded}, {height_expanded}")
                            button_region = (x_expanded, y_expanded, width_expanded, height_expanded)
                            button_screenshot = pyautogui.screenshot(region=button_region)
                            
                            # Save the screenshot temporarily
                            temp_button_path = os.path.join(tempfile.gettempdir(), "temp_button.png")
                            button_screenshot.save(temp_button_path)
                            
                            # Use OCR to extract text from the button screenshot
                            button_text = pytesseract.image_to_string(temp_button_path).lower()
                            
                            # Log the extracted text for debugging
                            logging.info(f"OCR extracted text from button: '{button_text}'")
                            
                            # Check if the text contains expected phrases
                            expected_phrases = ["human", "verify you", "verify you ar", "verify", "human verification"]
                            text_verified = any(phrase in button_text for phrase in expected_phrases)
                        except Exception as e:
                            logging.warning(f"Error during OCR verification: {str(e)}")
                            # If OCR fails, fall back to clicking based on image recognition only
                            logging.info("Falling back to image recognition only due to OCR error")
                            pyautogui.click(verify_human_button_position)
                            logging.info("Clicked verify human button (OCR verification failed)")
                            verify_human_button_found = True
                            break
                    
                    if text_verified:
                        logging.info(f"Button text verified as containing expected phrases")
                        
                        # Now detect the square-shaped clickable element within the button area
                        try:
                            # Load the image with OpenCV
                            button_img = cv2.imread(temp_button_path)
                            if button_img is None:
                                raise ValueError("Failed to load button image with OpenCV")
                            
                            # Convert to grayscale
                            gray = cv2.cvtColor(button_img, cv2.COLOR_BGR2GRAY)
                            
                            # Apply thresholding to create a binary image
                            _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
                            
                            # Find contours
                            contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                            
                            # Filter contours to find squares
                            squares = []
                            for contour in contours:
                                # Approximate the contour
                                epsilon = 0.04 * cv2.arcLength(contour, True)
                                approx = cv2.approxPolyDP(contour, epsilon, True)
                                
                                # If the contour has 4 vertices (square/rectangle)
                                if len(approx) == 4:
                                    # Calculate aspect ratio
                                    x, y, w, h = cv2.boundingRect(approx)
                                    aspect_ratio = float(w) / h
                                    
                                    # If it's approximately square (aspect ratio close to 1)
                                    if 0.8 <= aspect_ratio <= 1.2:
                                        # Add to squares list with area
                                        area = cv2.contourArea(contour)
                                        squares.append((x, y, w, h, area))
                            
                            # Check if any squares were found
                            if squares:
                                # Sort by area (largest first)
                                squares.sort(key=lambda s: s[4], reverse=True)
                                
                                # Get the largest square
                                x, y, w, h, _ = squares[0]
                                
                                # Save a debug image with the square highlighted
                                debug_img = button_img.copy()
                                cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                                debug_path = os.path.join(tempfile.gettempdir(), "debug_square.png")
                                cv2.imwrite(debug_path, debug_img)
                                logging.info(f"Saved debug image with detected square to {debug_path}")
                                
                                # Calculate center of the square
                                square_center_x = x + w // 2
                                square_center_y = y + h // 2
                                
                                # Calculate the absolute position to click
                                click_x = x_expanded + square_center_x
                                click_y = y_expanded + square_center_y
                                
                                logging.info(f"Detected square at ({x}, {y}) with size {w}x{h}")
                                logging.info(f"Clicking at calculated center point: ({click_x}, {click_y})")
                                
                                # Click at the center of the square
                                pyautogui.click(click_x, click_y)
                                logging.info("Clicked center of square in verify human button")
                            else:
                                # If no squares found, fall back to clicking the center of the button
                                logging.warning("No squares detected in button image, falling back to center click")
                                pyautogui.click(verify_human_button_position)
                                logging.info("Clicked verify human button (center)")
                        except Exception as e:
                            logging.warning(f"Error during square detection: {str(e)}")
                            # Fall back to clicking the button directly
                            pyautogui.click(verify_human_button_position)
                            logging.info("Clicked verify human button (fallback after square detection error)")
                                    
                        except Exception as e:
                            logging.warning(f"Error during OCR text verification: {str(e)}")
                            # If OCR fails, fall back to clicking based on image recognition only
                            logging.info("Falling back to image recognition only due to OCR error")
                            pyautogui.click(verify_human_button_position)
                            logging.info("Clicked verify human button (OCR verification failed)")
                            verify_human_button_found = True
                            break
                        
                        # If we reach here and text_verified is true, mark button as found
                        if text_verified:
                            verify_human_button_found = True
                            break
                        else:
                            logging.warning(f"Button found but text verification failed. Text: '{button_text}'")
                            # Continue to next confidence level without clicking
                except Exception as e:
                    logging.warning(f"Error finding verify human button with confidence {confidence}: {str(e)}")


           
            time.sleep(17)  # Wait a bit for the page to stabilize
            # Wait for the email input field to appear
            email_input_field_image = 'email_input_field.png'
            email_input_field = None
            max_attempts = 10
            attempts = 0
            
            # Try multiple confidence levels for email input field detection
            confidence_levels = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4]  # Added even lower confidence level
            
            # Give the page more time to fully load before starting detection
            logging.info("Waiting for page to fully load...")
            time.sleep(5)
            
            while email_input_field is None and attempts < max_attempts:
                for confidence in confidence_levels:
                    try:
                        logging.info(f"Looking for email input field with confidence {confidence}...")
                        email_input_field = pyautogui.locateOnScreen(email_input_field_image, confidence=confidence)
                        if email_input_field:
                            logging.info(f"Detected email input field with confidence {confidence}")
                            break
                    except Exception as e:
                        logging.warning(f"Error detecting email input field with confidence {confidence}: {str(e)}")
                
                if email_input_field is None:
                    attempts += 1
                    logging.warning(f"Could not detect email input field (attempt {attempts}/{max_attempts})")
                    
                    # Try refreshing the page if we're halfway through our attempts
                    if attempts == max_attempts // 2:
                        logging.info("Refreshing page to try again...")
                        pyautogui.hotkey('ctrl', 'r')  # Firefox uses Ctrl+R for refresh
                        time.sleep(5)  # Wait for page to reload
                    else:
                        time.sleep(2)  # Longer wait between attempts
            
            # Check if we found the email input field
            if email_input_field is not None:
                # We found the email input field, break out of the page load retry loop
                break
            
            # If we couldn't find the email input field, try reloading the page
            page_load_attempts += 1
            if page_load_attempts < max_page_load_attempts:
                logging.warning("Could not detect email input field. Restarting browser...")
                
                # Close the current browser
                browser_process.terminate()
                time.sleep(2)
                
                # Open a new browser instance in the virtual display
                browser_process = launch_browser_in_virtual_display(display, url)
                if not browser_process:
                    logging.error("Failed to restart browser")
                    return False
                
                time.sleep(5)  # Wait for the browser to load
            else:
                logging.error("Could not detect email input field after multiple page load attempts")
                return False
        
        # At this point, we've successfully found the email input field
        # Now process the email (this is outside the page load retry loop)
        
    # Get email from config.txt file instead of bouncework.txt
    email = None
    try:
        # Try to read cloudflare_email from config.txt
        with open(CONFIG_FILE, "r") as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith("cloudflare_email="):
                    email = line.split("=", 1)[1].strip()
                    logging.info(f"Found email in config.txt: {email}")
                    break
    except Exception as e:
        logging.error(f"Error reading email from config.txt: {str(e)}")
    
    # If no email was found in config.txt, generate a random one for testing
    if not email:
        logging.warning("No email found in config.txt, using a test email")
        email = f"test{random.randint(1000, 9999)}@example.com"
        save_config("cloudflare_email", email)

    # Click on the email input field and type the email
    pyautogui.click(email_input_field)
    pyautogui.typewrite(email)
    pyautogui.press('tab')  # Move to the next field
    logging.info(f"Entered email: {email}")

    # Give the page more time to load and stabilize
    time.sleep(3)

    # wait for email input to be processed
    time.sleep(3)
    # Generate password
    cloudflare_password = generate_password()
    logging.info(f"Generated cloudflare_password: {cloudflare_password}")
    time.sleep(1)

    pyautogui.typewrite(cloudflare_password)
    logging.info(f"Typed password into verified password field")

    # Save password to config.txt
    save_config("cloudflare_password", cloudflare_password)
    logging.info("Saved cloudflare_password to config.txt")
    
    # Extract and save domain from Heroku URL
    server_domain = extract_domain(heroku_url)
    save_config("server_domain", server_domain)
    logging.info(f"Saved server domain '{server_domain}' to config.txt")

    pyautogui.scroll(-500)
    time.sleep(1)
    pyautogui.scroll(-500)

    time.sleep(2)  # wait for page to stabilize after scrolling
    
    # Wait longer for the page to process and stabilize
    time.sleep(7)

    # Try to find the verify human button with multiple attempts and decreasing confidence
    verify_human_button_found = False
    confidence_levels = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4]  # Added even lower confidence level
    
    for confidence in confidence_levels:
        try:
            logging.info(f"Looking for verify human button with confidence {confidence}...")
            verify_human_button_position = pyautogui.locateOnScreen('verify_human_button.png', confidence=confidence)
            if verify_human_button_position:
                logging.info(f"Verify human button found with confidence {confidence}")
                
                # Before clicking, verify the text on the button using OCR
                try:
                    # Make sure pytesseract is installed
                    try:
                        import pytesseract
                    except ImportError:
                        logging.info("pytesseract not found, installing...")
                        subprocess.run(["pip", "install", "pytesseract"], check=True)
                        import pytesseract
                                
                    # Log the type and value of verify_human_button_position for debugging
                    logging.info(f"Button position type: {type(verify_human_button_position)}")
                    logging.info(f"Button position value: {verify_human_button_position}")
                    
                    # Handle different return types from locateOnScreen
                    # It could be a Box object or a tuple-like object
                    try:
                        # Try to access as a Box object with attributes
                        x = verify_human_button_position.left
                        y = verify_human_button_position.top
                        width = verify_human_button_position.width
                        height = verify_human_button_position.height
                        logging.info(f"Accessed button position as Box object: {x}, {y}, {width}, {height}")
                    except AttributeError:
                        # If that fails, try to unpack as a tuple
                        try:
                            x, y, width, height = verify_human_button_position
                            logging.info(f"Unpacked button position as tuple: {x}, {y}, {width}, {height}")
                        except (ValueError, TypeError):
                            # If both methods fail, log the error and fall back to clicking without OCR
                            logging.error(f"Could not extract coordinates from button position: {verify_human_button_position}")
                            pyautogui.click(verify_human_button_position)
                            logging.info("Clicked verify human button (skipped OCR due to coordinate extraction error)")
                            verify_human_button_found = True
                            break
                    
                    # Ensure all values are integers
                    x = int(x)
                    y = int(y)
                    width = int(width)
                    height = int(height)
                    
                    # Add padding around the button (20 pixels on each side)
                    x_expanded = max(0, x - 20)
                    y_expanded = max(0, y - 20)
                    width_expanded = width + 40
                    height_expanded = height + 40
                    
                    # Take a screenshot of the expanded button area
                    # PyAutoGUI screenshot region must be (left, top, width, height)
                    logging.info("Taking screenshot of button area for OCR verification...")
                    logging.info(f"Screenshot region: {x_expanded}, {y_expanded}, {width_expanded}, {height_expanded}")
                    button_region = (x_expanded, y_expanded, width_expanded, height_expanded)
                    button_screenshot = pyautogui.screenshot(region=button_region)
                    
                    # Save the screenshot temporarily
                    temp_button_path = os.path.join(tempfile.gettempdir(), "temp_button.png")
                    button_screenshot.save(temp_button_path)
                    
                    # Use OCR to extract text from the button screenshot
                    button_text = pytesseract.image_to_string(temp_button_path).lower()
                    
                    # Log the extracted text for debugging
                    logging.info(f"OCR extracted text from button: '{button_text}'")
                    
                    # Check if the text contains expected phrases
                    expected_phrases = ["human", "verify you", "verify you ar", "verify", "human verification"]
                    text_verified = any(phrase in button_text for phrase in expected_phrases)
                    import cv2
                    
                    if text_verified:
                        logging.info(f"Button text verified as containing expected phrases")
                        
                        # Now detect the square-shaped clickable element within the button area
                        try:
                            # Load the image with OpenCV
                            button_img = cv2.imread(temp_button_path)
                            if button_img is None:
                                raise ValueError("Failed to load button image with OpenCV")
                            
                            # Convert to grayscale
                            gray = cv2.cvtColor(button_img, cv2.COLOR_BGR2GRAY)
                            
                            # Apply thresholding to create a binary image
                            _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
                            
                            # Find contours
                            contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                            
                            # Filter contours to find squares
                            squares = []
                            for contour in contours:
                                # Approximate the contour
                                epsilon = 0.04 * cv2.arcLength(contour, True)
                                approx = cv2.approxPolyDP(contour, epsilon, True)
                                
                                # If the contour has 4 vertices (square/rectangle)
                                if len(approx) == 4:
                                    # Calculate aspect ratio
                                    x, y, w, h = cv2.boundingRect(approx)
                                    aspect_ratio = float(w) / h
                                    
                                    # If it's approximately square (aspect ratio close to 1)
                                    if 0.8 <= aspect_ratio <= 1.2:
                                        # Add to squares list with area
                                        area = cv2.contourArea(contour)
                                        squares.append((x, y, w, h, area))
                            
                            # If squares were found
                            if squares:
                                # Sort by area (largest first)
                                squares.sort(key=lambda s: s[4], reverse=True)
                                
                                # Get the largest square
                                x, y, w, h, _ = squares[0]
                                
                                # Save a debug image with the square highlighted
                                debug_img = button_img.copy()
                                cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                                debug_path = os.path.join(tempfile.gettempdir(), "debug_square.png")
                                cv2.imwrite(debug_path, debug_img)
                                logging.info(f"Saved debug image with detected square to {debug_path}")
                                
                                # Calculate center of the square
                                square_center_x = x + w // 2
                                square_center_y = y + h // 2
                                
                                # Calculate the absolute position to click
                                click_x = x_expanded + square_center_x
                                click_y = y_expanded + square_center_y
                                
                                logging.info(f"Detected square at ({x}, {y}) with size {w}x{h}")
                                logging.info(f"Clicking at calculated center point: ({click_x}, {click_y})")
                                
                                # Click at the center of the square
                                pyautogui.click(click_x, click_y)
                                logging.info("Clicked center of square in verify human button")
                            else:
                                # If no squares found, fall back to clicking the center of the button
                                logging.warning("No squares detected in button image, falling back to center click")
                                pyautogui.click(verify_human_button_position)
                                logging.info("Clicked verify human button (center)")
                        except Exception as e:
                            logging.warning(f"Error during square detection: {str(e)}")
                            # Fall back to clicking the button directly
                            pyautogui.click(verify_human_button_position)
                            logging.info("Clicked verify human button (fallback after square detection error)")
                        
                        verify_human_button_found = True
                        break
                    else:
                        logging.warning(f"Button found but text verification failed. Text: '{button_text}'")
                        # Continue to next confidence level without clicking
                except Exception as e:
                    logging.warning(f"Error during OCR text verification: {str(e)}")
                    # If OCR fails, fall back to clicking based on image recognition only
                    logging.info("Falling back to image recognition only due to OCR error")
                    pyautogui.click(verify_human_button_position)
                    logging.info("Clicked verify human button (OCR verification failed)")
                    verify_human_button_found = True
                    break
        except Exception as e:
            logging.warning(f"Error finding verify human button with confidence {confidence}: {str(e)}")
    
    # Wait for success sign
    time.sleep(12)  # Adjust the time as needed

    # After verify human button, look for sign_up_button
    
    # Try to find the sign_up_button with multiple attempts and decreasing confidence
    sign_up_button_found = False
    confidence_levels = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4]
                
    for confidence in confidence_levels:
        try:
            logging.info(f"Looking for sign_up_button with confidence {confidence}...")
            sign_up_button_position = pyautogui.locateOnScreen('signup_button_cloudflare.png', confidence=confidence)
            if sign_up_button_position:
                logging.info(f"Sign-up button found with confidence {confidence}")
                pyautogui.click(sign_up_button_position)
                logging.info("Clicked sign-up button")
                sign_up_button_found = True
                break
        except Exception as e:
            logging.warning(f"Error finding sign-up button with confidence {confidence}: {str(e)}")
    
    if not sign_up_button_found:
        logging.error("Could not find sign-up button after multiple attempts")
    
    
    time.sleep(32)  # Wait for any final processing


    logging.info("waiting for verification url1")




        # Human verify via PyAutoGUI
    time.sleep(12)
    
    # Open new tab in browser (Ctrl+T)
    pyautogui.hotkey('ctrl', 't')
    time.sleep(2)  # Wait for new tab to open

    # Read verification_url from config.txt with a 60-second timeout
    start_time = time.time()
    timeout = 100  # 60 seconds timeout
    verification_url = None
    
    logging.info("Waiting for verification_url to appear in config.txt (timeout: 60 seconds)...")
    
    while time.time() - start_time < timeout:
        try:
            with open(CONFIG_FILE, "r") as f:
                config_data = dict(line.strip().split("=", 1) for line in f if "=" in line)
            
            verification_url = config_data.get("verification_url")
            
            if verification_url:
                logging.info(f"Found verification_url after {int(time.time() - start_time)} seconds")
                break
            
            # Wait for 2 seconds before checking again
            time.sleep(2)
            logging.info(f"Waiting for verification_url... ({int(time.time() - start_time)} seconds elapsed)")
            
        except Exception as e:
            logging.warning(f"Error reading config.txt: {e}")
            time.sleep(2)
    
    if not verification_url:
        logging.error(f"verification_url missing in config.txt after {timeout} seconds timeout")
        return

# ✅ Remove verification_url from config_data
    del config_data["verification_url"]
    logging.info("Removed verification_url from config.txt")

# ✅ Rewrite config.txt without that key
    with open(CONFIG_FILE, "w") as f:
        for key, value in config_data.items():
           f.write(f"{key}={value}\n")

    # Type the verification URL and press Enter
    pyautogui.typewrite(verification_url)
    pyautogui.press('enter')
    logging.info(f"Visited verification URL: {verification_url}")

    time.sleep(15)  # wait for signup to complete



    # Make sure to capture the full browser window including address bar
    try:
        # Take screenshot with explicit dimensions to ensure entire browser is captured
        screenshot = pyautogui.screenshot()
        # Save with an informative name indicating it includes address bar
        screenshot_path = os.path.join(os.getcwd(), "full_profilepage_with_addressbar.png")
        screenshot.save(screenshot_path)
        # Also save with original filename for backward compatibility
        full_profilepage_path = "full_profilepage.png"
        screenshot.save(full_profilepage_path)
        logging.info(f"Saved complete browser screenshot to {full_profilepage_path}")
        
        # Process the specifically requested full_profilepage.png with OCR to extract text
        try:
            # Make sure pytesseract is installed
            try:
                import pytesseract
                import cv2
            except ImportError:
                logging.info("pytesseract or cv2 not found, installing...")
                subprocess.run(["pip", "install", "pytesseract opencv-python-headless"], check=True)
                import pytesseract
                import cv2
            
            # Make sure tesseract-ocr is installed (essential for OCR functionality)
            try:
                tesseract_check = subprocess.run(["which", "tesseract"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if tesseract_check.returncode != 0:
                    logging.info("tesseract-ocr not found, installing...")
                    subprocess.run(["sudo", "apt-get", "update", "-y"], check=False)
                    subprocess.run(["sudo", "apt-get", "install", "-y", "tesseract-ocr"], check=False)
                    logging.info("tesseract-ocr installation attempted")
            except Exception as e:
                logging.warning(f"Error checking/installing tesseract-ocr: {str(e)}")
            
            logging.info(f"Processing {full_profilepage_path} for text extraction with enhanced OCR...")
            
            # Try to directly copy the URL from the address bar first
            try:
                logging.info("Attempting to directly copy URL from address bar...")
                # Focus the address bar
                pyautogui.hotkey('ctrl', 'l')
                time.sleep(0.5)
                
                # Select all text in the address bar
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.5)
                
                # Copy the URL
                pyautogui.hotkey('ctrl', 'c')
                time.sleep(1)  # Give more time for copying
                
                # Check if clipboard tools are installed
                try:
                    # Ensure xclip is installed
                    subprocess.run(["which", "xclip"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                except subprocess.CalledProcessError:
                    logging.info("xclip not found, installing...")
                    subprocess.run(["sudo", "apt-get", "update"], check=False)
                    subprocess.run(["sudo", "apt-get", "install", "-y", "xclip"], check=False)
                
                # Try to get URL from clipboard using xclip
                try:
                    clipboard_process = subprocess.run(
                        ["xclip", "-selection", "clipboard", "-o"], 
                        capture_output=True, 
                        text=True,
                        env=dict(os.environ, DISPLAY=f":{display.display}")
                    )
                    direct_url = clipboard_process.stdout.strip()
                    
                    if direct_url and ('http' in direct_url.lower() or 'cloudflare' in direct_url.lower()):
                        logging.info(f"Successfully copied URL directly from address bar: {direct_url}")
                        # Save the URL to a variable for later use
                        extracted_url = direct_url
                        
                        # Extract account ID from URL and save to config
                        try:
                            # Extract account ID using regex pattern
                            account_id_match = re.search(r'dash\.cloudflare\.com/([a-zA-Z0-9]+)', direct_url)
                            if account_id_match:
                                account_id = account_id_match.group(1)
                                logging.info(f"Extracted Cloudflare account ID: {account_id}")
                                
                                # Save the account ID to config.txt
                                save_config("cloudflare_account_id", account_id)
                                logging.info("Saved account_id to config.txt")
                            else:
                                logging.warning("Could not extract account ID from URL")
                        except Exception as e:
                            logging.error(f"Error extracting or saving account ID: {e}")
                    else:
                        logging.warning(f"Clipboard content doesn't appear to be a valid URL: '{direct_url}'")
                except Exception as clip_err:
                    logging.warning(f"Error getting clipboard content with xclip: {clip_err}")
            except Exception as copy_err:
                logging.warning(f"Error during direct URL copying: {copy_err}")
            
            
                
        except Exception as ocr_err:
            logging.error(f"Failed to extract text from screenshot: {ocr_err}")
            logging.error(f"OCR error details: {traceback.format_exc()}")
            logging.error("Make sure tesseract-ocr is properly installed on your system")
            
           
    except Exception as ss_err:
        logging.error(f"Failed to save profile page screenshot: {ss_err}")

    time.sleep(5)
    # Step 4: Navigate to API tokens page
    api_tokens_url = "https://dash.cloudflare.com/profile/api-tokens"
    open_new_tab_in_firefox(api_tokens_url)

    time.sleep(5)

    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("enter")
    logging.info("Clicked 'View' button for Global API Key")


 
    time.sleep(10)

    # Step 6: Focus password input
    pyautogui.press("tab")
    time.sleep(2)

    # Step 7: Read password from config.txt and type it
    cloudflare_password = get_config("cloudflare_password")
    if not cloudflare_password:
        logging.error("Cloudflare password not found in config.txt")
        return
    pyautogui.typewrite(cloudflare_password, interval=0.05)
    logging.info("Typed Cloudflare password")

    time.sleep(7)

    

    verify_human_button_found = False
    confidence_levels = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4]  # Added even lower confidence level
                
    for confidence in confidence_levels:
        try:
            logging.info(f"Looking for verify human button1 with confidence {confidence}...")
            verify_human_button_position = pyautogui.locateOnScreen('verify_human3.png', confidence=confidence)
            if verify_human_button_position:
                logging.info(f"Verify human button found with confidence {confidence}")
                        

                        # Before clicking, verify the text on the button using OCR
                try:
                            # Make sure pytesseract is installed
                    try:
                        import pytesseract
                    except ImportError:
                        logging.info("pytesseract not found, installing...")
                        subprocess.run(["pip", "install", "pytesseract"], check=True)
                        import pytesseract
                                
                            # Log the type and value of verify_human_button_position for debugging
                    logging.info(f"Button position type: {type(verify_human_button_position)}")
                    logging.info(f"Button position value: {verify_human_button_position}")
                            
                            # Extract coordinates from button position
                    try:
                                # Try to access as a Box object with attributes
                        x = verify_human_button_position.left
                        y = verify_human_button_position.top
                        width = verify_human_button_position.width
                        height = verify_human_button_position.height
                        logging.info(f"Accessed button position as Box object: {x}, {y}, {width}, {height}")
                    except AttributeError:
                                # If that fails, try to unpack as a tuple
                        try:
                            x, y, width, height = verify_human_button_position
                            logging.info(f"Unpacked button position as tuple: {x}, {y}, {width}, {height}")
                        except (ValueError, TypeError):
                                    # If both methods fail, log the error and fall back to clicking without OCR
                            logging.error(f"Could not extract coordinates from button position: {verify_human_button_position}")
                            pyautogui.click(verify_human_button_position)
                            logging.info("Clicked verify human button (skipped OCR due to coordinate extraction error)")
                            verify_human_button_found = True
                            break
                            
                            # Ensure all values are integers
                    x = int(x)
                    y = int(y)
                    width = int(width)
                    height = int(height)
                            
                            # Add padding around the button (20 pixels on each side)
                    x_expanded = max(0, x - 20)
                    y_expanded = max(0, y - 20)
                    width_expanded = width + 40
                    height_expanded = height + 40
                            
                            # Take a screenshot of the expanded button area
                            # PyAutoGUI screenshot region must be (left, top, width, height)
                    logging.info("Taking screenshot of button area for OCR verification...")
                    logging.info(f"Screenshot region: {x_expanded}, {y_expanded}, {width_expanded}, {height_expanded}")
                    button_region = (x_expanded, y_expanded, width_expanded, height_expanded)
                    button_screenshot = pyautogui.screenshot(region=button_region)
                            
                            # Save the screenshot temporarily
                    temp_button_path = os.path.join(tempfile.gettempdir(), "temp_button.png")
                    button_screenshot.save(temp_button_path)
                            
                            # Use OCR to extract text from the button screenshot
                    button_text = pytesseract.image_to_string(temp_button_path).lower()
                            
                            # Log the extracted text for debugging
                    logging.info(f"OCR extracted text from button: '{button_text}'")
                            
                            # Check if the text contains expected phrases
                    expected_phrases = ["human", "verify you", "verify you ar", "verify", "human verification"]
                    text_verified = any(phrase in button_text for phrase in expected_phrases)
                except Exception as e:
                    logging.warning(f"Error during OCR verification: {str(e)}")
                            # If OCR fails, fall back to clicking based on image recognition only
                    logging.info("Falling back to image recognition only due to OCR error")
                    pyautogui.click(verify_human_button_position)
                    logging.info("Clicked verify human button (OCR verification failed)")
                    verify_human_button_found = True
                    break
                    
            if text_verified:
                logging.info(f"Button text verified as containing expected phrases")
                        
                        # Now detect the square-shaped clickable element within the button area
                try:
                            # Load the image with OpenCV
                    button_img = cv2.imread(temp_button_path)
                    if button_img is None:
                        raise ValueError("Failed to load button image with OpenCV")
                            
                            # Convert to grayscale
                    gray = cv2.cvtColor(button_img, cv2.COLOR_BGR2GRAY)
                            
                            # Apply thresholding to create a binary image
                    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
                            
                            # Find contours
                    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                            
                            # Filter contours to find squares
                    squares = []
                    for contour in contours:
                                # Approximate the contour
                        epsilon = 0.04 * cv2.arcLength(contour, True)
                        approx = cv2.approxPolyDP(contour, epsilon, True)
                                
                                # If the contour has 4 vertices (square/rectangle)
                        if len(approx) == 4:
                                    # Calculate aspect ratio
                            x, y, w, h = cv2.boundingRect(approx)
                            aspect_ratio = float(w) / h
                                    
                                    # If it's approximately square (aspect ratio close to 1)
                            if 0.8 <= aspect_ratio <= 1.2:
                                        # Add to squares list with area
                                area = cv2.contourArea(contour)
                                squares.append((x, y, w, h, area))
                            
                            # Check if any squares were found
                    if squares:
                                # Sort by area (largest first)
                        squares.sort(key=lambda s: s[4], reverse=True)
                                
                                # Get the largest square
                        x, y, w, h, _ = squares[0]
                                
                                # Save a debug image with the square highlighted
                        debug_img = button_img.copy()
                        cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        debug_path = os.path.join(tempfile.gettempdir(), "debug_square.png")
                        cv2.imwrite(debug_path, debug_img)
                        logging.info(f"Saved debug image with detected square to {debug_path}")
                                
                                # Calculate center of the square
                        square_center_x = x + w // 2
                        square_center_y = y + h // 2
                                
                                # Calculate the absolute position to click
                        click_x = x_expanded + square_center_x
                        click_y = y_expanded + square_center_y
                                
                        logging.info(f"Detected square at ({x}, {y}) with size {w}x{h}")
                        logging.info(f"Clicking at calculated center point: ({click_x}, {click_y})")
                                
                                # Click at the center of the square
                        pyautogui.click(click_x, click_y)
                        logging.info("Clicked center of square in verify human button")
                    else:
                                # If no squares found, fall back to clicking the center of the button
                        logging.warning("No squares detected in button image, falling back to center click")
                        pyautogui.click(verify_human_button_position)
                        logging.info("Clicked verify human button (center)")
                except Exception as e:
                    logging.warning(f"Error during square detection: {str(e)}")
                            # Fall back to clicking the button directly
                    pyautogui.click(verify_human_button_position)
                    logging.info("Clicked verify human button (fallback after square detection error)")
                                    
                except Exception as e:
                    logging.warning(f"Error during OCR text verification: {str(e)}")
                            # If OCR fails, fall back to clicking based on image recognition only
                    logging.info("Falling back to image recognition only due to OCR error")
                    pyautogui.click(verify_human_button_position)
                    logging.info("Clicked verify human button (OCR verification failed)")
                    verify_human_button_found = True
                    break
                        
                        # If we reach here and text_verified is true, mark button as found
                if text_verified:
                    verify_human_button_found = True
                    break
                else:
                    logging.warning(f"Button found but text verification failed. Text: '{button_text}'")
                            # Continue to next confidence level without clicking
        except Exception as e:
            logging.warning(f"Error finding verify human button with confidence {confidence}: {str(e)}")


    time.sleep(5)

    # Step 8: Press TAB to move to View button, then ENTER
    pyautogui.press("tab")
    time.sleep(1)
    pyautogui.press("tab")
    time.sleep(1)
    pyautogui.press("tab")
    time.sleep(1)
    pyautogui.press("tab")
    time.sleep(1)
    pyautogui.press("tab")
    time.sleep(1)
    pyautogui.press("enter")
    time.sleep(4)

    pyautogui.press("tab")

    
    time.sleep(3)

    try:
        clipboard_process = subprocess.run(
            ["xclip", "-selection", "clipboard", "-o"], 
            capture_output=True, 
            text=True,
            env=dict(os.environ, DISPLAY=f":{display.display}")
        )
        api_key = clipboard_process.stdout.strip()
        logging.info(f"Copied API key from clipboard: {api_key[:4]}...{api_key[-4:]} (length {len(api_key)})")
   
    except Exception as clip_err:
        logging.warning(f"Error getting clipboard content with xclip: {clip_err}")    
    save_config("cloudflare_api_key", api_key)
    logging.info("Saved Cloudflare API key successfully.")




    time.sleep(5)

    quit_firefox()
    logging.info("Closed Firefox browser")



    ########################################################################

    # Open the browser in the virtual display with the SIGNUP_URL
    browser_process = launch_browser_in_virtual_display2(display)
    if not browser_process:
        logging.error("Failed to launch browser in virtual display")
        return False
        
    # Wait for browser to initialize but don't force full screen mode
    time.sleep(4)
    try:
        # Ensure we're NOT in full screen mode (press ESC to exit if we are)
        pyautogui.press('escape')
        logging.info("Ensured browser is not in full screen mode")
        time.sleep(2)
        
        # Take a screenshot showing the full browser window including address bar
        screenshot_path = os.path.join(os.getcwd(), "browser_startup.png")
        try:
            pyautogui.screenshot(screenshot_path)
            logging.info(f"Saved initial browser screenshot to {screenshot_path}")
        except Exception as ss_err:
            logging.warning(f"Failed to save initial screenshot: {ss_err}")
    except Exception as e:
        logging.warning(f"Error setting browser window mode: {str(e)}")

    # Page loading retry loop
    
    page_load_attempts = 0
    max_page_load_attempts = 3
    
    while page_load_attempts < max_page_load_attempts:
            logging.info(f"Page load attempt {page_load_attempts + 1}/{max_page_load_attempts}")


            verify_human_button_found = False
            confidence_levels = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4]  # Added even lower confidence level
                
            for confidence in confidence_levels:
                try:
                    logging.info(f"Looking for verify human button1 with confidence {confidence}...")
                    verify_human_button_position = pyautogui.locateOnScreen('verify_human_button2.png', confidence=confidence)
                    if verify_human_button_position:
                        logging.info(f"Verify human button found with confidence {confidence}")
                        

                        # Before clicking, verify the text on the button using OCR
                        try:
                            # Make sure pytesseract is installed
                            try:
                                import pytesseract
                            except ImportError:
                                logging.info("pytesseract not found, installing...")
                                subprocess.run(["pip", "install", "pytesseract"], check=True)
                                import pytesseract
                                
                            # Log the type and value of verify_human_button_position for debugging
                            logging.info(f"Button position type: {type(verify_human_button_position)}")
                            logging.info(f"Button position value: {verify_human_button_position}")
                            
                            # Extract coordinates from button position
                            try:
                                # Try to access as a Box object with attributes
                                x = verify_human_button_position.left
                                y = verify_human_button_position.top
                                width = verify_human_button_position.width
                                height = verify_human_button_position.height
                                logging.info(f"Accessed button position as Box object: {x}, {y}, {width}, {height}")
                            except AttributeError:
                                # If that fails, try to unpack as a tuple
                                try:
                                    x, y, width, height = verify_human_button_position
                                    logging.info(f"Unpacked button position as tuple: {x}, {y}, {width}, {height}")
                                except (ValueError, TypeError):
                                    # If both methods fail, log the error and fall back to clicking without OCR
                                    logging.error(f"Could not extract coordinates from button position: {verify_human_button_position}")
                                    pyautogui.click(verify_human_button_position)
                                    logging.info("Clicked verify human button (skipped OCR due to coordinate extraction error)")
                                    verify_human_button_found = True
                                    break
                            
                            # Ensure all values are integers
                            x = int(x)
                            y = int(y)
                            width = int(width)
                            height = int(height)
                            
                            # Add padding around the button (20 pixels on each side)
                            x_expanded = max(0, x - 20)
                            y_expanded = max(0, y - 20)
                            width_expanded = width + 40
                            height_expanded = height + 40
                            
                            # Take a screenshot of the expanded button area
                            # PyAutoGUI screenshot region must be (left, top, width, height)
                            logging.info("Taking screenshot of button area for OCR verification...")
                            logging.info(f"Screenshot region: {x_expanded}, {y_expanded}, {width_expanded}, {height_expanded}")
                            button_region = (x_expanded, y_expanded, width_expanded, height_expanded)
                            button_screenshot = pyautogui.screenshot(region=button_region)
                            
                            # Save the screenshot temporarily
                            temp_button_path = os.path.join(tempfile.gettempdir(), "temp_button.png")
                            button_screenshot.save(temp_button_path)
                            
                            # Use OCR to extract text from the button screenshot
                            button_text = pytesseract.image_to_string(temp_button_path).lower()
                            
                            # Log the extracted text for debugging
                            logging.info(f"OCR extracted text from button: '{button_text}'")
                            
                            # Check if the text contains expected phrases
                            expected_phrases = ["human", "verify you", "verify you ar", "verify", "human verification"]
                            text_verified = any(phrase in button_text for phrase in expected_phrases)
                        except Exception as e:
                            logging.warning(f"Error during OCR verification: {str(e)}")
                            # If OCR fails, fall back to clicking based on image recognition only
                            logging.info("Falling back to image recognition only due to OCR error")
                            pyautogui.click(verify_human_button_position)
                            logging.info("Clicked verify human button (OCR verification failed)")
                            verify_human_button_found = True
                            break
                    
                    if text_verified:
                        logging.info(f"Button text verified as containing expected phrases")
                        
                        # Now detect the square-shaped clickable element within the button area
                        try:
                            # Load the image with OpenCV
                            button_img = cv2.imread(temp_button_path)
                            if button_img is None:
                                raise ValueError("Failed to load button image with OpenCV")
                            
                            # Convert to grayscale
                            gray = cv2.cvtColor(button_img, cv2.COLOR_BGR2GRAY)
                            
                            # Apply thresholding to create a binary image
                            _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
                            
                            # Find contours
                            contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                            
                            # Filter contours to find squares
                            squares = []
                            for contour in contours:
                                # Approximate the contour
                                epsilon = 0.04 * cv2.arcLength(contour, True)
                                approx = cv2.approxPolyDP(contour, epsilon, True)
                                
                                # If the contour has 4 vertices (square/rectangle)
                                if len(approx) == 4:
                                    # Calculate aspect ratio
                                    x, y, w, h = cv2.boundingRect(approx)
                                    aspect_ratio = float(w) / h
                                    
                                    # If it's approximately square (aspect ratio close to 1)
                                    if 0.8 <= aspect_ratio <= 1.2:
                                        # Add to squares list with area
                                        area = cv2.contourArea(contour)
                                        squares.append((x, y, w, h, area))
                            
                            # Check if any squares were found
                            if squares:
                                # Sort by area (largest first)
                                squares.sort(key=lambda s: s[4], reverse=True)
                                
                                # Get the largest square
                                x, y, w, h, _ = squares[0]
                                
                                # Save a debug image with the square highlighted
                                debug_img = button_img.copy()
                                cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                                debug_path = os.path.join(tempfile.gettempdir(), "debug_square.png")
                                cv2.imwrite(debug_path, debug_img)
                                logging.info(f"Saved debug image with detected square to {debug_path}")
                                
                                # Calculate center of the square
                                square_center_x = x + w // 2
                                square_center_y = y + h // 2
                                
                                # Calculate the absolute position to click
                                click_x = x_expanded + square_center_x
                                click_y = y_expanded + square_center_y
                                
                                logging.info(f"Detected square at ({x}, {y}) with size {w}x{h}")
                                logging.info(f"Clicking at calculated center point: ({click_x}, {click_y})")
                                
                                # Click at the center of the square
                                pyautogui.click(click_x, click_y)
                                logging.info("Clicked center of square in verify human button")
                            else:
                                # If no squares found, fall back to clicking the center of the button
                                logging.warning("No squares detected in button image, falling back to center click")
                                pyautogui.click(verify_human_button_position)
                                logging.info("Clicked verify human button (center)")
                        except Exception as e:
                            logging.warning(f"Error during square detection: {str(e)}")
                            # Fall back to clicking the button directly
                            pyautogui.click(verify_human_button_position)
                            logging.info("Clicked verify human button (fallback after square detection error)")
                                    
                        except Exception as e:
                            logging.warning(f"Error during OCR text verification: {str(e)}")
                            # If OCR fails, fall back to clicking based on image recognition only
                            logging.info("Falling back to image recognition only due to OCR error")
                            pyautogui.click(verify_human_button_position)
                            logging.info("Clicked verify human button (OCR verification failed)")
                            verify_human_button_found = True
                            break
                        
                        # If we reach here and text_verified is true, mark button as found
                        if text_verified:
                            verify_human_button_found = True
                            break
                        else:
                            logging.warning(f"Button found but text verification failed. Text: '{button_text}'")
                            # Continue to next confidence level without clicking
                except Exception as e:
                    logging.warning(f"Error finding verify human button with confidence {confidence}: {str(e)}")


           
            time.sleep(17)  # Wait a bit for the page to stabilize
            # Wait for the email input field to appear
            email_input_field_image = 'email_input_field.png'
            email_input_field = None
            max_attempts = 10
            attempts = 0
            
            # Try multiple confidence levels for email input field detection
            confidence_levels = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4]  # Added even lower confidence level
            
            # Give the page more time to fully load before starting detection
            logging.info("Waiting for page to fully load...")
            time.sleep(5)
            
            while email_input_field is None and attempts < max_attempts:
                for confidence in confidence_levels:
                    try:
                        logging.info(f"Looking for email input field with confidence {confidence}...")
                        email_input_field = pyautogui.locateOnScreen(email_input_field_image, confidence=confidence)
                        if email_input_field:
                            logging.info(f"Detected email input field with confidence {confidence}")
                            break
                    except Exception as e:
                        logging.warning(f"Error detecting email input field with confidence {confidence}: {str(e)}")
                
                if email_input_field is None:
                    attempts += 1
                    logging.warning(f"Could not detect email input field (attempt {attempts}/{max_attempts})")
                    
                    # Try refreshing the page if we're halfway through our attempts
                    if attempts == max_attempts // 2:
                        logging.info("Refreshing page to try again...")
                        pyautogui.hotkey('ctrl', 'r')  # Firefox uses Ctrl+R for refresh
                        time.sleep(5)  # Wait for page to reload
                    else:
                        time.sleep(2)  # Longer wait between attempts
            
            # Check if we found the email input field
            if email_input_field is not None:
                # We found the email input field, break out of the page load retry loop
                break
            
            # If we couldn't find the email input field, try reloading the page
            page_load_attempts += 1
            if page_load_attempts < max_page_load_attempts:
                logging.warning("Could not detect email input field. Restarting browser...")
                
                # Close the current browser
                browser_process.terminate()
                time.sleep(2)
                
                # Open a new browser instance in the virtual display
                browser_process = launch_browser_in_virtual_display(display, url)
                if not browser_process:
                    logging.error("Failed to restart browser")
                    return False
                
                time.sleep(5)  # Wait for the browser to load
            else:
                logging.error("Could not detect email input field after multiple page load attempts")
                return False
        
        # At this point, we've successfully found the email input field
        # Now process the email (this is outside the page load retry loop)
        
    # Get email from config.txt file instead of bouncework.txt
    email2 = None
    try:
        # Try to read cloudflare_email from config.txt
        with open(CONFIG_FILE, "r") as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith("cloudflare_email2="):
                    email2 = line.split("=", 1)[1].strip()
                    logging.info(f"Found email in config.txt: {email2}")
                    break
    except Exception as e:
        logging.error(f"Error reading email from config.txt: {str(e)}")
    
    # If no email was found in config.txt, generate a random one for testing
    if not email2:
        logging.warning("No email found in config.txt, using a test email")
        email = f"test{random.randint(1000, 9999)}@example.com"
        save_config("cloudflare_email2", email2)

    # Click on the email input field and type the email
    pyautogui.click(email_input_field)
    pyautogui.typewrite(email2)
    pyautogui.press('tab')  # Move to the next field
    logging.info(f"Entered email: {email2}")

    # Give the page more time to load and stabilize
    time.sleep(3)

    # wait for email input to be processed
    time.sleep(3)
    # Generate password
    cloudflare_password2 = generate_password()
    logging.info(f"Generated cloudflare_password: {cloudflare_password2}")
    time.sleep(1)

    pyautogui.typewrite(cloudflare_password2, interval=0.05)
    logging.info(f"Typed password into verified password field")

    # Save password to config.txt
    save_config("cloudflare_password2", cloudflare_password2)
    logging.info("Saved cloudflare_password2 to config.txt")

    pyautogui.scroll(-500)
    time.sleep(1)
    pyautogui.scroll(-500)

    time.sleep(2)  # wait for page to stabilize after scrolling
    
    # Wait longer for the page to process and stabilize
    time.sleep(7)

    # Try to find the verify human button with multiple attempts and decreasing confidence
    verify_human_button_found = False
    confidence_levels = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4]  # Added even lower confidence level
    
    for confidence in confidence_levels:
        try:
            logging.info(f"Looking for verify human button with confidence {confidence}...")
            verify_human_button_position = pyautogui.locateOnScreen('verify_human_button.png', confidence=confidence)
            if verify_human_button_position:
                logging.info(f"Verify human button found with confidence {confidence}")
                
                # Before clicking, verify the text on the button using OCR
                try:
                    # Make sure pytesseract is installed
                    try:
                        import pytesseract
                    except ImportError:
                        logging.info("pytesseract not found, installing...")
                        subprocess.run(["pip", "install", "pytesseract"], check=True)
                        import pytesseract
                                
                    # Log the type and value of verify_human_button_position for debugging
                    logging.info(f"Button position type: {type(verify_human_button_position)}")
                    logging.info(f"Button position value: {verify_human_button_position}")
                    
                    # Handle different return types from locateOnScreen
                    # It could be a Box object or a tuple-like object
                    try:
                        # Try to access as a Box object with attributes
                        x = verify_human_button_position.left
                        y = verify_human_button_position.top
                        width = verify_human_button_position.width
                        height = verify_human_button_position.height
                        logging.info(f"Accessed button position as Box object: {x}, {y}, {width}, {height}")
                    except AttributeError:
                        # If that fails, try to unpack as a tuple
                        try:
                            x, y, width, height = verify_human_button_position
                            logging.info(f"Unpacked button position as tuple: {x}, {y}, {width}, {height}")
                        except (ValueError, TypeError):
                            # If both methods fail, log the error and fall back to clicking without OCR
                            logging.error(f"Could not extract coordinates from button position: {verify_human_button_position}")
                            pyautogui.click(verify_human_button_position)
                            logging.info("Clicked verify human button (skipped OCR due to coordinate extraction error)")
                            verify_human_button_found = True
                            break
                    
                    # Ensure all values are integers
                    x = int(x)
                    y = int(y)
                    width = int(width)
                    height = int(height)
                    
                    # Add padding around the button (20 pixels on each side)
                    x_expanded = max(0, x - 20)
                    y_expanded = max(0, y - 20)
                    width_expanded = width + 40
                    height_expanded = height + 40
                    
                    # Take a screenshot of the expanded button area
                    # PyAutoGUI screenshot region must be (left, top, width, height)
                    logging.info("Taking screenshot of button area for OCR verification...")
                    logging.info(f"Screenshot region: {x_expanded}, {y_expanded}, {width_expanded}, {height_expanded}")
                    button_region = (x_expanded, y_expanded, width_expanded, height_expanded)
                    button_screenshot = pyautogui.screenshot(region=button_region)
                    
                    # Save the screenshot temporarily
                    temp_button_path = os.path.join(tempfile.gettempdir(), "temp_button.png")
                    button_screenshot.save(temp_button_path)
                    
                    # Use OCR to extract text from the button screenshot
                    button_text = pytesseract.image_to_string(temp_button_path).lower()
                    
                    # Log the extracted text for debugging
                    logging.info(f"OCR extracted text from button: '{button_text}'")
                    
                    # Check if the text contains expected phrases
                    expected_phrases = ["human", "verify you", "verify you ar", "verify", "human verification"]
                    text_verified = any(phrase in button_text for phrase in expected_phrases)
                    import cv2
                    
                    if text_verified:
                        logging.info(f"Button text verified as containing expected phrases")
                        
                        # Now detect the square-shaped clickable element within the button area
                        try:
                            # Load the image with OpenCV
                            button_img = cv2.imread(temp_button_path)
                            if button_img is None:
                                raise ValueError("Failed to load button image with OpenCV")
                            
                            # Convert to grayscale
                            gray = cv2.cvtColor(button_img, cv2.COLOR_BGR2GRAY)
                            
                            # Apply thresholding to create a binary image
                            _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
                            
                            # Find contours
                            contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                            
                            # Filter contours to find squares
                            squares = []
                            for contour in contours:
                                # Approximate the contour
                                epsilon = 0.04 * cv2.arcLength(contour, True)
                                approx = cv2.approxPolyDP(contour, epsilon, True)
                                
                                # If the contour has 4 vertices (square/rectangle)
                                if len(approx) == 4:
                                    # Calculate aspect ratio
                                    x, y, w, h = cv2.boundingRect(approx)
                                    aspect_ratio = float(w) / h
                                    
                                    # If it's approximately square (aspect ratio close to 1)
                                    if 0.8 <= aspect_ratio <= 1.2:
                                        # Add to squares list with area
                                        area = cv2.contourArea(contour)
                                        squares.append((x, y, w, h, area))
                            
                            # If squares were found
                            if squares:
                                # Sort by area (largest first)
                                squares.sort(key=lambda s: s[4], reverse=True)
                                
                                # Get the largest square
                                x, y, w, h, _ = squares[0]
                                
                                # Save a debug image with the square highlighted
                                debug_img = button_img.copy()
                                cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                                debug_path = os.path.join(tempfile.gettempdir(), "debug_square.png")
                                cv2.imwrite(debug_path, debug_img)
                                logging.info(f"Saved debug image with detected square to {debug_path}")
                                
                                # Calculate center of the square
                                square_center_x = x + w // 2
                                square_center_y = y + h // 2
                                
                                # Calculate the absolute position to click
                                click_x = x_expanded + square_center_x
                                click_y = y_expanded + square_center_y
                                
                                logging.info(f"Detected square at ({x}, {y}) with size {w}x{h}")
                                logging.info(f"Clicking at calculated center point: ({click_x}, {click_y})")
                                
                                # Click at the center of the square
                                pyautogui.click(click_x, click_y)
                                logging.info("Clicked center of square in verify human button")
                            else:
                                # If no squares found, fall back to clicking the center of the button
                                logging.warning("No squares detected in button image, falling back to center click")
                                pyautogui.click(verify_human_button_position)
                                logging.info("Clicked verify human button (center)")
                        except Exception as e:
                            logging.warning(f"Error during square detection: {str(e)}")
                            # Fall back to clicking the button directly
                            pyautogui.click(verify_human_button_position)
                            logging.info("Clicked verify human button (fallback after square detection error)")
                        
                        verify_human_button_found = True
                        break
                    else:
                        logging.warning(f"Button found but text verification failed. Text: '{button_text}'")
                        # Continue to next confidence level without clicking
                except Exception as e:
                    logging.warning(f"Error during OCR text verification: {str(e)}")
                    # If OCR fails, fall back to clicking based on image recognition only
                    logging.info("Falling back to image recognition only due to OCR error")
                    pyautogui.click(verify_human_button_position)
                    logging.info("Clicked verify human button (OCR verification failed)")
                    verify_human_button_found = True
                    break
        except Exception as e:
            logging.warning(f"Error finding verify human button with confidence {confidence}: {str(e)}")
    
    # Wait for success sign
    time.sleep(12)  # Adjust the time as needed

    # After verify human button, look for sign_up_button
    
    # Try to find the sign_up_button with multiple attempts and decreasing confidence
    sign_up_button_found = False
    confidence_levels = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4]
                
    for confidence in confidence_levels:
        try:
            logging.info(f"Looking for sign_up_button with confidence {confidence}...")
            sign_up_button_position = pyautogui.locateOnScreen('signup_button_cloudflare.png', confidence=confidence)
            if sign_up_button_position:
                logging.info(f"Sign-up button found with confidence {confidence}")
                pyautogui.click(sign_up_button_position)
                logging.info("Clicked sign-up button")
                sign_up_button_found = True
                break
        except Exception as e:
            logging.warning(f"Error finding sign-up button with confidence {confidence}: {str(e)}")
    
    if not sign_up_button_found:
        logging.error("Could not find sign-up button after multiple attempts")
    
    
    time.sleep(32)  # Wait for any final processing


    logging.info("waiting for verification url2 to be ready...")




        # Human verify via PyAutoGUI
    time.sleep(6)
    
    # Open new tab in browser (Ctrl+T)
    pyautogui.hotkey('ctrl', 't')
    time.sleep(2)  # Wait for new tab to open

    # Read verification_url from config.txt
    
    
    start_time = time.time()
    timeout = 100  # 60 seconds timeout
    verification_url2 = None
    
    logging.info("Waiting for verification_url2 to appear in config.txt (timeout: 100 seconds)...")
    
    while time.time() - start_time < timeout:
        try:
            with open(CONFIG_FILE, "r") as f:
                config_data = dict(line.strip().split("=", 1) for line in f if "=" in line)
            
            verification_url2 = config_data.get("verification_url2")
            
            if verification_url2:
                logging.info(f"Found verification_url2 after {int(time.time() - start_time)} seconds")
                break
            
            # Wait for 2 seconds before checking again
            time.sleep(2)
            logging.info(f"Waiting for verification_url2... ({int(time.time() - start_time)} seconds elapsed)")
            
        except Exception as e:
            logging.warning(f"Error reading config.txt: {e}")
            time.sleep(2)
    
    if not verification_url:
        logging.error(f"verification_url2 missing in config.txt after {timeout} seconds timeout")
        return

# ✅ Remove verification_url2 from config_data
    del config_data["verification_url2"]

# ✅ Rewrite config.txt without that key
    with open(CONFIG_FILE, "w") as f:
        for key, value in config_data.items():
           f.write(f"{key}={value}\n")

    logging.info("Removed verification_url2 from config.txt after reading it")


    logging.info(f"Using verification URL: {verification_url2}")
    # Type the verification URL and press Enter
    pyautogui.typewrite(verification_url2)
    pyautogui.press('enter')
    logging.info(f"Visited verification URL: {verification_url2}")

    time.sleep(15)  # wait for signup to complete



    # Make sure to capture the full browser window including address bar
    try:
        # Take screenshot with explicit dimensions to ensure entire browser is captured
       
        
        # Process the specifically requested full_profilepage.png with OCR to extract text
        try:
            # Make sure pytesseract is installed
            try:
                import pytesseract
                import cv2
            except ImportError:
                logging.info("pytesseract or cv2 not found, installing...")
                subprocess.run(["pip", "install", "pytesseract opencv-python-headless"], check=True)
                import pytesseract
                import cv2
            
            # Make sure tesseract-ocr is installed (essential for OCR functionality)
            try:
                tesseract_check = subprocess.run(["which", "tesseract"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if tesseract_check.returncode != 0:
                    logging.info("tesseract-ocr not found, installing...")
                    subprocess.run(["sudo", "apt-get", "update", "-y"], check=False)
                    subprocess.run(["sudo", "apt-get", "install", "-y", "tesseract-ocr"], check=False)
                    logging.info("tesseract-ocr installation attempted")
            except Exception as e:
                logging.warning(f"Error checking/installing tesseract-ocr: {str(e)}")
            
            logging.info(f"Processing {full_profilepage_path} for text extraction with enhanced OCR...")
            
            # Try to directly copy the URL from the address bar first
            try:
                logging.info("Attempting to directly copy URL from address bar...")
                # Focus the address bar
                pyautogui.hotkey('ctrl', 'l')
                time.sleep(0.5)
                
                # Select all text in the address bar
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.5)
                
                # Copy the URL
                pyautogui.hotkey('ctrl', 'c')
                time.sleep(1)  # Give more time for copying
                
                # Check if clipboard tools are installed
                try:
                    # Ensure xclip is installed
                    subprocess.run(["which", "xclip"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                except subprocess.CalledProcessError:
                    logging.info("xclip not found, installing...")
                    subprocess.run(["sudo", "apt-get", "update"], check=False)
                    subprocess.run(["sudo", "apt-get", "install", "-y", "xclip"], check=False)
                
                # Try to get URL from clipboard using xclip
                try:
                    clipboard_process = subprocess.run(
                        ["xclip", "-selection", "clipboard", "-o"], 
                        capture_output=True, 
                        text=True,
                        env=dict(os.environ, DISPLAY=f":{display.display}")
                    )
                    direct_url2 = clipboard_process.stdout.strip()
                    
                    if direct_url2 and ('http' in direct_url2.lower() or 'cloudflare' in direct_url2.lower()):
                        logging.info(f"Successfully copied URL directly from address bar: {direct_url2}")
                        # Save the URL to a variable for later use
                        extracted_url = direct_url2
                        
                        # Extract account ID from URL and save to config
                        try:
                            # Extract account ID using regex pattern
                            account_id_match2 = re.search(r'dash\.cloudflare\.com/([a-zA-Z0-9]+)', direct_url2)
                            if account_id_match2:
                                account_id2 = account_id_match2.group(1)
                                logging.info(f"Extracted Cloudflare account ID: {account_id2}")

                                # Save the account ID to config.txt
                                save_config("cloudflare_account_id2", account_id2)
                                logging.info("Saved account_id2 to config.txt")
                            else:
                                logging.warning("Could not extract account ID from URL")
                        except Exception as e:
                            logging.error(f"Error extracting or saving account ID: {e}")
                    else:
                        logging.warning(f"Clipboard content doesn't appear to be a valid URL: '{direct_url2}'")
                except Exception as clip_err:
                    logging.warning(f"Error getting clipboard content with xclip: {clip_err}")
            except Exception as copy_err:
                logging.warning(f"Error during direct URL copying: {copy_err}")
            
            
                
        except Exception as ocr_err:
            logging.error(f"Failed to extract text from screenshot: {ocr_err}")
            logging.error(f"OCR error details: {traceback.format_exc()}")
            logging.error("Make sure tesseract-ocr is properly installed on your system")
            
           
    except Exception as ss_err:
        logging.error(f"Failed to save profile page screenshot: {ss_err}")

    time.sleep(5)
    # Step 4: Navigate to API tokens page
    api_tokens_url = "https://dash.cloudflare.com/profile/api-tokens"
    open_new_tab_in_firefox(api_tokens_url)

    time.sleep(5)

    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("enter")
    logging.info("Clicked 'View' button for Global API Key")


 
    time.sleep(10)

    # Step 6: Focus password input
    pyautogui.press("tab")
    time.sleep(2)

    # Step 7: Read password from config.txt and type it
    cloudflare_password = get_config("cloudflare_password2")
    if not cloudflare_password:
        logging.error("Cloudflare password not found in config.txt")
        return
    pyautogui.typewrite(cloudflare_password, interval=0.05)
    logging.info("Typed Cloudflare password")

    time.sleep(7)

    

    verify_human_button_found = False
    confidence_levels = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4]  # Added even lower confidence level
                
    for confidence in confidence_levels:
        try:
            logging.info(f"Looking for verify human button1 with confidence {confidence}...")
            verify_human_button_position = pyautogui.locateOnScreen('verify_human3.png', confidence=confidence)
            if verify_human_button_position:
                logging.info(f"Verify human button found with confidence {confidence}")
                        

                        # Before clicking, verify the text on the button using OCR
                try:
                            # Make sure pytesseract is installed
                    try:
                        import pytesseract
                    except ImportError:
                        logging.info("pytesseract not found, installing...")
                        subprocess.run(["pip", "install", "pytesseract"], check=True)
                        import pytesseract
                                
                            # Log the type and value of verify_human_button_position for debugging
                    logging.info(f"Button position type: {type(verify_human_button_position)}")
                    logging.info(f"Button position value: {verify_human_button_position}")
                            
                            # Extract coordinates from button position
                    try:
                                # Try to access as a Box object with attributes
                        x = verify_human_button_position.left
                        y = verify_human_button_position.top
                        width = verify_human_button_position.width
                        height = verify_human_button_position.height
                        logging.info(f"Accessed button position as Box object: {x}, {y}, {width}, {height}")
                    except AttributeError:
                                # If that fails, try to unpack as a tuple
                        try:
                            x, y, width, height = verify_human_button_position
                            logging.info(f"Unpacked button position as tuple: {x}, {y}, {width}, {height}")
                        except (ValueError, TypeError):
                                    # If both methods fail, log the error and fall back to clicking without OCR
                            logging.error(f"Could not extract coordinates from button position: {verify_human_button_position}")
                            pyautogui.click(verify_human_button_position)
                            logging.info("Clicked verify human button (skipped OCR due to coordinate extraction error)")
                            verify_human_button_found = True
                            break
                            
                            # Ensure all values are integers
                    x = int(x)
                    y = int(y)
                    width = int(width)
                    height = int(height)
                            
                            # Add padding around the button (20 pixels on each side)
                    x_expanded = max(0, x - 20)
                    y_expanded = max(0, y - 20)
                    width_expanded = width + 40
                    height_expanded = height + 40
                            
                            # Take a screenshot of the expanded button area
                            # PyAutoGUI screenshot region must be (left, top, width, height)
                    logging.info("Taking screenshot of button area for OCR verification...")
                    logging.info(f"Screenshot region: {x_expanded}, {y_expanded}, {width_expanded}, {height_expanded}")
                    button_region = (x_expanded, y_expanded, width_expanded, height_expanded)
                    button_screenshot = pyautogui.screenshot(region=button_region)
                            
                            # Save the screenshot temporarily
                    temp_button_path = os.path.join(tempfile.gettempdir(), "temp_button.png")
                    button_screenshot.save(temp_button_path)
                            
                            # Use OCR to extract text from the button screenshot
                    button_text = pytesseract.image_to_string(temp_button_path).lower()
                            
                            # Log the extracted text for debugging
                    logging.info(f"OCR extracted text from button: '{button_text}'")
                            
                            # Check if the text contains expected phrases
                    expected_phrases = ["human", "verify you", "verify you ar", "verify", "human verification"]
                    text_verified = any(phrase in button_text for phrase in expected_phrases)
                except Exception as e:
                    logging.warning(f"Error during OCR verification: {str(e)}")
                            # If OCR fails, fall back to clicking based on image recognition only
                    logging.info("Falling back to image recognition only due to OCR error")
                    pyautogui.click(verify_human_button_position)
                    logging.info("Clicked verify human button (OCR verification failed)")
                    verify_human_button_found = True
                    break
                    
            if text_verified:
                logging.info(f"Button text verified as containing expected phrases")
                        
                        # Now detect the square-shaped clickable element within the button area
                try:
                            # Load the image with OpenCV
                    button_img = cv2.imread(temp_button_path)
                    if button_img is None:
                        raise ValueError("Failed to load button image with OpenCV")
                            
                            # Convert to grayscale
                    gray = cv2.cvtColor(button_img, cv2.COLOR_BGR2GRAY)
                            
                            # Apply thresholding to create a binary image
                    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
                            
                            # Find contours
                    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                            
                            # Filter contours to find squares
                    squares = []
                    for contour in contours:
                                # Approximate the contour
                        epsilon = 0.04 * cv2.arcLength(contour, True)
                        approx = cv2.approxPolyDP(contour, epsilon, True)
                                
                                # If the contour has 4 vertices (square/rectangle)
                        if len(approx) == 4:
                                    # Calculate aspect ratio
                            x, y, w, h = cv2.boundingRect(approx)
                            aspect_ratio = float(w) / h
                                    
                                    # If it's approximately square (aspect ratio close to 1)
                            if 0.8 <= aspect_ratio <= 1.2:
                                        # Add to squares list with area
                                area = cv2.contourArea(contour)
                                squares.append((x, y, w, h, area))
                            
                            # Check if any squares were found
                    if squares:
                                # Sort by area (largest first)
                        squares.sort(key=lambda s: s[4], reverse=True)
                                
                                # Get the largest square
                        x, y, w, h, _ = squares[0]
                                
                                # Save a debug image with the square highlighted
                        debug_img = button_img.copy()
                        cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        debug_path = os.path.join(tempfile.gettempdir(), "debug_square.png")
                        cv2.imwrite(debug_path, debug_img)
                        logging.info(f"Saved debug image with detected square to {debug_path}")
                                
                                # Calculate center of the square
                        square_center_x = x + w // 2
                        square_center_y = y + h // 2
                                
                                # Calculate the absolute position to click
                        click_x = x_expanded + square_center_x
                        click_y = y_expanded + square_center_y
                                
                        logging.info(f"Detected square at ({x}, {y}) with size {w}x{h}")
                        logging.info(f"Clicking at calculated center point: ({click_x}, {click_y})")
                                
                                # Click at the center of the square
                        pyautogui.click(click_x, click_y)
                        logging.info("Clicked center of square in verify human button")
                    else:
                                # If no squares found, fall back to clicking the center of the button
                        logging.warning("No squares detected in button image, falling back to center click")
                        pyautogui.click(verify_human_button_position)
                        logging.info("Clicked verify human button (center)")
                except Exception as e:
                    logging.warning(f"Error during square detection: {str(e)}")
                            # Fall back to clicking the button directly
                    pyautogui.click(verify_human_button_position)
                    logging.info("Clicked verify human button (fallback after square detection error)")
                                    
                except Exception as e:
                    logging.warning(f"Error during OCR text verification: {str(e)}")
                            # If OCR fails, fall back to clicking based on image recognition only
                    logging.info("Falling back to image recognition only due to OCR error")
                    pyautogui.click(verify_human_button_position)
                    logging.info("Clicked verify human button (OCR verification failed)")
                    verify_human_button_found = True
                    break
                        
                        # If we reach here and text_verified is true, mark button as found
                if text_verified:
                    verify_human_button_found = True
                    break
                else:
                    logging.warning(f"Button found but text verification failed. Text: '{button_text}'")
                            # Continue to next confidence level without clicking
        except Exception as e:
            logging.warning(f"Error finding verify human button with confidence {confidence}: {str(e)}")


    time.sleep(5)

    # Step 8: Press TAB to move to View button, then ENTER
    pyautogui.press("tab")
    time.sleep(1)
    pyautogui.press("tab")
    time.sleep(1)
    pyautogui.press("tab")
    time.sleep(1)
    pyautogui.press("tab")
    time.sleep(1)
    pyautogui.press("tab")
    time.sleep(1)
    pyautogui.press("enter")
    time.sleep(4)

    pyautogui.press("tab")

    
    time.sleep(3)

    try:
        clipboard_process = subprocess.run(
            ["xclip", "-selection", "clipboard", "-o"], 
            capture_output=True, 
            text=True,
            env=dict(os.environ, DISPLAY=f":{display.display}")
        )
        api_key2 = clipboard_process.stdout.strip()
        logging.info(f"Copied API key from clipboard: {api_key2[:4]}...{api_key2[-4:]} (length {len(api_key2)})")

    except Exception as clip_err:
        logging.warning(f"Error getting clipboard content with xclip: {clip_err}")    
    save_config("cloudflare_api_key2", api_key2)
    logging.info("Saved Cloudflare API key2 successfully.")


    time.sleep(5)  




    
    # Run update_workers_subdomain.js first
    logging.info("Starting update_workers_subdomain.js...")
    try:
        workers_subdomain_process = subprocess.run(["node", "update_workers_subdomain.cjs"], 
                                                  capture_output=True, 
                                                  text=True)
        
        if workers_subdomain_process.returncode == 0:
            logging.info("update_workers_subdomain.js completed successfully")
            logging.info(f"Output: {workers_subdomain_process.stdout.strip()}")
        else:
            logging.error(f"update_workers_subdomain.js failed with return code {workers_subdomain_process.returncode}")
            logging.error(f"Error: {workers_subdomain_process.stderr.strip()}")
    except Exception as e:
        logging.error(f"Error running update_workers_subdomain.cjs: {str(e)}")

    # Run deploy.js in a subprocess
    logging.info("Starting deploy.js...")
    try:
        deploy_process = subprocess.Popen(["node", "deploy.cjs"], 
                                         stdin=subprocess.PIPE, 
                                         stdout=subprocess.PIPE, 
                                         stderr=subprocess.PIPE, 
                                         text=True)
        
        # Write the user-provided Heroku URL to the process stdin
        logging.info(f"Passing Heroku URL to deploy.js: {heroku_url}")
        deploy_process.stdin.write(f"{heroku_url}\n")
        deploy_process.stdin.flush()
        
        # Wait for the process to complete
        stdout, stderr = deploy_process.communicate()
        
        if deploy_process.returncode == 0:
            logging.info("deploy.js completed successfully")
            logging.info(f"Output: {stdout.strip()}")
        else:
            logging.error(f"deploy.js failed with return code {deploy_process.returncode}")
            logging.error(f"Error: {stderr.strip()}")
    except Exception as e:
        logging.error(f"Error running deploy.js: {str(e)}")
    
    # Run cloudflare_turnstile_api.py in a subprocess
    logging.info("Starting cloudflare_turnstile_api.py...")
    try:
        turnstile_process = subprocess.run(["python3", "cloudflare_turnstile_api.py"], 
                                          capture_output=True, 
                                          text=True)
        
        if turnstile_process.returncode == 0:
            logging.info("cloudflare_turnstile_api.py completed successfully")
            logging.info(f"Output: {turnstile_process.stdout.strip()}")
        else:
            logging.error(f"cloudflare_turnstile_api.py failed with return code {turnstile_process.returncode}")
            logging.error(f"Error: {turnstile_process.stderr.strip()}")
    except Exception as e:
        logging.error(f"Error running cloudflare_turnstile_api.py: {str(e)}")
    
    # Run update_turnstile_keys.js in a subprocess
    logging.info("Starting update_turnstile_keys.js...")
    try:
        update_keys_process = subprocess.run(["node", "update_turnstile_keys.cjs"], 
                                           capture_output=True, 
                                           text=True)
        
        if update_keys_process.returncode == 0:
            logging.info("update_turnstile_keys.js completed successfully")
            logging.info(f"Output: {update_keys_process.stdout.strip()}")
        else:
            logging.error(f"update_turnstile_keys.js failed with return code {update_keys_process.returncode}")
            logging.error(f"Error: {update_keys_process.stderr.strip()}")
    except Exception as e:
        logging.error(f"Error running update_turnstile_keys.js: {str(e)}")

    time.sleep(5)



    # Process complete - function will return after a single run now
    logging.info("Process completed successfully")
    return True




def click_verify_checkbox3(template_path="verify_human3.png"):
    # Step 1: Try locating the image with multiple confidence levels
    location = locate_with_confidences(template_path)
    if not location:
        return False

    # Ensure all coords are ints
    region = (int(location.left), int(location.top), int(location.width), int(location.height))

    # Step 2: Screenshot that region
    screenshot = pyautogui.screenshot(region=region)
    screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    # Step 3: Convert to grayscale and detect contours
    gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    checkbox_center = None
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        aspect_ratio = float(w) / h

        # Looking for a square-ish small box
        if 15 < w < 50 and 15 < h < 50 and 0.8 < aspect_ratio < 1.2:
            checkbox_center = (region[0] + x + w//2, region[1] + y + h//2)
            logging.info(f"Checkbox found at {checkbox_center}")
            break

    # Step 4: Click the checkbox center
    if checkbox_center:
        pyautogui.moveTo(checkbox_center[0], checkbox_center[1], duration=0.3)
        pyautogui.click()
        logging.info("Clicked inside square checkbox successfully")
        return True
    else:
        logging.warning("Could not detect checkbox inside verify_human.png")
        # Fallback: click middle of whole image
        pyautogui.click(region[0] + region[2]//2, region[1] + region[3]//2)
        logging.info("Fallback: clicked center of verify_human.png")
        return False

def locate_and_click_with_text_verification(image_path, expected_text, description="", click_offset=(0,0)):
    """
    Locate an image, verify it contains the expected text using OCR, and click it if both conditions are met.
    
    Args:
        image_path (str): Path to the image to locate
        expected_text (str): Text that should be present in the button/element
        description (str): Description of the element for logging
        click_offset (tuple): Optional offset to apply to the click coordinates
        
    Returns:
        bool: True if element was found, verified, and clicked; False otherwise
    """
    logging.info(f"Looking for {description} containing text '{expected_text}'...")
    
    # Check if image file exists
    if not os.path.exists(image_path):
        logging.error(f"Image file not found: {image_path}")
        return False
    
    # Try different confidence levels
    confidence_levels = [0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5, 0.45, 0.4]
    
    for confidence in confidence_levels:
        try:
            logging.info(f"Trying confidence level {confidence} for {description}...")
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            
            if location:
                logging.info(f"Found potential match for {description} with confidence {confidence}")
                
                # Extract coordinates
                try:
                    # Try to access as a Box object with attributes
                    x = location.left
                    y = location.top
                    width = location.width
                    height = location.height
                except AttributeError:
                    # If that fails, try to unpack as a tuple
                    try:
                        x, y, width, height = location
                    except (ValueError, TypeError):
                        logging.error(f"Could not extract coordinates from location: {location}")
                        continue
                
                # Add padding around the button for better OCR results
                padding = 10
                x_expanded = max(0, int(x) - padding)
                y_expanded = max(0, int(y) - padding)
                width_expanded = int(width) + (padding * 2)
                height_expanded = int(height) + (padding * 2)
                
                # Take a screenshot of the expanded button area
                button_region = (x_expanded, y_expanded, width_expanded, height_expanded)
                try:
                    # Save button screenshot for OCR
                    button_screenshot = pyautogui.screenshot(region=button_region)
                    temp_button_path = os.path.join(tempfile.gettempdir(), f"temp_button_{confidence}.png")
                    button_screenshot.save(temp_button_path)
                    
                    # Perform OCR to extract text
                    # Try multiple OCR configurations for better results
                    ocr_configs = [
                        r'--oem 3 --psm 7',  # Single line of text
                        r'--oem 3 --psm 8',  # Single word
                        r'--oem 3 --psm 6',  # Assume a single uniform block of text
                    ]
                    
                    text_found = False
                    extracted_texts = []
                    
                    for config in ocr_configs:
                        try:
                            button_text = pytesseract.image_to_string(temp_button_path, config=config).lower()
                            extracted_texts.append(button_text)
                            logging.info(f"OCR extracted text with config '{config}': '{button_text}'")
                            
                            # Check if the expected text is in the OCR result
                            if expected_text.lower() in button_text.lower():
                                logging.info(f"✓ Text verification passed: Found '{expected_text}' in button")
                                text_found = True
                                break
                                
                            # Also try fuzzy matching for better accuracy
                            for word in button_text.split():
                                if fuzz.ratio(word.lower(), expected_text.lower()) > 80:
                                    logging.info(f"✓ Text verification passed (fuzzy match): '{word}' ~ '{expected_text}'")
                                    text_found = True
                                    break
                                    
                        except Exception as ocr_err:
                            logging.warning(f"OCR error with config '{config}': {ocr_err}")
                    
                    # If text verification passed, click the button
                    if text_found:
                        # Click at the center of the original location
                        click_x, click_y = pyautogui.center(location)
                        pyautogui.click(click_x + click_offset[0], click_y + click_offset[1])
                        logging.info(f"Clicked {description} after text verification")
                        return True
                    else:
                        logging.warning(f"Text verification failed: '{expected_text}' not found in extracted texts")
                        logging.warning(f"Found texts: {extracted_texts}")
                        # Don't return False yet, keep trying other confidence levels
                        
                except Exception as screenshot_err:
                    logging.warning(f"Error taking or processing button screenshot: {screenshot_err}")
            
        except Exception as e:
            logging.warning(f"Error at confidence {confidence}: {e}")
    
    # If we get here, we've tried all confidence levels and failed
    logging.error(f"Could not find {description} with text verification after trying all confidence levels")
    return False

def locate_and_click(image_path, description="", click_offset=(0,0)):
    """Locate an image using locate_with_confidences and click it if found."""
    logging.info(f"Locating {description}...")
    location = locate_with_confidences(image_path)
    if location:
        x, y = pyautogui.center(location)
        pyautogui.click(x + click_offset[0], y + click_offset[1])
        logging.info(f"Clicked {description}")
        return True
    else:
        logging.error(f"Could not find {description}")
        return False
    










def locate_with_confidences(image_path, confidences=[0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5, 0.45, 0.4], debug=False):
    """Locate an image with multiple confidence levels and optional debugging"""
    # First check if the image file exists
    if not os.path.exists(image_path):
        logging.error(f"Image file not found: {image_path}")
        return None
    
    # Take a full screenshot for debugging if requested
    if debug:
        try:
            screen = pyautogui.screenshot()
            screen.save(f"debug_screen_before_{os.path.basename(image_path)}")
            logging.info(f"Saved debug screenshot before search")
        except Exception as e:
            logging.error(f"Failed to save debug screenshot: {e}")
    
    # Try different confidence levels
    for conf in confidences:
        try:
            location = pyautogui.locateOnScreen(image_path, confidence=conf)
            if location:
                logging.info(f"Image {image_path} found with confidence {conf} at {location}")
                
                # If debug is enabled, save a screenshot of the match area
                if debug:
                    try:
                        # Take a screenshot of the match area
                        match_area = pyautogui.screenshot(region=(
                            int(location.left), 
                            int(location.top), 
                            int(location.width), 
                            int(location.height)
                        ))
                        debug_path = f"debug_match_{os.path.basename(image_path)}"
                        match_area.save(debug_path)
                        logging.info(f"Saved match area as {debug_path}")
                    except Exception as e:
                        logging.error(f"Failed to save match screenshot: {e}")
                
                return location
        except Exception as e:
            logging.error(f"Error at confidence {conf}: {e}")
    
    logging.warning(f"Image {image_path} not found with any confidence level")
    
    # Save final screenshot for debugging if requested
    if debug:
        try:
            screen = pyautogui.screenshot()
            screen.save(f"debug_screen_after_fail_{os.path.basename(image_path)}")
            logging.info(f"Saved debug screenshot after failed search")
        except Exception as e:
            logging.error(f"Failed to save debug screenshot: {e}")
    
    return None


def get_config(key):
    """Retrieve value from config.txt by key."""
    try:
        with open(CONFIG_FILE, "r") as f:
            for line in f:
                if line.startswith(f"{key}="):
                    return line.strip().split("=", 1)[1]
    except FileNotFoundError:
        return None
    return None

def open_new_tab_in_firefox(url):
    """Open a new tab in the currently active Firefox browser and navigate to the given URL."""
    logging.info(f"Opening new tab in Firefox: {url}")

    # Open a new tab
    pyautogui.hotkey("ctrl", "t")
    time.sleep(1)

    # Ensure we have focus in the new tab
    pyautogui.press('escape')  # Close any potential popups
    time.sleep(0.5)
    
    # Try multiple methods to navigate to the URL
    successful = False
    
    # Method 1: Direct typing method (most reliable)
    try:
        logging.info("Using direct typing method (primary)...")
        # Focus and clear the address bar
        pyautogui.hotkey("ctrl", "l")  # Focus address bar
        time.sleep(0.5)
        pyautogui.hotkey("ctrl", "a")  # Select all text
        time.sleep(0.5)
        pyautogui.press("delete")
        time.sleep(0.5)
        
        # Type URL character by character with longer pauses between characters
        pyautogui.typewrite(url, interval=0.08)  # Slower typing to ensure accuracy
        time.sleep(1)
        pyautogui.press("enter")
        logging.info("Navigated to URL using direct typing method")
        successful = True
    except Exception as e:
        logging.warning(f"Direct typing navigation failed: {e}")
    
    # Method 2: Try clipboard method with xclip and xsel
    if not successful:
        try:
            # Check and install both clipboard tools
            logging.info("Checking for clipboard tools...")
            subprocess.run(["sudo", "apt-get", "install", "-y", "xclip", "xsel"], check=False)
            
            try:
                # Try with custom environment variables for clipboard
                env = os.environ.copy()
                env['DISPLAY'] = os.environ.get('DISPLAY', ':0')
                
                # Write URL to file and use xsel to load it into clipboard
                temp_url_file = os.path.join(tempfile.gettempdir(), "url.txt")
                with open(temp_url_file, 'w') as f:
                    f.write(url)
                
                # Try using xsel directly
                subprocess.run(["xsel", "-i", "-b", "<", temp_url_file], env=env, check=False)
                
                # Try clipboard paste
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.5)
                pyautogui.press("enter")
                logging.info("Attempted URL navigation using xsel method")
                successful = True
            except Exception as e:
                logging.warning(f"xsel clipboard method failed: {e}")
        except Exception as e:
            logging.warning(f"Error setting up clipboard tools: {e}")
    
    # Method 3: JavaScript console method
    if not successful:
        try:
            logging.info("Using developer console method...")
            # Open developer console
            pyautogui.hotkey("f12")
            time.sleep(1.5)
            
            # Focus on console input and clear previous content
            pyautogui.hotkey("esc")  # Close any popups
            time.sleep(0.5)
            pyautogui.press("escape")  # Close any notifications
            time.sleep(0.5)
            pyautogui.hotkey("ctrl", "shift", "k")  # Firefox console shortcut
            time.sleep(1.5)
            
            # Clear any existing text
            pyautogui.hotkey("ctrl", "a")
            pyautogui.press("delete")
            time.sleep(0.5)
            
            # Type JavaScript to navigate without backslash issues - no f-strings
            # Create the command string in parts to avoid f-string syntax errors
            js_command = 'window.location.href = "'
            js_command += url.replace('"', '\\"')  # Escape double quotes in URL
            js_command += '"'
            pyautogui.typewrite(js_command, interval=0.05)
            time.sleep(1)
            pyautogui.press("enter")
            logging.info("Navigated to URL using developer console method")
            
            # Close developer tools
            time.sleep(1)
            pyautogui.hotkey("f12")
            successful = True
        except Exception as e:
            logging.warning(f"Developer console navigation failed: {e}")
    
    # Method 4: Enhanced basic fallback with multiple attempts at different positions
    if not successful:
        try:
            logging.info("Using enhanced basic fallback method...")
            
            # Try multiple positions for address bar (might vary based on Firefox version/theme)
            address_bar_positions = [
                (400, 60),   # Standard position
                (600, 60),   # Further right
                (800, 60),   # Even further right
                (400, 40),   # Higher up
                (600, 40)    # Higher and further right
            ]
            
            for position in address_bar_positions:
                try:
                    # Click on address bar position
                    pyautogui.click(position[0], position[1])
                    time.sleep(0.5)
                    
                    # Clear existing content
                    pyautogui.hotkey("ctrl", "a")
                    pyautogui.press("delete")
                    time.sleep(0.5)
                    
                    # Type URL with careful pacing
                    pyautogui.typewrite(url, interval=0.1)  # Even slower typing
                    time.sleep(1)
                    pyautogui.press("enter")
                    logging.info(f"Attempted navigation using position {position}")
                    break  # Stop after first attempt to avoid too many clicks
                except Exception as e:
                    logging.warning(f"Position {position} failed: {e}")
        except Exception as e:
            logging.error(f"All fallback navigation attempts failed: {e}")
    
    # Give more time for the page to load
    logging.info("Waiting for page to load...")
    time.sleep(12)  # Increased wait time for page load


if __name__ == "__main__":
    # Create test files if they don't exist
    create_test_files()
    
    # Generate a unique instance ID
    instance_id = generate_instance_id()
    
    # Display is already set up at the top of the file
    try:
        # Log the current progress at startup
        stats = get_progress_stats()
        logging.info(f"Starting with: {stats['valid']} valid, {stats['invalid']} invalid, "
                    f"{stats['unknown']} unknown, {stats['bouncework']} to process")
        
        # Save the instance ID to a file for reference
        with open('instance_id.txt', 'w') as f:
            f.write(f"Instance ID: {instance_id}\n")
            f.write(f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Display the instance ID
        logging.info("\n=== EMAIL VERIFIER INSTANCE INFORMATION ===")
        logging.info(f"Instance ID: {instance_id}")
        logging.info("This ID has been saved to instance_id.txt")
        logging.info("===============================\n")
        
        # Run the main process once instead of in a loop
        try:
            result = main_process(display)
            if result is False:
                logging.error("Main process failed. Exiting.")
            
            # Log progress after processing is complete
            stats = get_progress_stats()
            logging.info(f"Process completed with: {stats['valid']} valid, {stats['invalid']} invalid, "
                        f"{stats['unknown']} unknown, {stats['bouncework']} to process")
            
        except KeyboardInterrupt:
            logging.info("Process interrupted by user. Exiting.")
        except Exception as e:
            logging.error(f"An error occurred: {str(e)}")
            logging.error(traceback.format_exc())
            # Close any running Firefox processes
            subprocess.run(["pkill", "firefox"], stderr=subprocess.PIPE)
    finally:
        # Make sure to stop the virtual display when done
        if display:
            display.stop()
            logging.info("Virtual display stopped")
        
        # Make sure Firefox is closed
        subprocess.run(["pkill", "firefox"], stderr=subprocess.PIPE)
