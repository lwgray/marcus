#!/usr/bin/env python3
"""
Planka Screen Recording Options for PM Agent Demo

This script provides various methods to record Planka board activity
as tasks move through the workflow.
"""

import os
import time
import subprocess
from datetime import datetime


class PlankaRecorder:
    """Methods for recording Planka board activity"""
    
    def __init__(self, planka_url: str = "http://localhost:3333"):
        self.planka_url = planka_url
        self.output_dir = "recordings"
        os.makedirs(self.output_dir, exist_ok=True)
        
    def get_timestamp(self):
        """Get formatted timestamp for filenames"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def record_with_playwright(self, duration: int = 300):
        """
        Use Playwright to record Planka activity
        Requires: pip install playwright && playwright install chromium
        """
        script = f'''
import asyncio
from playwright.async_api import async_playwright

async def record_planka():
    async with async_playwright() as p:
        # Launch browser with video recording
        browser = await p.chromium.launch(
            headless=False,
            args=['--window-size=1920,1080']
        )
        
        context = await browser.new_context(
            viewport={{"width": 1920, "height": 1080}},
            record_video_dir="{self.output_dir}",
            record_video_size={{"width": 1920, "height": 1080}}
        )
        
        page = await context.new_page()
        
        # Navigate to Planka
        await page.goto("{self.planka_url}")
        
        # Login if needed (adjust selectors as needed)
        try:
            await page.fill('input[name="email"]', 'demo@demo.demo')
            await page.fill('input[name="password"]', 'demo')
            await page.click('button[type="submit"]')
            await page.wait_for_load_state('networkidle')
        except:
            pass  # Already logged in
        
        # Navigate to board (adjust as needed)
        await page.wait_for_timeout(2000)
        
        # Record for specified duration
        print(f"Recording for {duration} seconds...")
        await page.wait_for_timeout(duration * 1000)
        
        # Close to save video
        await context.close()
        await browser.close()
        
        print(f"Video saved to {self.output_dir}/")

asyncio.run(record_planka())
'''
        
        # Write and execute the script
        script_path = f"{self.output_dir}/playwright_recorder.py"
        with open(script_path, 'w') as f:
            f.write(script)
            
        subprocess.run([sys.executable, script_path])
        
    def record_with_selenium(self, duration: int = 300):
        """
        Use Selenium with screen recording
        Requires: pip install selenium opencv-python pillow numpy
        """
        script = f'''
import time
import cv2
import numpy as np
from PIL import ImageGrab
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from threading import Thread

class ScreenRecorder:
    def __init__(self, output_path):
        self.output_path = output_path
        self.recording = False
        
    def record(self):
        # Define codec and create VideoWriter
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(
            self.output_path, 
            fourcc, 
            10.0,  # FPS
            (1920, 1080)
        )
        
        self.recording = True
        while self.recording:
            # Capture screen
            img = ImageGrab.grab(bbox=(0, 0, 1920, 1080))
            frame = np.array(img)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            out.write(frame)
            
        out.release()
        cv2.destroyAllWindows()
        
    def stop(self):
        self.recording = False

# Setup Chrome
options = Options()
options.add_argument('--window-size=1920,1080')
driver = webdriver.Chrome(options=options)

# Start recording
recorder = ScreenRecorder("{self.output_dir}/planka_demo_{self.get_timestamp()}.mp4")
record_thread = Thread(target=recorder.record)
record_thread.start()

try:
    # Navigate to Planka
    driver.get("{self.planka_url}")
    
    # Login (adjust as needed)
    time.sleep(2)
    try:
        driver.find_element("name", "email").send_keys("demo@demo.demo")
        driver.find_element("name", "password").send_keys("demo")
        driver.find_element("css selector", "button[type='submit']").click()
    except:
        pass  # Already logged in
        
    # Record for duration
    print(f"Recording for {duration} seconds...")
    time.sleep(duration)
    
finally:
    recorder.stop()
    record_thread.join()
    driver.quit()
    print(f"Recording saved!")
'''
        
        # Write and execute
        script_path = f"{self.output_dir}/selenium_recorder.py"
        with open(script_path, 'w') as f:
            f.write(script)
            
        subprocess.run([sys.executable, script_path])
        
    def record_with_ffmpeg(self, duration: int = 300):
        """
        Use FFmpeg to record screen (macOS/Linux)
        Requires: FFmpeg installed
        """
        timestamp = self.get_timestamp()
        output_file = f"{self.output_dir}/planka_demo_{timestamp}.mp4"
        
        if os.name == 'posix':  # macOS/Linux
            if os.uname().sysname == 'Darwin':  # macOS
                # List available devices
                print("Available audio/video devices:")
                subprocess.run(['ffmpeg', '-f', 'avfoundation', '-list_devices', 'true', '-i', '""'], 
                             capture_output=True)
                
                # Record screen
                cmd = [
                    'ffmpeg',
                    '-f', 'avfoundation',
                    '-framerate', '30',
                    '-i', '1:none',  # Screen index 1, no audio
                    '-t', str(duration),
                    '-c:v', 'libx264',
                    '-preset', 'medium',
                    '-crf', '23',
                    output_file
                ]
            else:  # Linux
                cmd = [
                    'ffmpeg',
                    '-f', 'x11grab',
                    '-framerate', '30',
                    '-video_size', '1920x1080',
                    '-i', ':0.0',
                    '-t', str(duration),
                    '-c:v', 'libx264',
                    '-preset', 'medium',
                    '-crf', '23',
                    output_file
                ]
                
            print(f"Recording for {duration} seconds...")
            print(f"Command: {' '.join(cmd)}")
            subprocess.run(cmd)
            print(f"Recording saved to {output_file}")
            
    def record_with_obs_cli(self, duration: int = 300):
        """
        Use OBS Studio CLI for recording
        Requires: OBS Studio with CLI plugin
        """
        # This would require OBS Studio to be configured with scenes
        print("""
To use OBS for recording:

1. Install OBS Studio
2. Configure a scene capturing browser source with Planka URL
3. Use OBS WebSocket or CLI commands:

   obs-cli recording start
   sleep {duration}
   obs-cli recording stop

Or use OBS WebSocket API for programmatic control.
""")
        
    def create_gif_from_screenshots(self, interval: int = 2, duration: int = 60):
        """
        Create animated GIF from periodic screenshots
        Requires: pip install pillow selenium
        """
        from PIL import Image
        import glob
        
        script = f'''
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image

options = Options()
options.add_argument('--window-size=1920,1080')
driver = webdriver.Chrome(options=options)

driver.get("{self.planka_url}")
time.sleep(5)  # Wait for load

screenshots = []
end_time = time.time() + {duration}
frame_num = 0

while time.time() < end_time:
    filename = f"{self.output_dir}/frame_{{frame_num:04d}}.png"
    driver.save_screenshot(filename)
    screenshots.append(filename)
    frame_num += 1
    time.sleep({interval})

driver.quit()

# Create GIF
images = [Image.open(f) for f in screenshots]
images[0].save(
    f"{self.output_dir}/planka_demo_{self.get_timestamp()}.gif",
    save_all=True,
    append_images=images[1:],
    duration={interval * 1000},  # milliseconds
    loop=0
)

# Cleanup frames
for f in screenshots:
    os.remove(f)
    
print("GIF created!")
'''
        
        exec(script)


def main():
    """Demo recording options"""
    print("""
Planka Recording Options:

1. Playwright (Recommended for web apps)
   - Built-in video recording
   - Headless or visible browser
   - High quality output
   
2. Selenium + Screen Capture
   - Uses OpenCV/PIL for recording
   - More control over recording area
   
3. FFmpeg (System-level)
   - Records entire screen or window
   - Best performance
   - Platform-specific setup
   
4. OBS Studio
   - Professional recording
   - Requires manual setup
   
5. Animated GIF
   - Lightweight output
   - Good for documentation
   - Lower quality

For PM Agent demo, recommend:
- Playwright for automated testing
- FFmpeg for high-quality demos
- GIF for quick documentation
""")
    
    recorder = PlankaRecorder()
    
    # Example: Create a simple recording script
    print("\nExample usage:")
    print("python record_planka_demo.py")
    

if __name__ == "__main__":
    import sys
    
    recorder = PlankaRecorder()
    
    if len(sys.argv) > 1:
        method = sys.argv[1]
        duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        
        if method == "playwright":
            recorder.record_with_playwright(duration)
        elif method == "selenium":
            recorder.record_with_selenium(duration)
        elif method == "ffmpeg":
            recorder.record_with_ffmpeg(duration)
        elif method == "gif":
            recorder.create_gif_from_screenshots(duration=duration)
        else:
            main()
    else:
        main()