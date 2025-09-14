// Main project entry point
// This file loads the selected project from the PROJECTS directory
// and sets up an Express server to handle HTTP requests

import dotenv from 'dotenv';
import express from 'express';
import bodyParser from 'body-parser';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { existsSync, readdirSync } from 'fs';

// Initialize dotenv
dotenv.config();

// ES modules equivalent of __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Create Express app
const app = express();
const port = process.env.PORT || 3000;

// Middleware
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));
app.use(express.static(join(__dirname, 'public')));

// Get the project name from command line arguments or environment variable
const projectName = process.env.PROJECT_NAME || process.argv[2] || 'default';
const projectPath = join(__dirname, 'PROJECTS', projectName);

// Check if the project file exists
if (!existsSync(projectPath)) {
  console.error(`Error: Project file ${projectPath} not found.`);
  console.error('Available projects:');
  
  try {
    const projects = readdirSync(join(__dirname, 'PROJECTS'))
      .filter(file => file.endsWith('.js') || file.endsWith('.mjs'));
    
    if (projects.length === 0) {
      console.error('No projects found in the PROJECTS directory.');
    } else {
      projects.forEach(project => console.error(`- ${project}`));
    }
  } catch (error) {
    console.error('Error reading PROJECTS directory:', error);
  }
  
  process.exit(1);
}

// Load the project
let projectModule;
try {
  // Use dynamic import for ES modules
  const importedModule = await import(projectPath);
  projectModule = importedModule.default || importedModule;
  console.log(`Loaded project: ${projectName}`);
} catch (error) {
  console.error(`Error loading project ${projectName}:`, error);
  
  // If the project file is empty or has errors, create a default module
  projectModule = {
    name: projectName,
    description: `Default implementation for ${projectName}`,
    
    // Default route handler
    setupRoutes: (app) => {
      app.get('/', (req, res) => {
        res.send(`
          <html>
            <head>
              <title>${projectName} Project</title>
              <style>
                body {
                  font-family: Arial, sans-serif;
                  margin: 40px;
                  line-height: 1.6;
                }
                h1 {
                  color: #333;
                }
                .container {
                  max-width: 800px;
                  margin: 0 auto;
                  padding: 20px;
                  border: 1px solid #ddd;
                  border-radius: 5px;
                }
                .info {
                  background-color: #f8f9fa;
                  padding: 15px;
                  border-radius: 5px;
                  margin-bottom: 20px;
                }
                .success {
                  color: #28a745;
                  font-weight: bold;
                }
              </style>
            </head>
            <body>
              <div class="container">
                <h1>${projectName} Project</h1>
                <div class="info">
                  <p>This is a default implementation for the ${projectName} project.</p>
                  <p>The project file exists but may be empty or contain errors.</p>
                  <p>You can add your own code to <code>PROJECTS/${projectName}</code> to customize this project.</p>
                </div>
                <p class="success">Server is running successfully!</p>
                <p>Server time: ${new Date().toLocaleString()}</p>
              </div>
            </body>
          </html>
        `);
      });
    },
    
    // Default initialization function
    init: () => {
      console.log(`Initialized default implementation for ${projectName}`);
      return Promise.resolve();
    }
  };
  
  console.log(`Created default implementation for ${projectName}`);
}

// Set up project routes
if (typeof projectModule.setupRoutes === 'function') {
  projectModule.setupRoutes(app);
} else {
  // Default route if the project doesn't define routes
  app.get('/', (req, res) => {
    res.send(`
      <html>
        <head>
          <title>${projectName} Project</title>
          <style>
            body {
              font-family: Arial, sans-serif;
              margin: 40px;
              line-height: 1.6;
            }
            h1 {
              color: #333;
            }
            .container {
              max-width: 800px;
              margin: 0 auto;
              padding: 20px;
              border: 1px solid #ddd;
              border-radius: 5px;
            }
            .success {
              color: #28a745;
              font-weight: bold;
            }
          </style>
        </head>
        <body>
          <div class="container">
            <h1>${projectName} Project</h1>
            <p>Project loaded successfully, but no routes were defined.</p>
            <p class="success">Server is running!</p>
            <p>Server time: ${new Date().toLocaleString()}</p>
          </div>
        </body>
      </html>
    `);
  });
}

// Initialize the project
const initProject = async () => {
  try {
    // Call the project's init function if it exists
    if (typeof projectModule.init === 'function') {
      // Don't await the init function if it returns a promise that never resolves
      // Instead, call it and proceed with starting the server
      const initPromise = projectModule.init();
      
      // If the init function returns a promise, add a timeout to proceed anyway
      if (initPromise instanceof Promise) {
        const timeoutPromise = new Promise(resolve => {
          setTimeout(() => {
            console.log('Init function timeout reached, proceeding with server start');
            resolve();
          }, 2000); // Wait 2 seconds for init to complete
        });
        
        // Race between the init promise and the timeout
        await Promise.race([initPromise, timeoutPromise]);
      }
    }
    
    // Start the server on all interfaces (0.0.0.0) instead of just localhost
    const server = app.listen(port, '0.0.0.0', () => {
      console.log(`Server running at http://0.0.0.0:${port}`);
      console.log(`Server is accessible at http://localhost:${port} and your server's IP address`);
      console.log(`Project: ${projectName}`);
      console.log(`Time: ${new Date().toLocaleString()}`);
      console.log(`Environment: ${process.env.NODE_ENV || 'development'}`);
      console.log('Server is ready to accept connections');
    });
    
    // Handle server errors
    server.on('error', (error) => {
      if (error.code === 'EADDRINUSE') {
        console.error(`Error: Port ${port} is already in use`);
      } else {
        console.error('Server error:', error);
      }
      process.exit(1);
    });
  } catch (error) {
    console.error('Error initializing project:', error);
    process.exit(1);
  }
};

// Handle errors
process.on('uncaughtException', (error) => {
  console.error('Uncaught exception:', error);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled rejection at:', promise, 'reason:', reason);
});

// Start the project
initProject();