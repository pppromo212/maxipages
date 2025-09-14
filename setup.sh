#!/bin/bash

# setup.sh - Automated setup script for projects
# This script automates the setup process for different projects,
# including dependency installation, nginx configuration, and SSL setup.

set -e  # Exit on error
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECTS_DIR="$SCRIPT_DIR/PROJECTS"
LOG_FILE="$SCRIPT_DIR/setup_log.txt"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install system dependencies
install_system_dependencies() {
    log "Installing system dependencies..."
    
    # Update package lists
    sudo apt update && sudo apt upgrade -y
    
    # Install NVM (Node Version Manager)
    log "Installing NVM..."
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
    
    # Load NVM
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    
    # Install Node.js 18
    log "Installing Node.js 18..."
    nvm install 18
    
    # Print Node.js and npm versions
    node -v
    npm -v
    
    # Initialize npm project if package.json doesn't exist
    if [ ! -f "$SCRIPT_DIR/package.json" ]; then
        log "Initializing npm project..."
        npm init -y
    fi
    
    # Install Puppeteer and Chrome
    log "Installing Puppeteer and Chrome..."
    npx puppeteer browsers install chrome
    
    wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    sudo apt install -y ./google-chrome-stable_current_amd64.deb
    
    # Install npm packages
    log "Installing npm packages..."
    npm install puppeteer@latest
    
    # Set Puppeteer cache directory
    export PUPPETEER_CACHE_DIR=/app/.cache/puppeteer
    
    # Install other dependencies
    npm install express-session
    npm install axios
    npm install dotenv
    npm install express 
    npm install body-parser
    npm install puppeteer-extra 
    npm install puppeteer-extra-plugin-stealth
    
    # Install Telegram bot dependencies
    npm install node-telegram-bot-api
    
    # Install Chrome dependencies
    log "Installing Chrome dependencies..."
    sudo apt-get update
    sudo apt-get install -y \
        ca-certificates \
        fonts-liberation \
        libasound2 \
        libatk-bridge2.0-0 \
        libatk1.0-0 \
        libc6 \
        libcairo2 \
        libcups2 \
        libdbus-1-3 \
        libexpat1 \
        libfontconfig1 \
        libgbm1 \
        libgcc1 \
        libglib2.0-0 \
        libgtk-3-0 \
        libnspr4 \
        libnss3 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libstdc++6 \
        libx11-6 \
        libx11-xcb1 \
        libxcb1 \
        libxcomposite1 \
        libxcursor1 \
        libxdamage1 \
        libxext6 \
        libxfixes3 \
        libxi6 \
        libxrandr2 \
        libxrender1 \
        libxss1 \
        libxtst6 \
        lsb-release \
        wget \
        xdg-utils
    
    # Install nginx
    log "Installing nginx..."
    sudo apt install nginx -y
    
    # Install PM2 globally
    log "Installing PM2..."
    npm install -g pm2
    
    log "System dependencies installed successfully."
}

# Function to detect and install project-specific dependencies
detect_and_install_project_dependencies() {
    log "Detecting and installing project-specific dependencies..."
    
    # Check if PROJECTS directory exists
    if [ ! -d "$PROJECTS_DIR" ]; then
        log "PROJECTS directory not found. Creating it..."
        mkdir -p "$PROJECTS_DIR"
    fi
    
    # List all JavaScript files in the PROJECTS directory (both .js and .mjs)
    project_files=$(find "$PROJECTS_DIR" \( -name "*.js" -o -name "*.mjs" \) -type f)
    
    if [ -z "$project_files" ]; then
        log "No project files found in $PROJECTS_DIR"
        return
    fi
    
    log "Found the following project files:"
    for file in $project_files; do
        log "- $(basename "$file")"
    done
    
    # Check for package.json in each project directory
    for file in $project_files; do
        project_dir=$(dirname "$file")
        project_name=$(basename "$file" | sed 's/\.[^.]*$//')  # Remove extension
        
        log "Checking dependencies for project: $project_name"
        
        # If project has its own package.json, install its dependencies
        if [ -f "$project_dir/package.json" ]; then
            log "Found package.json for $project_name. Installing dependencies..."
            (cd "$project_dir" && npm install)
        else
            log "No package.json found for $project_name. Using default dependencies."
        fi
    done
    
    log "Project dependencies installed successfully."
}

# Function to configure nginx
configure_nginx() {
    local domain=$1
    
    if [ -z "$domain" ]; then
        log "Error: Domain name is required for nginx configuration."
        return 1
    fi
    
    log "Configuring nginx for domain: $domain"
    
    # Create nginx configuration file
    sudo tee /etc/nginx/sites-available/host-app > /dev/null << EOF
server {
    listen 80;
    server_name $domain;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOF
    
    # Create symbolic link to enable the site
    sudo ln -s /etc/nginx/sites-available/host-app /etc/nginx/sites-enabled/
    
    # Test nginx configuration
    sudo nginx -t
    
    # Reload nginx to apply changes
    sudo systemctl reload nginx
    
    log "Nginx configured successfully for domain: $domain"
}

# Function to set up SSL with certbot
setup_ssl() {
    local domain=$1
    
    if [ -z "$domain" ]; then
        log "Error: Domain name is required for SSL setup."
        return 1
    fi
    
    log "Setting up SSL for domain: $domain"
    
    # Install certbot
    sudo apt install certbot python3-certbot-nginx -y
    
    # Obtain SSL certificate non-interactively
    sudo certbot --nginx -d "$domain" --non-interactive --agree-tos --email admin@"$domain"
    
    log "SSL setup completed successfully for domain: $domain"
}

# Function to kill any process using a specific port
kill_process_on_port() {
    local port=$1
    log "Checking for processes using port $port..."
    
    # Try using lsof (common on many systems)
    if command_exists lsof; then
        local pid=$(lsof -ti:$port)
        if [ -n "$pid" ]; then
            log "Found process(es) using port $port: $pid"
            log "Killing process(es)..."
            kill -9 $pid
            log "Process(es) killed."
            return 0
        fi
    fi
    
    # Try using netstat (alternative method)
    if command_exists netstat; then
        local pid=$(netstat -tulpn 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1)
        if [ -n "$pid" ]; then
            log "Found process(es) using port $port: $pid"
            log "Killing process(es)..."
            kill -9 $pid
            log "Process(es) killed."
            return 0
        fi
    fi
    
    # Try using ss (newer alternative to netstat)
    if command_exists ss; then
        local pid=$(ss -tulpn 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d',' -f2 | cut -d'=' -f2)
        if [ -n "$pid" ]; then
            log "Found process(es) using port $port: $pid"
            log "Killing process(es)..."
            kill -9 $pid
            log "Process(es) killed."
            return 0
        fi
    fi
    
    log "No processes found using port $port."
    return 0
}

# Function to start a project with PM2
start_project() {
    local project_file=$1
    
    if [ -z "$project_file" ]; then
        log "Error: Project file is required."
        return 1
    fi
    
    # Check if the project file exists (with either .js or .mjs extension)
    if [[ "$project_file" == *.* ]]; then
        # File has an extension, check if it exists
        if [ ! -f "$PROJECTS_DIR/$project_file" ]; then
            log "Error: Project file $project_file not found in $PROJECTS_DIR"
            return 1
        fi
        project_path="$PROJECTS_DIR/$project_file"
    else
        # No extension provided, try both .js and .mjs
        if [ -f "$PROJECTS_DIR/$project_file.js" ]; then
            project_path="$PROJECTS_DIR/$project_file.js"
        elif [ -f "$PROJECTS_DIR/$project_file.mjs" ]; then
            project_path="$PROJECTS_DIR/$project_file.mjs"
        else
            log "Error: Project file $project_file not found in $PROJECTS_DIR (tried both .js and .mjs)"
            return 1
        fi
    fi
    
    log "Starting project: $project_path with PM2..."
    
    # Get just the filename without the path
    project_filename=$(basename "$project_path")
    
    # Kill any process using port 3000
    kill_process_on_port 3000
    
    # Stop and delete any existing PM2 process
    log "Stopping and deleting any existing PM2 process named 'host-app'..."
    pm2 stop host-app >/dev/null 2>&1 || true  # Stop if already running
    pm2 delete host-app >/dev/null 2>&1 || true  # Delete if exists
    
    # Start the project with PM2 using project.js as the entry point
    log "Running: pm2 start $SCRIPT_DIR/project.js --name host-app -- $project_filename"
    pm2 start "$SCRIPT_DIR/project.js" --name "host-app" -- "$project_filename"
    
    # Save PM2 configuration to restart on reboot
    pm2 save
    
    # Setup PM2 to start on system startup
    pm2 startup
    
    log "Project $project_file started successfully with PM2."
}

# Function to list available projects
list_projects() {
    log "Listing available projects..."
    
    # Check if PROJECTS directory exists
    if [ ! -d "$PROJECTS_DIR" ]; then
        log "PROJECTS directory not found."
        return
    fi
    
    # List all JavaScript files in the PROJECTS directory (both .js and .mjs)
    project_files=$(find "$PROJECTS_DIR" \( -name "*.js" -o -name "*.mjs" \) -type f)
    
    if [ -z "$project_files" ]; then
        log "No project files found in $PROJECTS_DIR"
        return
    fi
    
    echo "Available projects:"
    for file in $project_files; do
        echo "- $(basename "$file")"
    done
}

# Main function
main() {
    log "Starting setup script..."
    
    # Create log file if it doesn't exist
    touch "$LOG_FILE"
    
    # Install system dependencies
    install_system_dependencies
    
    # Detect and install project-specific dependencies
    detect_and_install_project_dependencies
    
    # If domain is provided, configure nginx and SSL
    if [ -n "$1" ]; then
        configure_nginx "$1"
        setup_ssl "$1"
    fi
    
    # If project file is provided, start it with PM2
    if [ -n "$2" ]; then
        start_project "$2"
    fi
    
    log "Setup completed successfully."
}

# If script is run directly (not sourced)
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    # Check if domain and project file are provided as arguments
    if [ $# -lt 2 ]; then
        echo "Usage: $0 <domain> <project_file>"
        echo "Example: $0 example.com amazon.js"
        list_projects
        exit 1
    fi
    
    # Run main function with provided arguments
    main "$1" "$2"
fi