/**
 * Discover Project
 * 
 * This is a simplified version of the discover.js project file
 * that uses ES module syntax.
 */

import express from "express";
import bodyParser from "body-parser";
import puppeteer from "puppeteer-extra";
import StealthPlugin from "puppeteer-extra-plugin-stealth";
import axios from "axios";
import { createRequire } from "module";
import session from "express-session";
import dotenv from "dotenv";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

// Initialize dotenv
dotenv.config();

// ES modules equivalent of __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Use createRequire for CommonJS modules if needed
const require = createRequire(import.meta.url);

// Register the stealth plugin
puppeteer.use(StealthPlugin());

// Store for Puppeteer instances and pages
const puppeteerInstances = {}; // In-memory storage for Puppeteer instances
const pageStore = new Map();
const timeouts = {}; // Store timeout IDs for each session

// Project metadata
const projectInfo = {
  name: 'Discover Project',
  description: 'A project that demonstrates using puppeteer for automation',
  version: '1.0.0',
  author: 'Your Name'
};

/**
 * Initialize a Puppeteer browser instance
 * @param {string} sessionId - The session ID to use for the browser instance
 * @returns {Promise<object>} - The browser instance
 */
async function initBrowser(sessionId) {
  try {
    // Launch a new browser instance
    const browser = await puppeteer.launch({
      headless: true,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--disable-gpu',
        '--window-size=1920,1080',
      ],
      defaultViewport: {
        width: 1920,
        height: 1080
      }
    });

    // Store the browser instance
    puppeteerInstances[sessionId] = browser;
    
    return browser;
  } catch (error) {
    console.error('Error initializing browser:', error);
    throw error;
  }
}

/**
 * Set up routes for the project
 * @param {express.Application} app - The Express application
 */
function setupRoutes(app) {
  // Configure session middleware
  app.use(session({
    secret: process.env.SESSION_SECRET || 'discover-project-secret',
    resave: false,
    saveUninitialized: true,
    cookie: { secure: process.env.NODE_ENV === 'production' }
  }));

  // Serve static files from the zimbra directory for future assets
  app.use('/static', express.static(join(__dirname, 'zimbra')));

  // Home page route - serve static HTML file
  app.get('/', (req, res) => {
    const indexPath = join(__dirname, 'zimbra', 'index.html');
    res.sendFile(indexPath);
  });

  // API routes
  app.get('/api/info', (req, res) => {
    res.json({
      project: projectInfo,
      serverTime: new Date().toISOString(),
      environment: process.env.NODE_ENV || 'development'
    });
  });

  // Example API endpoint that uses Puppeteer
  app.post('/api/browse', async (req, res) => {
    const { url, sessionId = 'default' } = req.body;
    
    if (!url) {
      return res.status(400).json({
        success: false,
        error: 'URL is required'
      });
    }
    
    try {
      // Get or create a browser instance
      let browser = puppeteerInstances[sessionId];
      if (!browser) {
        browser = await initBrowser(sessionId);
      }
      
      // Create a new page
      const page = await browser.newPage();
      
      // Store the page
      pageStore.set(sessionId, page);
      
      // Navigate to the URL
      await page.goto(url, { waitUntil: 'networkidle2' });
      
      // Get the page title
      const title = await page.title();
      
      // Take a screenshot
      const screenshot = await page.screenshot({ encoding: 'base64' });
      
      // Close the page
      await page.close();
      
      res.json({
        success: true,
        title,
        screenshot: `data:image/png;base64,${screenshot}`
      });
    } catch (error) {
      console.error('Error browsing URL:', error);
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  });

  // Cleanup endpoint
  app.post('/api/cleanup', async (req, res) => {
    const { sessionId = 'default' } = req.body;
    
    try {
      // Get the browser instance
      const browser = puppeteerInstances[sessionId];
      if (browser) {
        // Close the browser
        await browser.close();
        
        // Remove the browser instance
        delete puppeteerInstances[sessionId];
        
        // Remove the page
        pageStore.delete(sessionId);
        
        // Clear any timeouts
        if (timeouts[sessionId]) {
          clearTimeout(timeouts[sessionId]);
          delete timeouts[sessionId];
        }
      }
      
      res.json({
        success: true,
        message: `Session ${sessionId} cleaned up successfully`
      });
    } catch (error) {
      console.error('Error cleaning up session:', error);
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  });
}

/**
 * Initialize the project
 * This function is called when the project starts
 * @returns {Promise<void>}
 */
async function init() {
  console.log(`Initializing ${projectInfo.name}...`);
  
  // Register cleanup handler for graceful shutdown
  process.on('SIGINT', async () => {
    console.log('Shutting down...');
    
    // Close all browser instances
    for (const sessionId in puppeteerInstances) {
      try {
        await puppeteerInstances[sessionId].close();
        console.log(`Closed browser instance for session ${sessionId}`);
      } catch (error) {
        console.error(`Error closing browser instance for session ${sessionId}:`, error);
      }
    }
    
    process.exit(0);
  });
  
  // Log environment information
  console.log('Environment Information:');
  console.log(`- Node.js version: ${process.version}`);
  console.log(`- Process ID: ${process.pid}`);
  console.log(`- Working directory: ${process.cwd()}`);
  console.log(`- Environment: ${process.env.NODE_ENV || 'development'}`);
  
  console.log(`${projectInfo.name} initialized successfully!`);
  
  // Log that the server is ready to accept connections
  console.log('Server is ready to accept connections...');
  
  // Return a resolved promise to indicate initialization is complete
  return Promise.resolve();
}

// Export the project functions and metadata
export { projectInfo as info, setupRoutes, init };