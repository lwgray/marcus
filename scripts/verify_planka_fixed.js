#!/usr/bin/env node
/**
 * Fixed version - Verify the Todo App workflow in Planka using Puppeteer
 */

const puppeteer = require('puppeteer');

const PLANKA_URL = 'http://localhost:3333';
const EMAIL = 'demo@demo.demo';
const PASSWORD = 'demo';
const PROJECT_NAME = 'Task Master Test';
const BOARD_NAME = 'test';

async function verifyPlankaBoard() {
    console.log('🚀 Starting Planka verification with Puppeteer');
    console.log('=' + '='.repeat(59));
    
    const browser = await puppeteer.launch({
        headless: false, // Set to true for CI/CD
        defaultViewport: { width: 1280, height: 800 },
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    try {
        const page = await browser.newPage();
        
        // 1. Navigate to Planka
        console.log('\n📍 Navigating to Planka...');
        await page.goto(PLANKA_URL, { waitUntil: 'networkidle2', timeout: 60000 });
        console.log('✅ Planka loaded');
        
        // Wait for app to initialize
        await page.waitForTimeout(3000);
        
        // 2. Check if we're already logged in or need to login
        console.log('\n🔐 Checking login status...');
        
        const needsLogin = await page.evaluate(() => {
            // Check if login form exists
            return !!document.querySelector('input[type="email"], input[name="email"], input[data-test="email-input"]');
        });
        
        if (needsLogin) {
            console.log('Login required...');
            
            // Try different selectors for email input
            const emailSelectors = [
                'input[type="email"]',
                'input[name="email"]',
                'input[data-test="email-input"]',
                'input[placeholder*="email" i]',
                '#email'
            ];
            
            let emailInput = null;
            for (const selector of emailSelectors) {
                emailInput = await page.$(selector);
                if (emailInput) {
                    console.log(`Found email input with selector: ${selector}`);
                    break;
                }
            }
            
            if (!emailInput) {
                // Take screenshot for debugging
                await page.screenshot({ path: 'planka-login-debug.png' });
                throw new Error('Could not find email input field. Screenshot saved as planka-login-debug.png');
            }
            
            await emailInput.type(EMAIL);
            
            // Find password input
            const passwordInput = await page.$('input[type="password"]');
            if (!passwordInput) {
                throw new Error('Could not find password input field');
            }
            await passwordInput.type(PASSWORD);
            
            // Find and click submit button
            const submitButton = await page.$('button[type="submit"]');
            if (!submitButton) {
                throw new Error('Could not find submit button');
            }
            await submitButton.click();
            
            // Wait for navigation after login
            await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 30000 });
            console.log('✅ Logged in successfully');
        } else {
            console.log('✅ Already logged in');
        }
        
        // 3. Wait for projects to load
        console.log(`\n📁 Looking for project: ${PROJECT_NAME}`);
        
        // Wait for project elements
        await page.waitForFunction(
            () => document.querySelector('.project-wrapper, [data-test="project-card"], .project-name'),
            { timeout: 30000 }
        );
        
        await page.waitForTimeout(2000); // Let everything load
        
        // Click on the project
        const projectClicked = await page.evaluate((projectName) => {
            // Try multiple selectors
            const selectors = [
                '.project-wrapper',
                '[data-test="project-card"]',
                '.project-card',
                '.project'
            ];
            
            for (const selector of selectors) {
                const elements = document.querySelectorAll(selector);
                for (const element of elements) {
                    if (element.textContent && element.textContent.includes(projectName)) {
                        element.click();
                        return true;
                    }
                }
            }
            
            // Try clicking on any element containing the project name
            const allElements = document.querySelectorAll('*');
            for (const element of allElements) {
                if (element.textContent && 
                    element.textContent.includes(projectName) && 
                    element.children.length < 3) { // Avoid large containers
                    element.click();
                    return true;
                }
            }
            
            return false;
        }, PROJECT_NAME);
        
        if (!projectClicked) {
            await page.screenshot({ path: 'planka-projects-debug.png' });
            throw new Error(`Could not find project "${PROJECT_NAME}". Screenshot saved.`);
        }
        
        await page.waitForTimeout(3000); // Wait for board to load
        console.log('✅ Project found and opened');
        
        // 4. Verify board content
        console.log('\n📋 Verifying board content...');
        
        // Wait for lists to appear
        await page.waitForFunction(
            () => document.querySelector('.list-wrapper, [data-test="list"], .list'),
            { timeout: 30000 }
        );
        
        // Get lists
        const lists = await page.evaluate(() => {
            const selectors = [
                '.list-wrapper .list-header-name',
                '.list-header h4',
                '.list-name',
                '[data-test="list-name"]'
            ];
            
            for (const selector of selectors) {
                const elements = document.querySelectorAll(selector);
                if (elements.length > 0) {
                    return Array.from(elements).map(el => el.textContent.trim());
                }
            }
            
            return [];
        });
        
        console.log(`\nLists found (${lists.length}):`);
        lists.forEach(list => console.log(`  - ${list}`));
        
        // Get all card titles
        const cardInfo = await page.evaluate(() => {
            const cards = [];
            const cardElements = document.querySelectorAll('.card-wrapper, [data-test="card"], .card');
            
            cardElements.forEach(card => {
                const nameElement = card.querySelector('.card-name, [data-test="card-name"], h5');
                const listElement = card.closest('.list-wrapper, .list');
                const listNameElement = listElement ? listElement.querySelector('.list-header-name, .list-name') : null;
                
                if (nameElement) {
                    cards.push({
                        title: nameElement.textContent.trim(),
                        list: listNameElement ? listNameElement.textContent.trim() : 'Unknown'
                    });
                }
            });
            
            return cards;
        });
        
        console.log(`\nTotal cards found: ${cardInfo.length}`);
        console.log('Cards by list:');
        
        // Group cards by list
        const cardsByList = {};
        cardInfo.forEach(card => {
            if (!cardsByList[card.list]) {
                cardsByList[card.list] = [];
            }
            cardsByList[card.list].push(card.title);
        });
        
        Object.entries(cardsByList).forEach(([list, cards]) => {
            console.log(`\n  ${list} (${cards.length} cards):`);
            cards.forEach(title => console.log(`    - ${title}`));
        });
        
        // 5. Take screenshot
        const screenshotPath = 'planka-todo-board-verified.png';
        await page.screenshot({ path: screenshotPath, fullPage: true });
        console.log(`\n📸 Screenshot saved: ${screenshotPath}`);
        
        // 6. Summary
        console.log('\n✅ Verification Summary:');
        console.log('=' + '='.repeat(59));
        console.log(`Project: ${PROJECT_NAME}`);
        console.log(`Lists: ${lists.length}`);
        console.log(`Total Cards: ${cardInfo.length}`);
        
        const expectedLists = ['Backlog', 'In Progress', 'Testing', 'Done'];
        const foundLists = lists.filter(list => expectedLists.includes(list));
        
        if (foundLists.length === expectedLists.length) {
            console.log('✅ All expected lists are present!');
        } else {
            console.log(`⚠️  Found ${foundLists.length}/${expectedLists.length} expected lists`);
            console.log('Missing:', expectedLists.filter(l => !lists.includes(l)));
        }
        
        if (cardInfo.length >= 9) {
            console.log('✅ Expected number of cards found!');
        } else {
            console.log(`⚠️  Expected 9 cards, found ${cardInfo.length}`);
        }
        
        console.log('\n🎉 Todo App workflow successfully verified in Planka!');
        
    } catch (error) {
        console.error('\n❌ Error:', error.message);
        await page.screenshot({ path: 'planka-error-debug.png' });
        console.error('Screenshot saved as planka-error-debug.png');
        throw error;
    } finally {
        await browser.close();
    }
}

// Run the verification
verifyPlankaBoard().catch(console.error);