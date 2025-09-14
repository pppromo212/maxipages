#!/usr/bin/env node

/**
 * Create Project Script
 * 
 * This script creates a new project file in the PROJECTS directory
 * with ES module syntax.
 * 
 * Usage: node create-project.js <project-name>
 * Example: node create-project.js myproject
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import readline from 'readline';

// ES modules equivalent of __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const { dirname } = path;

// Path to the PROJECTS directory
const projectsDir = path.join(__dirname, 'PROJECTS');

// Create the PROJECTS directory if it doesn't exist
if (!fs.existsSync(projectsDir)) {
  fs.mkdirSync(projectsDir, { recursive: true });
  console.log(`Created PROJECTS directory at ${projectsDir}`);
}

// Create a readline interface for user input
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

// Get the project name from command line arguments or prompt the user
const projectName = process.argv[2] || await new Promise(resolve => {
  rl.question('Enter project name: ', (answer) => {
    resolve(answer);
  });
});

// Validate the project name
if (!projectName) {
  console.error('Error: Project name is required');
  rl.close();
  process.exit(1);
}

// Ask the user which file extension to use
async function getFileExtension() {
  return new Promise(resolve => {
    rl.question('Choose file extension (1 for .js, 2 for .mjs) [default: 2]: ', (answer) => {
      if (answer === '1') {
        resolve('.js');
      } else {
        // Default to .mjs for ES modules
        resolve('.mjs');
      }
    });
  });
}

// Get the file extension from the user
const fileExtension = await getFileExtension();

// Check if the project name already has an extension
let fileName;
if (projectName.endsWith('.js') || projectName.endsWith('.mjs')) {
  fileName = projectName;
} else {
  fileName = `${projectName}${fileExtension}`;
}

const filePath = path.join(projectsDir, fileName);

// Check if the file already exists
if (fs.existsSync(filePath)) {
  rl.question(`File ${fileName} already exists. Overwrite? (y/n): `, (answer) => {
    if (answer.toLowerCase() !== 'y') {
      console.log('Operation cancelled');
      rl.close();
      process.exit(0);
    } else {
      createProjectFile();
    }
  });
} else {
  createProjectFile();
}

// Log the chosen extension
console.log(`Using ${fileExtension} extension for ES module syntax`);

// Function to create the project file
function createProjectFile() {
  // Get project details from user
  rl.question('Project description: ', (description) => {
    rl.question('Author name: ', (author) => {
      // Create the project file content
      const content = `/**
 * ${projectName} Project
 * 
 * ${description}
 */

// Import required modules
import express from 'express';
import axios from 'axios';

// Project metadata
const projectInfo = {
  name: '${projectName}',
  description: '${description}',
  version: '1.0.0',
  author: '${author}'
};

/**
 * Set up routes for the project
 * @param {express.Application} app - The Express application
 */
function setupRoutes(app) {
  // Home page route
  app.get('/', (req, res) => {
    res.send(\`
      <html>
        <head>
          <title>\${projectInfo.name}</title>
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
            <h1>\${projectInfo.name}</h1>
            <div class="info">
              <p><strong>Description:</strong> \${projectInfo.description}</p>
              <p><strong>Version:</strong> \${projectInfo.version}</p>
              <p><strong>Author:</strong> \${projectInfo.author}</p>
            </div>
            <p class="success">Server is running successfully!</p>
            <p>Server time: \${new Date().toLocaleString()}</p>
          </div>
        </body>
      </html>
    \`);
  });

  // API routes
  app.get('/api/info', (req, res) => {
    res.json({
      project: projectInfo,
      serverTime: new Date().toISOString(),
      environment: process.env.NODE_ENV || 'development'
    });
  });

  // Add your custom routes here
}

/**
 * Initialize the project
 * This function is called when the project starts
 * @returns {Promise<void>}
 */
async function init() {
  console.log(\`Initializing \${projectInfo.name}...\`);
  
  // You can perform any initialization tasks here
  // For example, connecting to a database, setting up scheduled tasks, etc.
  
  console.log(\`\${projectInfo.name} initialized successfully!\`);
}

// Export the project functions and metadata
export { projectInfo as info, setupRoutes, init };
`;

      // Write the file
      fs.writeFileSync(filePath, content);
      console.log(`Created project file: ${filePath}`);
      
      // Close the readline interface
      rl.close();
    });
  });
}

// Handle readline close
rl.on('close', () => {
  console.log('Project creation completed');
  process.exit(0);
});