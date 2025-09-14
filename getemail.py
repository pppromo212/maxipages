import time
import subprocess
import logging
import os
import traceback
import signal
import platform
import sys
import threading

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import random
import string

# Custom logger to reduce noise
app_logger = logging.getLogger('app')
app_logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - [EMAIL] - %(message)s')
handler.setFormatter(formatter)
app_logger.addHandler(handler)

# Suppress other loggers
logging.getLogger().setLevel(logging.WARNING)
selenium_logger = logging.getLogger('selenium')
selenium_logger.setLevel(logging.ERROR)
urllib3_logger = logging.getLogger('urllib3')
urllib3_logger.setLevel(logging.ERROR)

# Paths for Ubuntu VPS - Check multiple possible Chrome/Chromium binary locations
chrome_binaries = [
    "/usr/bin/chromium-browser",  # Ubuntu's Chromium package
    "/usr/bin/chromium",          # Alternative Chromium name
    "/usr/bin/google-chrome",     # Google Chrome if installed
    "/snap/bin/chromium",         # Snap Chromium package
    "/snap/bin/google-chrome"     # Snap Google Chrome package
]
chrome_path = None
for binary in chrome_binaries:
    if os.path.exists(binary):
        chrome_path = binary
        app_logger.info(f"Found Chrome/Chromium binary at: {chrome_path}")
        break

# Create profile directory
chrome_profile = os.path.expanduser("~/chrome_debug_profile")
os.makedirs(chrome_profile, exist_ok=True)

url = "https://premium.emailnator.com/login"

GNATOR_EMAIL = "jhnccts@gmail.com"
GNATOR_PASSWORD = "Pass12345"

CONFIG_FILE = "config.txt"

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
    
    app_logger.info(f"Saved {key}={value} to config.txt")

def setup_chrome_in_headless_mode():
    """Start Chrome in headless mode and return the driver"""
    app_logger.info("Setting up Chrome in headless mode...")
    
    global chrome_path
    
    # If no Chrome binary was found during initialization, try to install one
    if not chrome_path:
        app_logger.warning("No Chrome/Chromium binary found. Attempting to install Chromium...")
        try:
            # Try to install Chromium
            subprocess.run(["sudo", "apt-get", "update"], check=True)
            subprocess.run(["sudo", "apt-get", "install", "-y", "chromium-browser"], check=True)
            
            # Check if installation succeeded
            if os.path.exists("/usr/bin/chromium-browser"):
                chrome_path = "/usr/bin/chromium-browser"
                app_logger.info(f"Successfully installed Chromium at {chrome_path}")
            else:
                # Try alternative package name
                subprocess.run(["sudo", "apt-get", "install", "-y", "chromium"], check=True)
                if os.path.exists("/usr/bin/chromium"):
                    chrome_path = "/usr/bin/chromium"
                    app_logger.info(f"Successfully installed Chromium at {chrome_path}")
                else:
                    app_logger.error("Failed to install Chromium. Unable to proceed.")
                    raise Exception("No Chrome/Chromium binary found and installation failed")
        except Exception as e:
            app_logger.error(f"Error installing Chromium: {e}")
            app_logger.error("Attempting to use Firefox as fallback...")
            return setup_firefox_in_headless_mode()
    
    options = Options()
    options.add_argument("--headless=new")  # New headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--incognito")
    
    # Ensure we're using the display from the virtual display if available
    if 'DISPLAY' in os.environ:
        app_logger.info(f"Using display: {os.environ['DISPLAY']}")
    else:
        # Use display :99 if not set (likely to be the virtual display)
        os.environ["DISPLAY"] = ":99"
        app_logger.info("Set DISPLAY=:99 for virtual display environment")
    
    # Set the binary location
    options.binary_location = chrome_path
    app_logger.info(f"Using Chrome/Chromium binary at: {chrome_path}")
    
    try:
        driver = webdriver.Chrome(options=options)
        app_logger.info("Chrome/Chromium started successfully in headless mode")
        return driver
    except Exception as e:
        app_logger.error(f"Failed to start Chrome/Chromium: {e}")
        app_logger.error(traceback.format_exc())
        app_logger.warning("Attempting to use Firefox as fallback...")
        return setup_firefox_in_headless_mode()

def setup_firefox_in_headless_mode():
    """Fallback to Firefox if Chrome/Chromium fails"""
    app_logger.info("Setting up Firefox in headless mode as fallback...")
    
    try:
        from selenium.webdriver.firefox.options import Options as FirefoxOptions
        
        # Check if Firefox is installed
        try:
            subprocess.run(["which", "firefox"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            app_logger.info("Firefox is already installed")
        except subprocess.CalledProcessError:
            app_logger.info("Firefox not found, installing...")
            subprocess.run(["sudo", "apt-get", "update"], check=True)
            subprocess.run(["sudo", "apt-get", "install", "-y", "firefox"], check=True)
            app_logger.info("Firefox installed successfully")
        
        # Set up Firefox options
        options = FirefoxOptions()
        options.add_argument("--headless")
        options.add_argument("--width=1920")
        options.add_argument("--height=1080")
        options.add_argument("-private")
        
        # Create Firefox profile
        firefox_profile_dir = os.path.expanduser("~/firefox_profile")
        os.makedirs(firefox_profile_dir, exist_ok=True)
        
        # Launch Firefox
        driver = webdriver.Firefox(options=options)
        app_logger.info("Firefox started successfully in headless mode")
        return driver
    except Exception as e:
        app_logger.error(f"Failed to start Firefox: {e}")
        app_logger.error(traceback.format_exc())
        raise Exception("Failed to start both Chrome/Chromium and Firefox")

def main_process():
    try:
        # Open Chrome in headless mode
        driver = setup_chrome_in_headless_mode()
        
        # Navigate to emailnator
        app_logger.info("Navigating to emailnator.com...")
        driver.get(url)
        time.sleep(3)
        
        # Login with credentials
        app_logger.info("Logging in...")

        screenshot_path = "emailnator_page.png"
        driver.save_screenshot(screenshot_path)
        app_logger.info(f"Saved screenshot to {screenshot_path}")

        try:
            email_element = driver.find_element(By.ID, "email")
            email_element.clear()
            email_element.send_keys(GNATOR_EMAIL)
            
            password_element = driver.find_element(By.NAME, "password")
            password_element.clear()
            password_element.send_keys(GNATOR_PASSWORD)
            
            # Click login button
            login_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]")
            login_btn.click()
            app_logger.info("Logged in successfully")
        except Exception as e:
            app_logger.error(f"Login failed: {e}")
            driver.quit()
            return

        # Navigate to email generator
        time.sleep(3)
        driver.get("https://premium.emailnator.com/email-generator")
        time.sleep(3)
        
        # Configure email options
        app_logger.info("Configuring email options...")
        checkboxes = [
            ("public-domain-option", False),
            ("public-gmailplus-option", False),
            ("public-gmaildot-option", False),
            ("public-googlemail-option", False),
            ("private-gmailplus-option", False),
            ("private-domain-option", True),
            ("private-gmaildot-option", False),
            ("private-googlemail-option", False),
        ]

        for checkbox_id, should_check in checkboxes:
            try:
                cb = driver.find_element(By.ID, checkbox_id)
                is_checked = cb.is_selected()

                if is_checked != should_check:
                    driver.execute_script("arguments[0].click();", cb)
                    app_logger.info(f"Set {checkbox_id} to {should_check}")
            except Exception as e:
                app_logger.warning(f"Could not find checkbox {checkbox_id}: {e}")

        # Generate email
        app_logger.info("Generating email...")
        try:
            gen_button = driver.find_element(By.ID, "generate-button")
            gen_button.click()
            time.sleep(3)

            clear_config_file("config.txt")
            logging.info("Cleared config.txt")
            
            email_field = driver.find_element(By.ID, "generated-email")
            generated_email = email_field.get_attribute("value")
            app_logger.info(f"Generated Email: {generated_email}")
            
            # Save to config.txt
            save_config("cloudflare_email", generated_email)
            app_logger.info("Email saved to config.txt. Waiting for verification email...")
            
            # Wait for Cloudflare verification email
            wait_for_cloudflare_email(driver)
        except Exception as e:
            app_logger.error(f"Error generating email: {e}")
            driver.quit()
            return

    except Exception as e:
        app_logger.error(f"Error in main process: {e}")
        app_logger.error(traceback.format_exc())
        try:
            driver.quit()
        except:
            pass
        return
    



def clear_config_file(config_path="config.txt"):
    """Clears all content from config.txt"""
    try:
        with open(config_path, "w") as f:
            f.truncate(0)  # Clears file contents
        logging.info(f"Cleared all content from {config_path}")
    except Exception as e:
        logging.error(f"Failed to clear {config_path}: {e}")


def wait_for_cloudflare_email(driver, max_attempts=30):
    """Wait for and process Cloudflare verification email"""
    for attempt in range(max_attempts):
        app_logger.info(f"Checking for Cloudflare email (attempt {attempt+1}/{max_attempts})...")
        
        try:
            # Click reload button
            reload_btn = driver.find_element(By.ID, "reload-btn")
            reload_btn.click()
            time.sleep(5)  # wait for page to refresh
            
            # Look for Cloudflare message in the list
            tables = driver.find_elements(By.CLASS_NAME, "message_container")
            target_table = None
            
            for table in tables:
                if "Cloudflare" in table.get_attribute("innerHTML"):
                    target_table = table
                    break

            if target_table:
                target_table.click()
                app_logger.info("Found Cloudflare message, extracting verification URL...")
                time.sleep(3)
                
                # Extract verification URL
                try:
                    button_div = driver.find_element(By.ID, "buttonText")
                    link = button_div.find_element(By.TAG_NAME, "a")
                    verify_url = link.get_attribute("href")
                    app_logger.info("Verification URL found")
                    
                    # Save to config.txt
                    save_config("verification_url", verify_url)
                    app_logger.info("Verification URL saved to config.txt")

                    time.sleep(100)

                    logging.info("Re-attempting to generate a new email for second cloudflare...")

           


                    driver.get("https://premium.emailnator.com/email-generator")
                    logging.info("Returned to email generator page")


                    app_logger.info("Configuring email options...")
                    checkboxes = [
                        ("public-domain-option", False),
                        ("public-gmailplus-option", False),
                        ("public-gmaildot-option", False),
                        ("public-googlemail-option", False),
                        ("private-gmailplus-option", False),
                        ("private-domain-option", True),
                        ("private-gmaildot-option", False),
                        ("private-googlemail-option", False),
                    ]

                    for checkbox_id, should_check in checkboxes:
                        try:
                            cb = driver.find_element(By.ID, checkbox_id)
                            is_checked = cb.is_selected()

                            if is_checked != should_check:
                                driver.execute_script("arguments[0].click();", cb)
                                app_logger.info(f"Set {checkbox_id} to {should_check}")
                        except Exception as e:
                            app_logger.warning(f"Could not find checkbox {checkbox_id}: {e}")

                    app_logger.info("Generating email...")
                    try:
                        gen_button = driver.find_element(By.ID, "generate-button")
                        gen_button.click()
                        time.sleep(3)

                        email_field = driver.find_element(By.ID, "generated-email")
                        generated_email2 = email_field.get_attribute("value")
                        app_logger.info(f"Generated Email: {generated_email2}")

            # Save to config.txt
                        save_config("cloudflare_email2", generated_email2)
                        app_logger.info("Email2 saved to config.txt. Waiting for verification email...")

                        wait_for_cloudflare_email2(driver)
                    except Exception as e:
                        app_logger.error(f"Error generating email: {e}")
                        driver.quit()
                        return      
      
       


                    return True
                except Exception as e:
                    app_logger.error(f"Error extracting verification link: {e}")
            else:
                app_logger.info("No Cloudflare message yet, retrying...")
        
        except Exception as e:
            app_logger.warning(f"Error checking emails: {e}")
        
        time.sleep(5)  # Wait before next attempt
    
    app_logger.error(f"Failed to find Cloudflare email after {max_attempts} attempts")
    return False




def wait_for_cloudflare_email2(driver, max_attempts=30):
    """Wait for and process Cloudflare verification email"""
    for attempt in range(max_attempts):
        app_logger.info(f"Checking for Cloudflare email2 (attempt {attempt+1}/{max_attempts})...")
        
        try:
            # Click reload button
            reload_btn = driver.find_element(By.ID, "reload-btn")
            reload_btn.click()
            time.sleep(5)  # wait for page to refresh
            
            # Look for Cloudflare message in the list
            tables = driver.find_elements(By.CLASS_NAME, "message_container")
            target_table = None
            
            for table in tables:
                if "Cloudflare" in table.get_attribute("innerHTML"):
                    target_table = table
                    break

            if target_table:
                target_table.click()
                app_logger.info("Found Cloudflare message, extracting verification URL...")
                time.sleep(3)
                
                # Extract verification URL
                try:
                    button_div = driver.find_element(By.ID, "buttonText")
                    link = button_div.find_element(By.TAG_NAME, "a")
                    verify_url2 = link.get_attribute("href")
                    app_logger.info("Verification URL2 found")
                    
                    # Save to config.txt
                    save_config("verification_url2", verify_url2)
                    app_logger.info("Verification URL2 saved to config.txt")

                   

                    return True
                except Exception as e:
                    app_logger.error(f"Error extracting verification link: {e}")
            else:
                app_logger.info("No Cloudflare message yet, retrying...")
        
        except Exception as e:
            app_logger.warning(f"Error checking emails: {e}")
        
        time.sleep(5)  # Wait before next attempt
    
    app_logger.error(f"Failed to find Cloudflare email after {max_attempts} attempts")
    return False

def run_as_thread():
    """Run the main process in a thread so it can be called from creator.py"""
    app_logger.info("Starting email generation process in thread...")
    try:
        main_process()
    except Exception as e:
        app_logger.error(f"Error in email thread: {e}")
        app_logger.error(traceback.format_exc())
    app_logger.info("Email generation process completed")

if __name__ == "__main__":
    app_logger.info("Starting email generation process...")
    main_process()
    app_logger.info("Email generation process completed")