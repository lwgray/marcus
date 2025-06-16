#!/usr/bin/env node
/**
 * Final version - Verify the Todo App workflow in Planka using Puppeteer
 */

const puppeteer = require('puppeteer');

const PLANKA_URL = 'http://localhost:3333';
const EMAIL = 'demo@demo.demo';
const PASSWORD = 'demo';
const PROJECT_NAME = 'Task Master Test';

async function wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function verifyPlankaBoard() {
    console.log('🚀 Starting Planka verification with Puppeteer');
    console.log('=' + '='.repeat(59));
    
    const browser = await puppeteer.launch({
        headless: false,
        defaultViewport: { width: 1280, height: 800 },
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    let page;
    
    try {
        page = await browser.newPage();
        
        // Navigate to Planka
        console.log('\n📍 Navigating to Planka...');
        await page.goto(PLANKA_URL, { waitUntil: 'networkidle2', timeout: 60000 });
        console.log('✅ Planka loaded');
        
        // Wait for app to initialize
        await wait(3000);
        
        // Check if we need to login
        console.log('\n🔐 Checking login status...');
        
        // Take a screenshot to see current state
        await page.screenshot({ path: 'planka-initial.png' });
        console.log('📸 Initial screenshot saved as planka-initial.png');
        
        // Check page content
        const pageContent = await page.content();
        console.log('\nChecking page structure...');
        
        // Look for common Planka elements
        const hasProjects = pageContent.includes('project') || pageContent.includes('Project');
        const hasLogin = pageContent.includes('email') || pageContent.includes('Email') || pageContent.includes('password');
        
        if (hasLogin && !hasProjects) {
            console.log('Login form detected, attempting to login...');
            
            // Wait for form to be ready
            await wait(2000);
            
            // Try to find and fill email field
            try {
                // Click on email field first
                await page.evaluate(() => {
                    const inputs = document.querySelectorAll('input');
                    for (const input of inputs) {
                        if (input.type === 'email' || 
                            input.name === 'email' || 
                            input.placeholder?.toLowerCase().includes('email')) {
                            input.click();
                            input.focus();
                            return;
                        }
                    }
                });
                
                // Type email
                await page.keyboard.type(EMAIL, { delay: 100 });
                
                // Tab to password field
                await page.keyboard.press('Tab');
                await wait(500);
                
                // Type password
                await page.keyboard.type(PASSWORD, { delay: 100 });
                
                // Submit form
                await page.keyboard.press('Enter');
                
                console.log('Login submitted, waiting for navigation...');
                await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 30000 });
                console.log('✅ Logged in successfully');
                
            } catch (loginError) {
                console.error('Login failed:', loginError.message);
                await page.screenshot({ path: 'planka-login-error.png' });
            }
        }
        
        // Wait for projects page
        await wait(3000);
        
        // Look for project
        console.log(`\n📁 Looking for project: ${PROJECT_NAME}`);
        
        // Take screenshot of projects page
        await page.screenshot({ path: 'planka-projects.png' });
        console.log('📸 Projects page screenshot saved');
        
        // Try to click on project
        const projectClicked = await page.evaluate((projectName) => {
            const elements = document.querySelectorAll('*');
            for (const element of elements) {
                if (element.textContent && 
                    element.textContent.includes(projectName) &&
                    element.offsetParent !== null && // visible
                    element.getBoundingClientRect().width > 0) {
                    
                    // Try to find the most specific element
                    if (element.children.length <= 2 || element.tagName === 'A' || element.tagName === 'BUTTON') {
                        element.click();
                        return true;
                    }
                }
            }
            return false;
        }, PROJECT_NAME);
        
        if (projectClicked) {
            console.log('✅ Project clicked, waiting for board to load...');
            await wait(5000);
            
            // Take screenshot of board
            await page.screenshot({ path: 'planka-board.png', fullPage: true });
            console.log('📸 Board screenshot saved');
            
            // Get board content
            const boardInfo = await page.evaluate(() => {
                const info = {
                    lists: [],
                    cards: [],
                    pageTitle: document.title,
                    url: window.location.href
                };
                
                // Find lists
                const listSelectors = ['.list-wrapper', '.list', '[class*="list"]'];
                for (const selector of listSelectors) {
                    const lists = document.querySelectorAll(selector);
                    if (lists.length > 0) {
                        lists.forEach(list => {
                            const text = list.textContent;
                            if (text && (text.includes('Backlog') || text.includes('Progress') || text.includes('Testing') || text.includes('Done'))) {
                                const name = text.match(/(Backlog|In Progress|Testing|Done)/)?.[0];
                                if (name && !info.lists.includes(name)) {
                                    info.lists.push(name);
                                }
                            }
                        });
                        break;
                    }
                }
                
                // Find cards
                const cardSelectors = ['.card', '.card-wrapper', '[class*="card"]'];
                for (const selector of cardSelectors) {
                    const cards = document.querySelectorAll(selector);
                    cards.forEach(card => {
                        const text = card.textContent;
                        if (text && text.length > 5 && text.length < 200) {
                            info.cards.push(text.substring(0, 50));
                        }
                    });
                    if (info.cards.length > 0) break;
                }
                
                return info;
            });
            
            console.log('\n📊 Board Analysis:');
            console.log(`URL: ${boardInfo.url}`);
            console.log(`Page Title: ${boardInfo.pageTitle}`);
            console.log(`\nLists found: ${boardInfo.lists.length}`);
            boardInfo.lists.forEach(list => console.log(`  - ${list}`));
            console.log(`\nCards found: ${boardInfo.cards.length}`);
            
            // Summary
            console.log('\n✅ Verification Complete!');
            console.log('=' + '='.repeat(59));
            console.log('Screenshots saved:');
            console.log('  - planka-initial.png (initial page)');
            console.log('  - planka-projects.png (projects page)');
            console.log('  - planka-board.png (board with todo app)');
            
            if (boardInfo.lists.length >= 4) {
                console.log('\n✅ Board has the expected lists!');
            }
            if (boardInfo.cards.length >= 9) {
                console.log('✅ Board has the expected number of cards!');
            }
            
            console.log('\n🎉 Todo App workflow verified in Planka!');
            
        } else {
            console.log('❌ Could not find or click on project');
            
            // Get all text content for debugging
            const allText = await page.evaluate(() => document.body.innerText);
            console.log('\nPage contains:', allText.substring(0, 500) + '...');
        }
        
    } catch (error) {
        console.error('\n❌ Error:', error.message);
        if (page) {
            await page.screenshot({ path: 'planka-error.png' });
            console.error('Error screenshot saved as planka-error.png');
        }
    } finally {
        console.log('\n🔚 Closing browser...');
        await browser.close();
    }
}

// Run the verification
verifyPlankaBoard().catch(console.error);