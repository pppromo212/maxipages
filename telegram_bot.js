// Telegram bot for project automation
// This bot provides a user interface for setting up and configuring projects

import dotenv from 'dotenv';
import TelegramBot from 'node-telegram-bot-api';
import { exec, spawn } from 'child_process';
import { chmodSync, readdirSync, readFileSync, existsSync, writeFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

// Initialize dotenv
dotenv.config();

// ES modules equivalent of __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Replace with your actual bot token from BotFather
const token = process.env.TELEGRAM_BOT_TOKEN || 'YOUR_TELEGRAM_BOT_TOKEN';

// Create a bot instance
const bot = new TelegramBot(token, { polling: true });

// Path to the projects directory
const projectsDir = join(__dirname, 'PROJECTS');

// Path to the setup script
const setupScript = join(__dirname, 'setup.sh');

// Path to the setuplink.py script
const setuplinkScript = join(__dirname, 'setuplink.py');

// Path to the config.txt file
const configFile = join(__dirname, 'config.txt');

// Path to the nginx config file
const nginxConfigFile = '/etc/nginx/sites-available/host-app';

// Make sure the setup script is executable
try {
  chmodSync(setupScript, '755');
  console.log('Setup script permissions updated');
} catch (error) {
  console.error('Error updating setup script permissions:', error);
}

// Make sure the setuplink.py script is executable
try {
  chmodSync(setuplinkScript, '755');
  console.log('Setuplink script permissions updated');
} catch (error) {
  console.error('Error updating setuplink script permissions:', error);
}

// Store active processes
const activeProcesses = {};

// Store user data (domain, selected project)
const userData = {};

// Function to get available projects
function getAvailableProjects() {
  try {
    const files = readdirSync(projectsDir);
    return files.filter(file => file.endsWith('.js') || file.endsWith('.mjs'));
  } catch (error) {
    console.error('Error reading projects directory:', error);
    return [];
  }
}

// Function to execute shell commands
function executeCommand(command) {
  return new Promise((resolve, reject) => {
    exec(command, (error, stdout, stderr) => {
      if (error) {
        console.error(`Error executing command: ${error}`);
        return reject(error);
      }
      return resolve({ stdout, stderr });
    });
  });
}

// Function to read config.txt file
function readConfigFile() {
  try {
    if (existsSync(configFile)) {
      const content = readFileSync(configFile, 'utf8');
      return content;
    }
    return 'Config file does not exist yet.';
  } catch (error) {
    console.error('Error reading config file:', error);
    return `Error reading config file: ${error.message}`;
  }
}

// Function to save value to config.txt
function saveToConfig(key, value) {
  try {
    let content = '';
    let updated = false;
    
    if (existsSync(configFile)) {
      const lines = readFileSync(configFile, 'utf8').split('\n');
      
      // Update existing key or add new line
      const updatedLines = lines.map(line => {
        if (line.startsWith(`${key}=`)) {
          updated = true;
          return `${key}=${value}`;
        }
        return line;
      });
      
      if (!updated) {
        updatedLines.push(`${key}=${value}`);
      }
      
      content = updatedLines.join('\n');
    } else {
      content = `${key}=${value}\n`;
    }
    
    writeFileSync(configFile, content);
    return true;
  } catch (error) {
    console.error(`Error saving to config file: ${error}`);
    return false;
  }
}

// Function to check if PM2 process is running
async function isPM2ProcessRunning(processName) {
  try {
    const { stdout } = await executeCommand('pm2 list --no-color');
    return stdout.includes(processName) && stdout.includes('online');
  } catch (error) {
    console.error(`Error checking PM2 process: ${error}`);
    return false;
  }
}

// Function to get PM2 logs
async function getPM2Logs(processName, lines = 10) {
  try {
    const { stdout, stderr } = await executeCommand(`pm2 logs ${processName} --lines ${lines} --nostream`);
    return stdout || stderr || 'No logs available.';
  } catch (error) {
    console.error(`Error getting PM2 logs: ${error}`);
    return `Error getting logs: ${error.message}`;
  }
}

// Function to update nginx config with new domain
async function updateNginxConfig(domain) {
  try {
    // Read current nginx config
    const { stdout: currentConfig } = await executeCommand(`sudo cat ${nginxConfigFile}`);
    
    // Create new config with updated domain
    const newConfig = currentConfig.replace(
      /server_name\s+[^;]+;/g, 
      `server_name ${domain};`
    );
    
    // Write to a temporary file
    const tempFile = join(__dirname, 'temp_nginx_config');
    writeFileSync(tempFile, newConfig);
    
    // Use sudo to copy the temp file to the nginx config location
    await executeCommand(`sudo cp ${tempFile} ${nginxConfigFile}`);
    
    // Test nginx config
    await executeCommand('sudo nginx -t');
    
    // Reload nginx
    await executeCommand('sudo systemctl reload nginx');
    
    // Run certbot
    await executeCommand(`sudo certbot --nginx -d ${domain} --non-interactive --agree-tos`);
    
    return true;
  } catch (error) {
    console.error(`Error updating nginx config: ${error}`);
    return false;
  }
}

// Command: /start
bot.onText(/\/start/, (msg) => {
  const chatId = msg.chat.id;
  sendMainMenu(chatId);
});

// Function to send main menu
function sendMainMenu(chatId) {
  const welcomeMessage = 
    'Welcome to the Project Automation Bot!\n\n' +
    'This bot helps you set up and configure projects. Use the buttons below to manage your setup:';
  
  // Create keyboard with main options
  const keyboard = [
    [
      { text: 'Setup Project', callback_data: 'menu:setup' },
      { text: 'SETUPLINK', callback_data: 'menu:setuplink' }
    ],
    [
      { text: 'GET CONFIG', callback_data: 'menu:getconfig' },
      { text: 'CHANGE DOMAIN', callback_data: 'menu:changedomain' }
    ],
    [
      { text: 'CHANGE PROJECT', callback_data: 'menu:changeproject' },
      { text: 'START/STOP', callback_data: 'menu:startstop' }
    ],
    [
      { text: 'RESTART', callback_data: 'menu:restart' },
      { text: 'VIEW LOGS', callback_data: 'menu:viewlogs' }
    ],
    [
      { text: 'List Projects', callback_data: 'menu:projects' },
      { text: 'Help', callback_data: 'menu:help' }
    ]
  ];
  
  bot.sendMessage(chatId, welcomeMessage, {
    reply_markup: {
      inline_keyboard: keyboard
    }
  });
}

// Command: /help
bot.onText(/\/help/, (msg) => {
  const chatId = msg.chat.id;
  const helpMessage = 
    'Project Automation Bot Help:\n\n' +
    '/start - Show main menu\n' +
    '/setup - Start the setup process\n' +
    '/projects - List available projects\n' +
    '/setuplink - Launch the setuplink.py script\n' +
    '/getconfig - Display current config.txt content\n' +
    '/changedomain - Change the domain name\n' +
    '/changeproject - Change the active project\n' +
    '/startstop - Start or stop the host-app\n' +
    '/restart - Restart the host-app\n' +
    '/viewlogs - View PM2 logs\n' +
    '/help - Show this help message';
  
  bot.sendMessage(chatId, helpMessage);
});

// Command: /projects
bot.onText(/\/projects/, (msg) => {
  const chatId = msg.chat.id;
  sendProjectsList(chatId);
});

// Command: /getconfig
bot.onText(/\/getconfig/, (msg) => {
  const chatId = msg.chat.id;
  sendConfigContent(chatId);
});

// Function to send config.txt content
function sendConfigContent(chatId) {
  const configContent = readConfigFile();
  bot.sendMessage(chatId, `📄 Current config.txt content:\n\n${configContent}`);
}

// Command: /changedomain
bot.onText(/\/changedomain/, (msg) => {
  const chatId = msg.chat.id;
  startChangeDomainProcess(chatId);
});

// Function to start change domain process
function startChangeDomainProcess(chatId) {
  // Check if there's already an active process for this chat
  if (activeProcesses[chatId]) {
    bot.sendMessage(chatId, '⚠️ There is already an active process running. Please wait for it to complete or cancel it first.');
    return;
  }
  
  bot.sendMessage(chatId, 'Please enter the new domain name (e.g., example.com):');
  
  // Set user state to waiting for domain
  userData[chatId] = { state: 'waiting_for_new_domain' };
}

// Command: /changeproject
bot.onText(/\/changeproject/, (msg) => {
  const chatId = msg.chat.id;
  startChangeProjectProcess(chatId);
});

// Function to start change project process
function startChangeProjectProcess(chatId) {
  // Check if there's already an active process for this chat
  if (activeProcesses[chatId]) {
    bot.sendMessage(chatId, '⚠️ There is already an active process running. Please wait for it to complete or cancel it first.');
    return;
  }
  
  const projects = getAvailableProjects();
  
  if (projects.length === 0) {
    bot.sendMessage(chatId, 'No projects found in the PROJECTS directory.');
    return;
  }
  
  // Create keyboard with project options
  const keyboard = projects.map(project => [{
    text: project,
    callback_data: `changeproject:${project}`
  }]);
  
  bot.sendMessage(chatId, 'Please select a project to switch to:', {
    reply_markup: {
      inline_keyboard: keyboard
    }
  });
}

// Command: /startstop
bot.onText(/\/startstop/, (msg) => {
  const chatId = msg.chat.id;
  checkHostAppStatus(chatId);
});

// Function to check host-app status and show start/stop options
async function checkHostAppStatus(chatId) {
  try {
    // Check if there's already an active process for this chat
    if (activeProcesses[chatId]) {
      bot.sendMessage(chatId, '⚠️ There is already an active process running. Please wait for it to complete or cancel it first.');
      return;
    }
    
    const isRunning = await isPM2ProcessRunning('host-app');
    
    if (isRunning) {
      bot.sendMessage(chatId, '🟢 The host-app is currently running. Do you want to stop it?', {
        reply_markup: {
          inline_keyboard: [
            [{ text: 'Yes, stop the app', callback_data: 'pm2:stop' }],
            [{ text: 'No, keep it running', callback_data: 'pm2:cancel' }]
          ]
        }
      });
    } else {
      bot.sendMessage(chatId, '🔴 The host-app is currently stopped. Do you want to start it?', {
        reply_markup: {
          inline_keyboard: [
            [{ text: 'Yes, start the app', callback_data: 'pm2:start' }],
            [{ text: 'No, keep it stopped', callback_data: 'pm2:cancel' }]
          ]
        }
      });
    }
  } catch (error) {
    bot.sendMessage(chatId, `❌ Error checking host-app status: ${error.message}`);
  }
}

// Command: /restart
bot.onText(/\/restart/, (msg) => {
  const chatId = msg.chat.id;
  restartHostApp(chatId);
});

// Function to restart host-app
async function restartHostApp(chatId) {
  try {
    // Check if there's already an active process for this chat
    if (activeProcesses[chatId]) {
      bot.sendMessage(chatId, '⚠️ There is already an active process running. Please wait for it to complete or cancel it first.');
      return;
    }
    
    bot.sendMessage(chatId, '🔄 Restarting host-app...');
    
    // Mark this chat as having an active process
    activeProcesses[chatId] = { type: 'restart', startTime: new Date() };
    
    const { stdout, stderr } = await executeCommand('pm2 restart host-app');
    
    if (stderr && stderr.includes('error')) {
      throw new Error(stderr);
    }
    
    bot.sendMessage(chatId, '✅ host-app restarted successfully.');
    
    // Clear active process
    delete activeProcesses[chatId];
  } catch (error) {
    bot.sendMessage(chatId, `❌ Error restarting host-app: ${error.message}`);
    
    // Clear active process on error
    delete activeProcesses[chatId];
  }
}

// Command: /viewlogs
bot.onText(/\/viewlogs/, (msg) => {
  const chatId = msg.chat.id;
  viewHostAppLogs(chatId);
});

// Function to view host-app logs
async function viewHostAppLogs(chatId) {
  try {
    bot.sendMessage(chatId, '📋 Fetching the last 10 lines of host-app logs...');
    
    const logs = await getPM2Logs('host-app', 10);
    
    // Split logs into chunks if too long for Telegram
    const maxLength = 4000;
    if (logs.length <= maxLength) {
      bot.sendMessage(chatId, `📋 host-app logs:\n\n${logs}`);
    } else {
      // Split logs into chunks
      for (let i = 0; i < logs.length; i += maxLength) {
        const chunk = logs.substring(i, i + maxLength);
        bot.sendMessage(chatId, `📋 host-app logs (part ${Math.floor(i / maxLength) + 1}):\n\n${chunk}`);
      }
    }
  } catch (error) {
    bot.sendMessage(chatId, `❌ Error fetching host-app logs: ${error.message}`);
  }
}

// Function to send projects list
function sendProjectsList(chatId) {
  const projects = getAvailableProjects();
  
  if (projects.length === 0) {
    bot.sendMessage(chatId, 'No projects found in the PROJECTS directory.');
    return;
  }
  
  const projectsList = projects.map(project => `- ${project}`).join('\n');
  const message = `Available projects:\n${projectsList}`;
  
  bot.sendMessage(chatId, message);
}

// Command: /setup
bot.onText(/\/setup/, (msg) => {
  const chatId = msg.chat.id;
  startSetupProcess(chatId);
});

// Function to start setup process
function startSetupProcess(chatId) {
  // Check if there's already an active process for this chat
  if (activeProcesses[chatId]) {
    bot.sendMessage(chatId, '⚠️ There is already an active process running. Please wait for it to complete or cancel it first.');
    return;
  }
  
  const projects = getAvailableProjects();
  
  if (projects.length === 0) {
    bot.sendMessage(chatId, 'No projects found in the PROJECTS directory. Please add projects first.');
    return;
  }
  
  // Create keyboard with project options
  const keyboard = projects.map(project => [{
    text: project,
    callback_data: `project:${project}`
  }]);
  
  bot.sendMessage(chatId, 'Please select a project to set up:', {
    reply_markup: {
      inline_keyboard: keyboard
    }
  });
}

// Command: /setuplink
bot.onText(/\/setuplink/, (msg) => {
  const chatId = msg.chat.id;
  startSetuplinkProcess(chatId);
});

// Function to start setuplink process
function startSetuplinkProcess(chatId) {
  // Check if there's already an active process for this chat
  if (activeProcesses[chatId]) {
    bot.sendMessage(chatId, '⚠️ There is already an active process running. Please wait for it to complete or cancel it first.');
    return;
  }
  
  bot.sendMessage(chatId, 'Please enter your Heroku URL (e.g., https://your-app.herokuapp.com):');
  
  // Set user state to waiting for Heroku URL
  userData[chatId] = { state: 'waiting_for_heroku_url' };
}

// Handle menu selections
bot.on('callback_query', async (callbackQuery) => {
  const chatId = callbackQuery.message.chat.id;
  const data = callbackQuery.data;
  
  bot.answerCallbackQuery(callbackQuery.id);
  
  if (data.startsWith('menu:')) {
    const option = data.split(':')[1];
    
    switch (option) {
      case 'setup':
        startSetupProcess(chatId);
        break;
      case 'projects':
        sendProjectsList(chatId);
        break;
      case 'setuplink':
        startSetuplinkProcess(chatId);
        break;
      case 'getconfig':
        sendConfigContent(chatId);
        break;
      case 'changedomain':
        startChangeDomainProcess(chatId);
        break;
      case 'changeproject':
        startChangeProjectProcess(chatId);
        break;
      case 'startstop':
        checkHostAppStatus(chatId);
        break;
      case 'restart':
        restartHostApp(chatId);
        break;
      case 'viewlogs':
        viewHostAppLogs(chatId);
        break;
      case 'help':
        bot.sendMessage(chatId, 
          'Project Automation Bot Help:\n\n' +
          '/start - Show main menu\n' +
          '/setup - Start the setup process\n' +
          '/projects - List available projects\n' +
          '/setuplink - Launch the setuplink.py script\n' +
          '/getconfig - Display current config.txt content\n' +
          '/changedomain - Change the domain name\n' +
          '/changeproject - Change the active project\n' +
          '/startstop - Start or stop the host-app\n' +
          '/restart - Restart the host-app\n' +
          '/viewlogs - View PM2 logs\n' +
          '/help - Show this help message'
        );
        break;
    }
  }
  else if (data.startsWith('project:')) {
    const project = data.split(':')[1];
    userData[chatId] = { project, state: 'waiting_for_domain' };
    
    bot.sendMessage(chatId, `You selected: ${project}\n\nPlease enter your domain name (e.g., example.com):`);
  }
  else if (data.startsWith('changeproject:')) {
    const project = data.split(':')[1];
    
    bot.sendMessage(chatId, `You selected to switch to project: ${project}\n\nStopping current host-app and starting ${project}...`);
    
    try {
      // Mark this chat as having an active process
      activeProcesses[chatId] = { type: 'changeproject', startTime: new Date() };
      
      // Stop current host-app
      await executeCommand('pm2 stop host-app');
      bot.sendMessage(chatId, '✅ Stopped current host-app');
      
      // Start new project
      await executeCommand(`pm2 start ${join(projectsDir, project)} --name "host-app"`);
      bot.sendMessage(chatId, `✅ Started ${project} as host-app`);
      
      // Clear active process
      delete activeProcesses[chatId];
    } catch (error) {
      bot.sendMessage(chatId, `❌ Error changing project: ${error.message}`);
      
      // Clear active process on error
      delete activeProcesses[chatId];
    }
  }
  else if (data.startsWith('pm2:')) {
    const action = data.split(':')[1];
    
    switch (action) {
      case 'start':
        try {
          // Mark this chat as having an active process
          activeProcesses[chatId] = { type: 'pm2start', startTime: new Date() };
          
          bot.sendMessage(chatId, '🔄 Starting host-app...');
          await executeCommand('pm2 start host-app');
          bot.sendMessage(chatId, '✅ host-app started successfully');
          
          // Clear active process
          delete activeProcesses[chatId];
        } catch (error) {
          bot.sendMessage(chatId, `❌ Error starting host-app: ${error.message}`);
          
          // Clear active process on error
          delete activeProcesses[chatId];
        }
        break;
      
      case 'stop':
        try {
          // Mark this chat as having an active process
          activeProcesses[chatId] = { type: 'pm2stop', startTime: new Date() };
          
          bot.sendMessage(chatId, '🔄 Stopping host-app...');
          await executeCommand('pm2 stop host-app');
          bot.sendMessage(chatId, '✅ host-app stopped successfully');
          
          // Clear active process
          delete activeProcesses[chatId];
        } catch (error) {
          bot.sendMessage(chatId, `❌ Error stopping host-app: ${error.message}`);
          
          // Clear active process on error
          delete activeProcesses[chatId];
        }
        break;
      
      case 'cancel':
        bot.sendMessage(chatId, '❌ Operation cancelled');
        break;
    }
  }
  else if (data.startsWith('confirm:')) {
    const answer = data.split(':')[1];
    
    if (answer === 'yes') {
      const { project, domain } = userData[chatId];
      
      bot.sendMessage(chatId, `Starting setup process for ${project} on ${domain}. This may take some time...`);
      
      try {
        // Mark this chat as having an active process
        activeProcesses[chatId] = { type: 'setup', startTime: new Date() };
        
        // Execute the setup script
        const command = `bash ${setupScript} ${domain} ${project}`;
        bot.sendMessage(chatId, `Executing: ${command}`);
        
        // Execute in chunks to provide progress updates
        bot.sendMessage(chatId, '1/4: Installing system dependencies...');
        await executeCommand(`bash -c "source ${setupScript} && install_system_dependencies"`);
        
        bot.sendMessage(chatId, '2/4: Detecting and installing project dependencies...');
        await executeCommand(`bash -c "source ${setupScript} && detect_and_install_project_dependencies"`);
        
        bot.sendMessage(chatId, `3/4: Configuring nginx and SSL for ${domain}...`);
        await executeCommand(`bash -c "source ${setupScript} && configure_nginx ${domain} && setup_ssl ${domain}"`);
        
        bot.sendMessage(chatId, `4/4: Starting project ${project} with PM2...`);
        await executeCommand(`bash -c "source ${setupScript} && start_project ${project}"`);
        
        bot.sendMessage(chatId, 
          `✅ Setup completed successfully!\n\n` +
          `Your project ${project} is now running on https://${domain}\n\n` +
          `To view logs: pm2 logs host-app\n` +
          `To restart: pm2 restart host-app\n` +
          `To stop: pm2 stop host-app`
        );
        
        // Clear user data and active process
        delete userData[chatId];
        delete activeProcesses[chatId];
        
      } catch (error) {
        bot.sendMessage(chatId, `❌ Error during setup: ${error.message}`);
        console.error('Setup error:', error);
        
        // Clear active process on error
        delete activeProcesses[chatId];
      }
    } else {
      bot.sendMessage(chatId, 'Setup cancelled.');
      delete userData[chatId];
    }
  }
  else if (data.startsWith('changedomain:')) {
    const answer = data.split(':')[1];
    
    if (answer === 'yes') {
      const { newDomain } = userData[chatId];
      
      bot.sendMessage(chatId, `Starting domain change process for ${newDomain}. This may take some time...`);
      
      try {
        // Mark this chat as having an active process
        activeProcesses[chatId] = { type: 'changedomain', startTime: new Date() };
        
        // Save domain to config.txt
        saveToConfig('server_domain', newDomain);
        bot.sendMessage(chatId, `✅ Domain saved to config.txt as server_domain=${newDomain}`);
        
        // Update nginx config
        bot.sendMessage(chatId, '🔄 Updating nginx configuration...');
        const nginxUpdated = await updateNginxConfig(newDomain);
        
        if (nginxUpdated) {
          bot.sendMessage(chatId, '✅ Nginx configuration updated successfully');
          bot.sendMessage(chatId, '✅ SSL certificate obtained successfully');
          bot.sendMessage(chatId, `✅ Domain changed successfully to ${newDomain}`);
        } else {
          throw new Error('Failed to update nginx configuration');
        }
        
        // Clear user data and active process
        delete userData[chatId];
        delete activeProcesses[chatId];
        
      } catch (error) {
        bot.sendMessage(chatId, `❌ Error during domain change: ${error.message}`);
        console.error('Domain change error:', error);
        
        // Clear active process on error
        delete activeProcesses[chatId];
      }
    } else {
      bot.sendMessage(chatId, 'Domain change cancelled.');
      delete userData[chatId];
    }
  }
  else if (data === 'setuplink:cancel') {
    // Cancel the setuplink process
    if (activeProcesses[chatId] && activeProcesses[chatId].type === 'setuplink' && activeProcesses[chatId].process) {
      try {
        // Kill the process
        activeProcesses[chatId].process.kill();
        bot.sendMessage(chatId, '🛑 Setuplink process cancelled.');
        
        // Display current config.txt content
        const configContent = readConfigFile();
        bot.sendMessage(chatId, `Current config.txt content:\n\n${configContent}`);
        
        // Clear user data and active process
        delete userData[chatId];
        delete activeProcesses[chatId];
      } catch (error) {
        bot.sendMessage(chatId, `❌ Error cancelling process: ${error.message}`);
        console.error('Error cancelling process:', error);
      }
    } else {
      bot.sendMessage(chatId, 'No active setuplink process to cancel.');
    }
  }
});

// Handle message inputs
bot.on('message', async (msg) => {
  const chatId = msg.chat.id;
  const text = msg.text;
  
  // Skip commands
  if (text && text.startsWith('/')) {
    return;
  }
  
  // Check user state
  if (userData[chatId]) {
    // Handle Heroku URL input for setuplink
    if (userData[chatId].state === 'waiting_for_heroku_url') {
      // Basic URL validation
      if (!text || (!text.startsWith('http://') && !text.startsWith('https://'))) {
        bot.sendMessage(chatId, 'Invalid URL. Please enter a valid URL starting with http:// or https://');
        return;
      }
      
      const herokuUrl = text;
      userData[chatId].herokuUrl = herokuUrl;
      
      // Extract domain from URL
      const urlObj = new URL(herokuUrl);
      const domain = urlObj.hostname;
      
      // Confirm setuplink process
      const confirmMessage = 
        `Ready to run setuplink.py with the following URL:\n\n` +
        `${herokuUrl}\n\n` +
        `This will:\n` +
        `1. Extract domain: ${domain}\n` +
        `2. Create Cloudflare accounts\n` +
        `3. Configure Cloudflare settings\n` +
        `4. Update various configuration files\n\n` +
        `Do you want to proceed?`;
      
      bot.sendMessage(chatId, confirmMessage, {
        reply_markup: {
          inline_keyboard: [
            [{ text: 'Yes, proceed', callback_data: 'setuplink:yes' }],
            [{ text: 'No, cancel', callback_data: 'setuplink:no' }]
          ]
        }
      });
      
      // Update user state
      userData[chatId].state = 'confirming_setuplink';
    }
    // Handle domain input for project setup
    else if (userData[chatId].state === 'waiting_for_domain') {
      // Simple domain validation
      const domainRegex = /^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.[a-zA-Z]{2,}$/;
      if (!domainRegex.test(text)) {
        bot.sendMessage(chatId, 'Invalid domain name. Please enter a valid domain (e.g., example.com):');
        return;
      }
      
      userData[chatId].domain = text;
      userData[chatId].state = 'confirming_setup';
      
      // Confirm setup
      const { project, domain } = userData[chatId];
      const confirmMessage = 
        `Ready to set up your project with the following details:\n\n` +
        `Project: ${project}\n` +
        `Domain: ${domain}\n\n` +
        `This will:\n` +
        `1. Install all necessary dependencies\n` +
        `2. Configure nginx with your domain\n` +
        `3. Set up SSL with certbot\n` +
        `4. Start the project with PM2\n\n` +
        `Do you want to proceed?`;
      
      bot.sendMessage(chatId, confirmMessage, {
        reply_markup: {
          inline_keyboard: [
            [{ text: 'Yes, proceed', callback_data: 'confirm:yes' }],
            [{ text: 'No, cancel', callback_data: 'confirm:no' }]
          ]
        }
      });
    }
    // Handle new domain input for domain change
    else if (userData[chatId].state === 'waiting_for_new_domain') {
      // Simple domain validation
      const domainRegex = /^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.[a-zA-Z]{2,}$/;
      if (!domainRegex.test(text)) {
        bot.sendMessage(chatId, 'Invalid domain name. Please enter a valid domain (e.g., example.com):');
        return;
      }
      
      userData[chatId].newDomain = text;
      userData[chatId].state = 'confirming_domain_change';
      
      // Confirm domain change
      const confirmMessage = 
        `Ready to change the domain to: ${text}\n\n` +
        `This will:\n` +
        `1. Update the nginx configuration\n` +
        `2. Obtain a new SSL certificate\n` +
        `3. Save the domain to config.txt\n\n` +
        `Do you want to proceed?`;
      
      bot.sendMessage(chatId, confirmMessage, {
        reply_markup: {
          inline_keyboard: [
            [{ text: 'Yes, proceed', callback_data: 'changedomain:yes' }],
            [{ text: 'No, cancel', callback_data: 'changedomain:no' }]
          ]
        }
      });
    }
  }
});

// Handle setuplink confirmation
bot.on('callback_query', async (callbackQuery) => {
  const chatId = callbackQuery.message.chat.id;
  const data = callbackQuery.data;
  
  if (data.startsWith('setuplink:')) {
    const answer = data.split(':')[1];
    
    bot.answerCallbackQuery(callbackQuery.id);
    
    if (answer === 'yes' && userData[chatId] && userData[chatId].herokuUrl) {
      const { herokuUrl } = userData[chatId];
      
      // Check if there's already an active process
      if (activeProcesses[chatId]) {
        bot.sendMessage(chatId, '⚠️ There is already an active process running. Please wait for it to complete or cancel it first.');
        return;
      }
      
      bot.sendMessage(chatId, `Starting setuplink.py with URL: ${herokuUrl}\n\nPlease wait, this may take some time...`);
      
      // Create a cancel button
      const cancelKeyboard = {
        reply_markup: {
          inline_keyboard: [
            [{ text: '🛑 Cancel Process', callback_data: 'setuplink:cancel' }]
          ]
        }
      };
      
      const cancelMessage = await bot.sendMessage(chatId, 'Click below to cancel the process at any time:', cancelKeyboard);
      
      try {
        // Start the setuplink.py process
        const process = spawn('python3', [setuplinkScript]);
        
        // Mark this chat as having an active process
        activeProcesses[chatId] = { 
          type: 'setuplink', 
          process: process, 
          startTime: new Date(),
          cancelMessageId: cancelMessage.message_id
        };
        
        let stdoutBuffer = '';
        let stderrBuffer = '';
        let configDisplayed = false;
        let apiKey1Saved = false;
        let apiKey2Saved = false;
        
        // Handle stdout data
        process.stdout.on('data', async (data) => {
          const output = data.toString();
          stdoutBuffer += output;
          console.log(`setuplink stdout: ${output}`);
          
          // Check for Heroku URL prompt
          if (output.includes('Please enter your Heroku URL')) {
            // Send the Heroku URL to the process
            process.stdin.write(`${herokuUrl}\n`);
            
            // Display progress message to user
            bot.sendMessage(chatId, `🔄 Setuplink is processing your Heroku URL: ${herokuUrl}`);
            
            // Extract domain from URL and display it
            const urlObj = new URL(herokuUrl);
            const domain = urlObj.hostname;
            bot.sendMessage(chatId, `📝 Extracted domain: ${domain}`);
            
            // Read config.txt after a short delay to see if domain was saved
            setTimeout(async () => {
              const configContent = readConfigFile();
              if (configContent.includes(`server_domain=${domain}`)) {
                bot.sendMessage(chatId, `✅ Domain saved to config.txt as server_domain=${domain}`);
                
                // Display full config.txt content
                bot.sendMessage(chatId, `📄 Current config.txt content:\n\n${configContent}`);
                configDisplayed = true;
              }
            }, 5000);
          }
          
          // Check for API key saved message
          if (output.includes('Saved Cloudflare API key successfully') && !apiKey1Saved) {
            apiKey1Saved = true;
            bot.sendMessage(chatId, '✅ Cloudflare API key saved successfully');
            
            // Display progress postcard with config.txt content
            setTimeout(async () => {
              const configContent = readConfigFile();
              bot.sendMessage(chatId, `📊 Progress Update: API Key Saved\n\n📄 Current config.txt content:\n\n${configContent}`);
            }, 2000);
          }
          
          // Check for API key2 saved message
          if (output.includes('Saved Cloudflare API key2 successfully') && !apiKey2Saved) {
            apiKey2Saved = true;
            bot.sendMessage(chatId, '✅ Cloudflare API key2 saved successfully');
            
            // Display progress postcard with config.txt content
            setTimeout(async () => {
              const configContent = readConfigFile();
              bot.sendMessage(chatId, `📊 Progress Update: API Key2 Saved\n\n📄 Current config.txt content:\n\n${configContent}`);
            }, 2000);
          }
          
          // Check for subprocess executions
          if (output.includes('Starting update_workers_subdomain.js')) {
            bot.sendMessage(chatId, '🔄 Running update_workers_subdomain.js...');
          }
          
          if (output.includes('Starting deploy.js')) {
            bot.sendMessage(chatId, '🔄 Running deploy.js...');
          }
          
          if (output.includes('Starting cloudflare_turnstile_api.py')) {
            bot.sendMessage(chatId, '🔄 Running cloudflare_turnstile_api.py...');
          }
          
          if (output.includes('Starting update_turnstile_keys.js')) {
            bot.sendMessage(chatId, '🔄 Running update_turnstile_keys.js...');
          }
          
          // Check for subprocess completion
          if (output.includes('update_workers_subdomain.js completed successfully')) {
            bot.sendMessage(chatId, '✅ update_workers_subdomain.js completed successfully');
          }
          
          if (output.includes('deploy.js completed successfully')) {
            bot.sendMessage(chatId, '✅ deploy.js completed successfully');
          }
          
          if (output.includes('cloudflare_turnstile_api.py completed successfully')) {
            bot.sendMessage(chatId, '✅ cloudflare_turnstile_api.py completed successfully');
          }
          
          if (output.includes('update_turnstile_keys.js completed successfully')) {
            bot.sendMessage(chatId, '✅ update_turnstile_keys.js completed successfully');
          }
          
          // Check for process completion
          if (output.includes('Process completed successfully')) {
            bot.sendMessage(chatId, '🎉 Setuplink process completed successfully!');
            
            // Display final config.txt content
            const configContent = readConfigFile();
            bot.sendMessage(chatId, `📄 Final config.txt content:\n\n${configContent}`);
            
            // Remove cancel button
            try {
              await bot.editMessageReplyMarkup({ inline_keyboard: [] }, {
                chat_id: chatId,
                message_id: cancelMessage.message_id
              });
            } catch (error) {
              console.error('Error removing cancel button:', error);
            }
            
            // Clear user data and active process
            delete userData[chatId];
            delete activeProcesses[chatId];
          }
        });
        
        // Handle stderr data
        process.stderr.on('data', (data) => {
          const output = data.toString();
          stderrBuffer += output;
          console.error(`setuplink stderr: ${output}`);
          
          // Check for errors in specific subprocesses
          if (output.includes('Error running update_workers_subdomain.js')) {
            bot.sendMessage(chatId, '❌ Error running update_workers_subdomain.js');
          }
          
          if (output.includes('Error running deploy.js')) {
            bot.sendMessage(chatId, '❌ Error running deploy.js');
          }
          
          if (output.includes('Error running cloudflare_turnstile_api.py')) {
            bot.sendMessage(chatId, '❌ Error running cloudflare_turnstile_api.py');
          }
          
          if (output.includes('Error running update_turnstile_keys.js')) {
            bot.sendMessage(chatId, '❌ Error running update_turnstile_keys.js');
          }
        });
        
        // Handle process close
        process.on('close', (code) => {
          console.log(`setuplink process exited with code ${code}`);
          
          // Remove cancel button
          try {
            bot.editMessageReplyMarkup({ inline_keyboard: [] }, {
              chat_id: chatId,
              message_id: cancelMessage.message_id
            });
          } catch (error) {
            console.error('Error removing cancel button:', error);
          }
          
          if (code === 0) {
            bot.sendMessage(chatId, '✅ Setuplink process completed successfully');
            
            // Display final config.txt content if not already displayed
            if (!configDisplayed) {
              const configContent = readConfigFile();
              bot.sendMessage(chatId, `📄 Final config.txt content:\n\n${configContent}`);
            }
          } else {
            bot.sendMessage(chatId, `❌ Setuplink process failed with code ${code}`);
            
            // Display error details if available
            if (stderrBuffer) {
              // Limit the error message length to avoid Telegram API limits
              const errorMessage = stderrBuffer.length > 3000 
                ? stderrBuffer.substring(0, 3000) + '...' 
                : stderrBuffer;
              
              bot.sendMessage(chatId, `Error details:\n\n${errorMessage}`);
            }
            
            // Display current config.txt content
            const configContent = readConfigFile();
            bot.sendMessage(chatId, `📄 Current config.txt content:\n\n${configContent}`);
          }
          
          // Clear user data and active process
          delete userData[chatId];
          delete activeProcesses[chatId];
        });
        
        // Handle process error
        process.on('error', (error) => {
          console.error(`setuplink process error: ${error.message}`);
          bot.sendMessage(chatId, `❌ Error starting setuplink process: ${error.message}`);
          
          // Clear user data and active process
          delete userData[chatId];
          delete activeProcesses[chatId];
        });
        
      } catch (error) {
        bot.sendMessage(chatId, `❌ Error starting setuplink process: ${error.message}`);
        console.error('Error starting setuplink process:', error);
        
        // Clear user data and active process
        delete userData[chatId];
        delete activeProcesses[chatId];
      }
    } else if (answer === 'no') {
      bot.sendMessage(chatId, 'Setuplink process cancelled.');
      delete userData[chatId];
    }
  }
});

// Handle errors
bot.on('polling_error', (error) => {
  console.error('Polling error:', error);
});

console.log('Telegram bot started. Press Ctrl+C to exit.');