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

// Function to generate a boundary for multipart/form-data
function generateBoundary() {
  return `----FormBoundary${crypto.randomBytes(16).toString('hex')}`;
}

// Function to create multipart/form-data body
function createMultipartBody(boundary, workerCode) {
  const metadata = JSON.stringify({
    main_module: "index.js",
    compatibility_date: new Date().toISOString().split('T')[0], // Current date in YYYY-MM-DD format
    usage_model: "bundled"
  });

  return Buffer.concat([
    // Metadata part
    Buffer.from(`--${boundary}\r\n`),
    Buffer.from('Content-Disposition: form-data; name="metadata"\r\n'),
    Buffer.from('Content-Type: application/json\r\n\r\n'),
    Buffer.from(metadata),
    Buffer.from('\r\n'),
    
    // Worker script part
    Buffer.from(`--${boundary}\r\n`),
    Buffer.from('Content-Disposition: form-data; name="index.js"; filename="index.js"\r\n'),
    Buffer.from('Content-Type: application/javascript+module\r\n\r\n'),
    Buffer.from(workerCode),
    Buffer.from('\r\n'),
    
    // End boundary
    Buffer.from(`--${boundary}--\r\n`)
  ]);
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

// Function to update a deployed worker
async function updateDeployedWorker(workerName, scriptPath, isSecondAccount = false) {
  try {
    console.log(`Updating deployed worker "${workerName}"...`);
    
    // Read worker code
    const workerCode = fs.readFileSync(path.join(__dirname, scriptPath), 'utf8');
    
    // Create multipart form data
    const boundary = generateBoundary();
    const body = createMultipartBody(boundary, workerCode);
    
    // Upload the updated worker script
    const uploadEndpoint = `/accounts/{accountId}/workers/scripts/${workerName}`;
    await makeRequest(
      'PUT', 
      uploadEndpoint, 
      body, 
      `multipart/form-data; boundary=${boundary}`,
      isSecondAccount
    );
    
    console.log(`Worker "${workerName}" updated successfully!`);
    
    // Ensure the workers.dev subdomain is enabled
    const subdomainEndpoint = `/accounts/{accountId}/workers/scripts/${workerName}/subdomain`;
    await makeRequest('POST', subdomainEndpoint, JSON.stringify({ enabled: true }), 'application/json', isSecondAccount);
    
    return true;
  } catch (error) {
    console.error(`Error updating worker "${workerName}":`, error);
    return false;
  }
}

// Function to update workers with Turnstile keys locally
async function updateWorkersFilesWithTurnstileKeys() {
  try {
    const config = readConfig();
    let updatesApplied = false;
    
    // Check if Turnstile keys are available for link_url.js
    if (config.cloudflare_site_key && config.cloudflare_secret_key) {
      console.log('Updating link_url.js file with Turnstile keys...');
      let linkUrlContent = fs.readFileSync(path.join(__dirname, 'link_url.js'), 'utf8');
      
      // Update secret key
      linkUrlContent = linkUrlContent.replace(
        /const TURNSTILE_SECRET_KEY = "[^"]+";/,
        `const TURNSTILE_SECRET_KEY = "${config.cloudflare_secret_key}";`
      );
      
      // Update site key
      linkUrlContent = linkUrlContent.replace(
        /data-sitekey="[^"]+"/,
        `data-sitekey="${config.cloudflare_site_key}"`
      );
      
      fs.writeFileSync(path.join(__dirname, 'link_url.js'), linkUrlContent);
      console.log('link_url.js file updated with Turnstile keys.');
      updatesApplied = true;
    } else {
      console.log('Turnstile keys for link_url.js not found in config.txt.');
    }
    
    // Check if second Turnstile key is available for inbuilt_redirect.js
    if (config.cloudflare_site_key2) {
      console.log('Updating inbuilt_redirect.js file with Turnstile key...');
      let redirectContent = fs.readFileSync(path.join(__dirname, 'inbuilt_redirect.js'), 'utf8');
      
      // Update site key
      redirectContent = redirectContent.replace(
        /const SITE_KEY = "[^"]+";/,
        `const SITE_KEY = "${config.cloudflare_site_key2}";`
      );
      
      fs.writeFileSync(path.join(__dirname, 'inbuilt_redirect.js'), redirectContent);
      console.log('inbuilt_redirect.js file updated with Turnstile key.');
      updatesApplied = true;
    } else {
      console.log('Turnstile key for inbuilt_redirect.js not found in config.txt.');
    }
    
    // Update redirect URL if available
    if (config.link_url) {
      console.log('Updating inbuilt_redirect.js file with link_url...');
      let redirectContent = fs.readFileSync(path.join(__dirname, 'inbuilt_redirect.js'), 'utf8');
      
      // Update redirect URL
      redirectContent = redirectContent.replace(
        /content="1;URL=https:\/\/[^"]+"/,
        `content="1;URL=${config.link_url}"`
      );
      
      fs.writeFileSync(path.join(__dirname, 'inbuilt_redirect.js'), redirectContent);
      console.log('inbuilt_redirect.js file updated with link_url.');
      updatesApplied = true;
    } else {
      console.log('link_url not found in config.txt.');
    }
    
    return updatesApplied;
  } catch (error) {
    console.error('Error updating worker files with Turnstile keys:', error);
    return false;
  }
}

// Main function to update both local files and deployed workers
async function updateWorkersWithTurnstileKeys() {
  try {
    console.log('=== Updating Worker Files with Turnstile Keys ===');
    const filesUpdated = await updateWorkersFilesWithTurnstileKeys();
    
    if (!filesUpdated) {
      console.log('No local files were updated. Turnstile keys may not be available in config.txt yet.');
      console.log('Run turnstile.py first to create Turnstile widgets and get the keys.');
      return;
    }
    
    console.log('\n=== Updating Deployed Workers ===');
    const config = readConfig();
    
    // Update link_url worker (first account)
    if (config.link_url_hostname) {
      const linkUrlHostname = config.link_url_hostname;
      const workerName = linkUrlHostname.split('.')[0]; // Extract worker name from hostname
      
      console.log(`Updating link_url worker (${workerName}) on first Cloudflare account...`);
      const linkUrlSuccess = await updateDeployedWorker(workerName, 'link_url.js', false);
      
      if (linkUrlSuccess) {
        console.log(`Link URL worker updated successfully at: ${config.link_url}`);
      } else {
        console.error('Failed to update Link URL worker.');
      }
    } else {
      console.log('link_url_hostname not found in config.txt. Cannot update deployed worker.');
    }
    
    // Update inbuilt_redirect worker (second account)
    if (config.inbuilt_redirect_hostname) {
      const redirectHostname = config.inbuilt_redirect_hostname;
      const workerName = redirectHostname.split('.')[0]; // Extract worker name from hostname
      
      console.log(`\nUpdating inbuilt_redirect worker (${workerName}) on second Cloudflare account...`);
      const redirectSuccess = await updateDeployedWorker(workerName, 'inbuilt_redirect.js', true);
      
      if (redirectSuccess) {
        console.log(`Inbuilt Redirect worker updated successfully at: ${config.inbuilt_redirect}`);
      } else {
        console.error('Failed to update Inbuilt Redirect worker.');
      }
    } else {
      console.log('inbuilt_redirect_hostname not found in config.txt. Cannot update deployed worker.');
    }
    
    console.log('\n=== Update Summary ===');
    console.log('Local worker files updated with Turnstile keys.');
    console.log('Deployed workers updated via Cloudflare API.');
    console.log('The changes are now live on your Cloudflare Workers!');
    
  } catch (error) {
    console.error('Error in update process:', error);
  }
}

// Run the update function
updateWorkersWithTurnstileKeys();