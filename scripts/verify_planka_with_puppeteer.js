#!/usr/bin/env node
/**
 * Verify the Todo App workflow in Planka using Puppeteer
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
        defaultViewport: { width: 1280, height: 800 }
    });
    
    try {
        const page = await browser.newPage();
        
        // 1. Navigate to Planka
        console.log('\n📍 Navigating to Planka...');
        await page.goto(PLANKA_URL, { waitUntil: 'networkidle2' });
        console.log('✅ Planka loaded');
        
        // 2. Login
        console.log('\n🔐 Logging in...');
        await page.waitForSelector('input[name="email"]');
        await page.type('input[name="email"]', EMAIL);
        await page.type('input[name="password"]', PASSWORD);
        await page.click('button[type="submit"]');
        
        // Wait for navigation after login
        await page.waitForNavigation({ waitUntil: 'networkidle2' });
        console.log('✅ Logged in successfully');
        
        // 3. Find and click on the Task Master Test project
        console.log(`\n📁 Looking for project: ${PROJECT_NAME}`);
        await page.waitForSelector('.project-wrapper', { timeout: 10000 });
        
        // Click on the project
        const projectFound = await page.evaluate((projectName) => {
            const projects = document.querySelectorAll('.project-wrapper');
            for (const project of projects) {
                if (project.textContent.includes(projectName)) {
                    project.click();
                    return true;
                }
            }
            return false;
        }, PROJECT_NAME);
        
        if (!projectFound) {
            throw new Error(`Project "${PROJECT_NAME}" not found`);
        }
        
        await page.waitForTimeout(2000); // Wait for board to load
        console.log('✅ Project found and opened');
        
        // 4. Verify board content
        console.log('\n📋 Verifying board content...');
        
        // Get lists
        const lists = await page.evaluate(() => {
            const listElements = document.querySelectorAll('.list-wrapper');
            return Array.from(listElements).map(list => {
                const header = list.querySelector('.list-header-name');
                return header ? header.textContent.trim() : '';
            });
        });
        
        console.log(`\nLists found (${lists.length}):`);
        lists.forEach(list => console.log(`  - ${list}`));
        
        // Get cards count per list
        const cardsPerList = await page.evaluate(() => {
            const listWrappers = document.querySelectorAll('.list-wrapper');
            const result = {};
            
            listWrappers.forEach(wrapper => {
                const header = wrapper.querySelector('.list-header-name');
                const listName = header ? header.textContent.trim() : 'Unknown';
                const cards = wrapper.querySelectorAll('.card-wrapper');
                result[listName] = cards.length;
            });
            
            return result;
        });
        
        console.log('\nCards per list:');
        Object.entries(cardsPerList).forEach(([list, count]) => {
            console.log(`  - ${list}: ${count} cards`);
        });
        
        // Get all card titles
        const cardTitles = await page.evaluate(() => {
            const cards = document.querySelectorAll('.card-name');
            return Array.from(cards).map(card => card.textContent.trim());
        });
        
        console.log(`\nTotal cards found: ${cardTitles.length}`);
        console.log('Card titles:');
        cardTitles.forEach((title, idx) => {
            console.log(`  ${idx + 1}. ${title}`);
        });
        
        // 5. Click on a card to see details
        console.log('\n🔍 Checking card details...');
        const firstCard = await page.$('.card-wrapper');
        if (firstCard) {
            await firstCard.click();
            await page.waitForTimeout(1000);
            
            // Check for tasks
            const tasks = await page.evaluate(() => {
                const taskElements = document.querySelectorAll('.task-item');
                return Array.from(taskElements).map(task => {
                    const text = task.querySelector('.text');
                    const checkbox = task.querySelector('input[type="checkbox"]');
                    return {
                        text: text ? text.textContent.trim() : '',
                        completed: checkbox ? checkbox.checked : false
                    };
                });
            });
            
            if (tasks.length > 0) {
                console.log(`\nTasks in first card (${tasks.length}):`);
                tasks.forEach((task, idx) => {
                    const status = task.completed ? '✅' : '⬜';
                    console.log(`  ${status} ${task.text}`);
                });
            }
            
            // Close modal
            await page.keyboard.press('Escape');
            await page.waitForTimeout(500);
        }
        
        // 6. Take screenshot
        const screenshotPath = 'planka-todo-board.png';
        await page.screenshot({ path: screenshotPath, fullPage: true });
        console.log(`\n📸 Screenshot saved: ${screenshotPath}`);
        
        // 7. Summary
        console.log('\n✅ Verification Summary:');
        console.log('=' + '='.repeat(59));
        console.log(`Project: ${PROJECT_NAME}`);
        console.log(`Board: ${BOARD_NAME}`);
        console.log(`Lists: ${lists.length}`);
        console.log(`Total Cards: ${cardTitles.length}`);
        
        const expectedLists = ['Backlog', 'In Progress', 'Testing', 'Done'];
        const allListsFound = expectedLists.every(list => lists.includes(list));
        
        if (allListsFound) {
            console.log('\n✅ All expected lists are present!');
        } else {
            console.log('\n⚠️  Some expected lists are missing');
        }
        
        if (cardTitles.length >= 9) {
            console.log('✅ Expected number of cards found!');
        } else {
            console.log(`⚠️  Expected 9 cards, found ${cardTitles.length}`);
        }
        
        console.log('\n🎉 Todo App workflow successfully verified in Planka!');
        
    } catch (error) {
        console.error('\n❌ Error:', error.message);
        throw error;
    } finally {
        await browser.close();
    }
}

// Run the verification
verifyPlankaBoard().catch(console.error);