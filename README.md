# Project Automation with Telegram Bot

This project provides a Telegram bot for automating the setup and configuration of various projects. The bot allows users to select a project, provide a domain name, and then automatically sets up the project with all necessary dependencies, nginx configuration, SSL certificates, and PM2 process management.

## Features

- Automatic detection and installation of project dependencies
- Nginx configuration with the provided domain
- SSL setup with certbot
- PM2 process management
- Telegram bot interface for easy setup
- ES module support for modern JavaScript syntax

## Prerequisites

- Ubuntu/Debian-based system
- Node.js and npm (installed by the setup script)
- A Telegram bot token (obtained from BotFather)
- A domain name pointing to your server

## Installation

1. Clone this repository to your server:

```bash
git clone <repository-url>
cd <repository-directory>
```

2. Make the setup script executable:

```bash
chmod +x setup.sh
```

3. Create a `.env` file with your Telegram bot token:

```bash
cp .env.example .env
# Edit the .env file and add your Telegram bot token
nano .env
```

4. Install the required Node.js packages:

```bash
npm install
```

## Configuring the Telegram Bot

1. Create a new bot on Telegram by talking to [BotFather](https://t.me/botfather)
2. Follow the instructions to create a new bot and get the bot token
3. Add the bot token to the `.env` file:

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

## Adding Projects

Place your project files in the `PROJECTS` directory. Each project should be a JavaScript file with either a `.js` or `.mjs` extension (e.g., `amazon.js`, `capitalone.js`, `discover.mjs`).

The `.mjs` extension is recommended for projects using ES module syntax (import/export), as it explicitly tells Node.js to treat the file as an ES module regardless of the package.json settings.

If your project has specific dependencies, you can create a `package.json` file in the same directory as your project file.

### Creating New Projects

You can use the `create-project.js` script to create a new project file with ES module syntax (either .js or .mjs):

```bash
node create-project.js <project-name>
```

This script will prompt you for project details and create a new project file in the PROJECTS directory with the correct ES module syntax.

### Project Structure

Projects use ES module syntax (`import`/`export`) instead of CommonJS (`require`/`module.exports`). You can use either `.js` or `.mjs` file extensions, but `.mjs` is recommended for clarity. Here's an example of a basic project structure:

```javascript
// Import required modules
import express from 'express';
import axios from 'axios';

// Project metadata
const projectInfo = {
  name: 'Example Project',
  description: 'An example project',
  version: '1.0.0',
  author: 'Your Name'
};

// Set up routes for the project
function setupRoutes(app) {
  // Define your routes here
  app.get('/', (req, res) => {
    res.send('Hello World!');
  });
}

// Initialize the project
async function init() {
  console.log(`Initializing ${projectInfo.name}...`);
  // Perform initialization tasks
}

// Export the project functions and metadata
export { projectInfo as info, setupRoutes, init };
```

## Starting the Bot

Start the Telegram bot:

```bash
node telegram_bot.js
```

For production use, it's recommended to use PM2 to keep the bot running:

```bash
npm install -g pm2
pm2 start telegram_bot.js --name "telegram-bot"
pm2 save
pm2 startup
```

## Using the Bot

1. Start a conversation with your bot on Telegram
2. Use the `/setup` command to start the setup process
3. Select a project from the list
4. Enter your domain name when prompted
5. Confirm the setup to begin the automated process

The bot will provide progress updates as it:
- Installs system dependencies
- Detects and installs project dependencies
- Configures nginx with your domain
- Sets up SSL with certbot
- Starts the project with PM2

## Manual Setup

If you prefer to set up a project manually without using the Telegram bot, you can use the setup script directly:

```bash
./setup.sh your-domain.com project-name.js
```

## Troubleshooting

### Nginx Configuration

If you encounter issues with the nginx configuration, you can check the nginx error logs:

```bash
sudo tail -f /var/log/nginx/error.log
```

### SSL Certificate

If certbot fails to obtain an SSL certificate, make sure:
- Your domain is correctly pointing to your server
- Port 80 and 443 are open in your firewall
- You have the correct permissions to create certificates

### PM2 Issues

If your project doesn't start correctly with PM2, check the logs:

```bash
pm2 logs host-app
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.