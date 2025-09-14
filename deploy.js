const fs = require('fs');
const path = require('path');
const https = require('https');
const crypto = require('crypto');
const readline = require('readline');

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

// Function to prompt for Heroku URL
async function promptForHerokuUrl() {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });
  
  return new Promise(resolve => {
    rl.question('Enter your Heroku URL (e.g., https://yourdomain.herokuapp.com): ', (url) => {
      rl.close();
      resolve(url);
    });
  });
}

// Function to extract domain from URL
function extractDomain(url) {
  try {
    const urlObj = new URL(url);
    return urlObj.hostname;
  } catch (error) {
    console.error('Invalid URL:', error.message);
    return url.replace(/^https?:\/\//, '').split('/')[0];
  }
}

// Function to update config.txt with server domain
function updateServerDomain(domain) {
  const configPath = path.join(__dirname, 'config.txt');
  let content = '';
  
  if (fs.existsSync(configPath)) {
    content = fs.readFileSync(configPath, 'utf8');
  }
  
  const lines = content.split('\n');
  let domainFound = false;
  
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].startsWith('server_domain=')) {
      lines[i] = `server_domain=${domain}`;
      domainFound = true;
      break;
    }
  }
  
  if (!domainFound) {
    lines.push(`server_domain=${domain}`);
  }
  
  fs.writeFileSync(configPath, lines.join('\n'));
  console.log(`Server domain "${domain}" saved to config.txt.`);
}

// Function to update link_url.js with Heroku URL and Turnstile keys
function updateLinkUrlWorker(herokuUrl) {
  const filePath = path.join(__dirname, 'link_url.js');
  const config = readConfig();
  
  let content = fs.readFileSync(filePath, 'utf8');
  
  // Update Heroku URL
  content = content.replace(/const HEROKU_URL = "[^"]+";/, `const HEROKU_URL = "${herokuUrl}";`);
  
  // Update Turnstile secret key if available
  if (config.cloudflare_secret_key) {
    content = content.replace(/const TURNSTILE_SECRET_KEY = "[^"]+";/, `const TURNSTILE_SECRET_KEY = "${config.cloudflare_secret_key}";`);
  }
  
  // Update Turnstile site key if available
  if (config.cloudflare_site_key) {
    content = content.replace(/data-sitekey="[^"]+"/, `data-sitekey="${config.cloudflare_site_key}"`);
  }
  
  fs.writeFileSync(filePath, content);
  console.log('Updated link_url.js with Heroku URL and Turnstile keys.');
}

// Function to update inbuilt_redirect.js with Turnstile key and redirect URL
function updateInbuiltRedirectWorker() {
  const filePath = path.join(__dirname, 'inbuilt_redirect.js');
  const config = readConfig();
  
  let content = fs.readFileSync(filePath, 'utf8');
  
  // Update Turnstile site key if available
  if (config.cloudflare_site_key2) {
    content = content.replace(/const SITE_KEY = "[^"]+";/, `const SITE_KEY = "${config.cloudflare_site_key2}";`);
  }
  
  // Update redirect URL if available
  if (config.link_url) {
    content = content.replace(/content="1;URL=[^"]+"/, `content="1;URL=${config.link_url}"`);
  }
  
  fs.writeFileSync(filePath, content);
  console.log('Updated inbuilt_redirect.js with Turnstile key and redirect URL.');
}

// Generate a random 12-character worker name
function generateRandomWorkerName() {
  const characters = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let result = '';
  for (let i = 0; i < 12; i++) {
    result += characters.charAt(Math.floor(Math.random() * characters.length));
  }
  return result;
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

// Check if worker already exists and delete it if necessary
async function checkAndDeleteExistingWorker(workerName, isSecondAccount = false) {
  try {
    console.log(`Checking if worker "${workerName}" already exists...`);
    const endpoint = `/accounts/{accountId}/workers/scripts/${workerName}`;
    
    // Try to get the worker
    try {
      await makeRequest('GET', endpoint, null, 'application/json', isSecondAccount);
      console.log(`Worker "${workerName}" already exists. Deleting it...`);
      
      // Delete the existing worker
      await makeRequest('DELETE', endpoint, null, 'application/json', isSecondAccount);
      console.log(`Existing worker "${workerName}" deleted.`);
    } catch (error) {
      // If it doesn't exist, that's fine
      console.log(`Worker "${workerName}" doesn't exist yet.`);
    }
  } catch (error) {
    console.error('Error checking/deleting worker:', error);
    throw error;
  }
}

// Deploy the worker
async function deployWorker(scriptPath, isSecondAccount = false) {
  try {
    // Generate a unique worker name for this deployment
    const workerName = generateRandomWorkerName();
    
    console.log(`Reading worker code from ${scriptPath}...`);
    const workerCode = fs.readFileSync(path.join(__dirname, scriptPath), 'utf8');
    
    // Check and delete existing worker if necessary
    await checkAndDeleteExistingWorker(workerName, isSecondAccount);
    
    console.log(`Deploying worker "${workerName}" to Cloudflare...`);
    
    // Create multipart form data
    const boundary = generateBoundary();
    const body = createMultipartBody(boundary, workerCode);
    
    // Upload the worker script
    const uploadEndpoint = `/accounts/{accountId}/workers/scripts/${workerName}`;
    const uploadResult = await makeRequest(
      'PUT', 
      uploadEndpoint, 
      body, 
      `multipart/form-data; boundary=${boundary}`,
      isSecondAccount
    );
    
    console.log('Worker deployed successfully!');
    
    // Get worker URL using the subdomain from config.txt
    const config = readConfig();
    const accountSubdomain = isSecondAccount ? config.account_subdomain2 : config.account_subdomain;
    const workerUrl = `https://${workerName}.${accountSubdomain}.workers.dev`;
    
    // Ensure the workers.dev subdomain is enabled
    const subdomainEndpoint = `/accounts/{accountId}/workers/scripts/${workerName}/subdomain`;
    await makeRequest('POST', subdomainEndpoint, JSON.stringify({ enabled: true }), 'application/json', isSecondAccount);
    
    console.log(`Your worker is available at: ${workerUrl}`);
    
    return workerUrl;
  } catch (error) {
    console.error('Deployment failed:', error);
    throw error;
  }
}

// Main function to deploy a link_url worker
async function deployLinkUrl() {
  try {
    // Deploy the link_url worker to the first account
    const linkUrl = await deployWorker('link_url.js', false);
    console.log(`\nLink URL worker deployed successfully.`);
    console.log(`Access your worker at: ${linkUrl}`);
    return linkUrl;
  } catch (error) {
    console.error('Link URL deployment failed:', error.message);
    throw error;
  }
}

// Main function to deploy an inbuilt_redirect worker
async function deployInbuiltRedirect(targetUrl) {
  try {
    // First read the inbuilt_redirect.js file
    let redirectCode = fs.readFileSync(path.join(__dirname, 'inbuilt_redirect.js'), 'utf8');
    
    // Update the redirect URL to point to the deployed link_url worker
    redirectCode = redirectCode.replace(
      /content="1;URL=https:\/\/[^"]+"/,
      `content="1;URL=${targetUrl}"`
    );
    
    // Write the updated code back to the file
    fs.writeFileSync(path.join(__dirname, 'inbuilt_redirect.js'), redirectCode);
    
    // Deploy the inbuilt_redirect worker to the second account
    const redirectUrl = await deployWorker('inbuilt_redirect.js', true);
    console.log(`\nInbuilt Redirect worker deployed successfully.`);
    console.log(`Access your redirect worker at: ${redirectUrl}`);
    return redirectUrl;
  } catch (error) {
    console.error('Inbuilt Redirect deployment failed:', error.message);
    throw error;
  }
}

// Function to update config.txt with worker URLs and hostnames
async function updateConfigFile(linkUrl, redirectUrl) {
  try {
    const configPath = path.join(__dirname, 'config.txt');
    let configContent = '';
    
    // Read existing config.txt if it exists
    if (fs.existsSync(configPath)) {
      configContent = fs.readFileSync(configPath, 'utf8');
    }
    
    // Extract link_url and inbuilt_redirect hostnames
    const linkUrlHostname = new URL(linkUrl).hostname;
    const redirectUrlHostname = new URL(redirectUrl).hostname;
    
    // Extract subdomains from hostnames
    const firstSubdomain = linkUrlHostname.split('.')[1]; // Extract subdomain from linkUrlHostname
    const secondSubdomain = redirectUrlHostname.split('.')[1]; // Extract subdomain from redirectUrlHostname
    
    // Create an array of lines from the config file
    const lines = configContent.split('\n');
    
    // Create a map to track which entries we've found
    const foundEntries = {
      linkUrl: false,
      linkUrlHostname: false,
      redirectUrl: false,
      redirectUrlHostname: false,
      account_subdomain: false,
      account_subdomain2: false
    };
    
    // Update existing entries if they exist
    for (let i = 0; i < lines.length; i++) {
      if (lines[i].startsWith('link_url=')) {
        lines[i] = `link_url=${linkUrl}`;
        foundEntries.linkUrl = true;
      } else if (lines[i].startsWith('link_url_hostname=')) {
        lines[i] = `link_url_hostname=${linkUrlHostname}`;
        foundEntries.linkUrlHostname = true;
      } else if (lines[i].startsWith('inbuilt_redirect=')) {
        lines[i] = `inbuilt_redirect=${redirectUrl}`;
        foundEntries.redirectUrl = true;
      } else if (lines[i].startsWith('inbuilt_redirect_hostname=')) {
        lines[i] = `inbuilt_redirect_hostname=${redirectUrlHostname}`;
        foundEntries.redirectUrlHostname = true;
      } else if (lines[i].startsWith('account_subdomain=')) {
        lines[i] = `account_subdomain=${firstSubdomain}`;
        foundEntries.account_subdomain = true;
      } else if (lines[i].startsWith('account_subdomain2=')) {
        lines[i] = `account_subdomain2=${secondSubdomain}`;
        foundEntries.account_subdomain2 = true;
      }
    }
    
    // Add entries that weren't found
    if (!foundEntries.linkUrl) {
      lines.push(`link_url=${linkUrl}`);
    }
    if (!foundEntries.linkUrlHostname) {
      lines.push(`link_url_hostname=${linkUrlHostname}`);
    }
    if (!foundEntries.redirectUrl) {
      lines.push(`inbuilt_redirect=${redirectUrl}`);
    }
    if (!foundEntries.redirectUrlHostname) {
      lines.push(`inbuilt_redirect_hostname=${redirectUrlHostname}`);
    }
    if (!foundEntries.account_subdomain) {
      lines.push(`account_subdomain=${firstSubdomain}`);
    }
    if (!foundEntries.account_subdomain2) {
      lines.push(`account_subdomain2=${secondSubdomain}`);
    }
    
    // Join lines and write back to config.txt
    const updatedContent = lines.join('\n');
    fs.writeFileSync(configPath, updatedContent);
    
    console.log('Config file updated with worker URLs, hostnames, and account subdomains.');
  } catch (error) {
    console.error('Error updating config file:', error);
  }
}

// Function to update workers with Turnstile keys
async function updateWorkersWithTurnstileKeys() {
  try {
    const config = readConfig();
    
    // Check if Turnstile keys are available
    if (config.cloudflare_site_key && config.cloudflare_secret_key) {
      console.log('Updating link_url.js with Turnstile keys...');
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
      console.log('link_url.js updated with Turnstile keys.');
    }
    
    // Check if second Turnstile key is available
    if (config.cloudflare_site_key2) {
      console.log('Updating inbuilt_redirect.js with Turnstile key...');
      let redirectContent = fs.readFileSync(path.join(__dirname, 'inbuilt_redirect.js'), 'utf8');
      
      // Update site key
      redirectContent = redirectContent.replace(
        /const SITE_KEY = "[^"]+";/,
        `const SITE_KEY = "${config.cloudflare_site_key2}";`
      );
      
      fs.writeFileSync(path.join(__dirname, 'inbuilt_redirect.js'), redirectContent);
      console.log('inbuilt_redirect.js updated with Turnstile key.');
    }
    
    // Update redirect URL if available
    if (config.link_url) {
      console.log('Updating inbuilt_redirect.js with link_url...');
      let redirectContent = fs.readFileSync(path.join(__dirname, 'inbuilt_redirect.js'), 'utf8');
      
      // Update redirect URL
      redirectContent = redirectContent.replace(
        /content="1;URL=https:\/\/[^"]+"/,
        `content="1;URL=${config.link_url}"`
      );
      
      fs.writeFileSync(path.join(__dirname, 'inbuilt_redirect.js'), redirectContent);
      console.log('inbuilt_redirect.js updated with link_url.');
    }
    
    console.log('Workers updated with Turnstile keys.');
  } catch (error) {
    console.error('Error updating workers with Turnstile keys:', error);
  }
}

// Main function to run the entire process
async function run() {
  try {
    // Prompt for Heroku URL
    const herokuUrl = await promptForHerokuUrl();
    
    // Extract domain and save to config.txt
    const domain = extractDomain(herokuUrl);
    updateServerDomain(domain);
    
    // Update link_url.js with Heroku URL
    updateLinkUrlWorker(herokuUrl);
    
    // Check for Turnstile keys and update workers
    updateWorkersWithTurnstileKeys();
    
    console.log('=== Deploying Link URL Worker ===');
    const linkUrl = await deployLinkUrl();
    
    console.log('\n=== Deploying Inbuilt Redirect Worker ===');
    const redirectUrl = await deployInbuiltRedirect(linkUrl);
    
    // Update config.txt with worker URLs and hostnames
    await updateConfigFile(linkUrl, redirectUrl);
    
    console.log('\n=== Deployment Summary ===');
    console.log(`Link URL Worker: ${linkUrl}`);
    console.log(`Redirect Worker: ${redirectUrl}`);
    console.log(`Heroku URL: ${herokuUrl}`);
    console.log(`Server Domain: ${domain}`);
    console.log('\nBoth workers deployed successfully!');
    
  } catch (error) {
    console.error('Process failed:', error.message);
    process.exit(1);
  }
}

// Run the deployment process
run();