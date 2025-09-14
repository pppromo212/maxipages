/**
 * Update Cloudflare Workers.dev Subdomain
 * 
 * This script updates the workers.dev subdomain for a Cloudflare account.
 * It generates a random 12-16 character string and updates the subdomain via the Cloudflare API.
 * 
 * Usage:
 *  node update_workers_subdomain.js
 */

const fs = require('fs');
const path = require('path');
const https = require('https');
const crypto = require('crypto');

// Function to read and parse config.txt
function readConfig() {
  const configPath = path.join(__dirname, 'config.txt');
  const config = {};
  
  if (fs.existsSync(configPath)) {
    const content = fs.readFileSync(configPath, 'utf8');
    const lines = content.split('\n');
    
    for (const line of lines) {
      const parts = line.split('=');
      if (parts.length === 2) {
        config[parts[0].trim()] = parts[1].trim();
      }
    }
  }
  
  return config;
}

// Function to update config.txt with new values
function updateConfig(key, value) {
  const configPath = path.join(__dirname, 'config.txt');
  let content = '';
  
  if (fs.existsSync(configPath)) {
    content = fs.readFileSync(configPath, 'utf8');
  }
  
  const lines = content.split('\n');
  let keyFound = false;
  
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].startsWith(`${key}=`)) {
      lines[i] = `${key}=${value}`;
      keyFound = true;
      break;
    }
  }
  
  if (!keyFound) {
    lines.push(`${key}=${value}`);
  }
  
  fs.writeFileSync(configPath, lines.join('\n'));
  console.log(`Config updated: ${key}=${value}`);
}

// Function to make requests to Cloudflare API
function makeRequest(method, endpoint, body = null, contentType = 'application/json', isSecondAccount = false) {
  return new Promise((resolve, reject) => {
    // Read credentials from config.txt
    const config = readConfig();
    
    // Use different credentials based on account
    const email = isSecondAccount ? config.cloudflare_email2 : config.cloudflare_email;
    const apiKey = isSecondAccount ? config.cloudflare_api_key2 : config.cloudflare_api_key;
    const accountId = isSecondAccount ? config.cloudflare_account_id2 : config.cloudflare_account_id;
    
    const options = {
      hostname: 'api.cloudflare.com',
      path: `/client/v4${endpoint.replace('{accountId}', accountId)}`,
      method: method,
      headers: {
        'X-Auth-Email': email,
        'X-Auth-Key': apiKey,
        'Content-Type': contentType
      }
    };

    if (body) {
      options.headers['Content-Length'] = Buffer.byteLength(body);
    }

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        try {
          const parsedData = JSON.parse(data);
          if (!parsedData.success) {
            console.error('API Error:', parsedData.errors);
            reject(new Error('API request failed: ' + JSON.stringify(parsedData.errors)));
            return;
          }
          resolve(parsedData);
        } catch (e) {
          console.error('Error parsing response:', e);
          console.error('Raw response:', data);
          reject(e);
        }
      });
    });

    req.on('error', (error) => {
      console.error('Request error:', error);
      reject(error);
    });

    if (body) {
      req.write(body);
    }
    req.end();
  });
}

// Function to generate a random subdomain (12-16 characters)
function generateRandomSubdomain(length = null) {
  if (length === null) {
    // Random length between 12 and 16
    length = Math.floor(Math.random() * 5) + 12;
  }
  
  // Use lowercase letters and numbers for the subdomain
  const characters = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let result = '';
  
  for (let i = 0; i < length; i++) {
    result += characters.charAt(Math.floor(Math.random() * characters.length));
  }
  
  return result;
}

// Function to update the workers.dev subdomain for an account
async function updateWorkersSubdomain(isSecondAccount = false) {
  try {
    // Generate a random subdomain
    const newSubdomain = generateRandomSubdomain();
    console.log(`Generated random subdomain: ${newSubdomain}`);
    
    // Cloudflare API endpoint for updating workers.dev subdomain
    const endpoint = `/accounts/{accountId}/workers/subdomain`;
    
    // Create the request body
    const body = JSON.stringify({
      subdomain: newSubdomain
    });
    
    console.log(`Updating workers.dev subdomain for ${isSecondAccount ? 'second' : 'first'} account...`);
    
    // Make the API request
    const response = await makeRequest('PUT', endpoint, body, 'application/json', isSecondAccount);
    
    console.log('Subdomain update response:', response);
    
    // Save the new subdomain to config.txt
    const configKey = isSecondAccount ? 'account_subdomain2' : 'account_subdomain';
    updateConfig(configKey, newSubdomain);
    
    console.log(`Workers.dev subdomain updated successfully to: ${newSubdomain}.workers.dev`);
    return newSubdomain;
    
  } catch (error) {
    console.error('Error updating workers.dev subdomain:', error);
    return null;
  }
}

// Main function to update workers.dev subdomains for both accounts
async function updateBothSubdomains() {
  try {
    console.log('=== Updating Workers.dev Subdomains ===');
    
    // Update first account subdomain
    console.log('\n--- Updating First Account Subdomain ---');
    const firstSubdomain = await updateWorkersSubdomain(false);
    
    // Update second account subdomain
    console.log('\n--- Updating Second Account Subdomain ---');
    const secondSubdomain = await updateWorkersSubdomain(true);
    
    console.log('\n=== Update Summary ===');
    if (firstSubdomain) {
      console.log(`First Account Subdomain: ${firstSubdomain}.workers.dev`);
    } else {
      console.log('Failed to update first account subdomain.');
    }
    
    if (secondSubdomain) {
      console.log(`Second Account Subdomain: ${secondSubdomain}.workers.dev`);
    } else {
      console.log('Failed to update second account subdomain.');
    }
    
    if (firstSubdomain || secondSubdomain) {
      console.log('\nNOTE: You will need to redeploy your workers for the changes to take effect.');
      console.log('Run deploy.js to redeploy your workers with the new subdomains.');
    }
    
  } catch (error) {
    console.error('Error in update process:', error);
  }
}

// Run the update function
updateBothSubdomains();