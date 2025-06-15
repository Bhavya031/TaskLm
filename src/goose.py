#!/usr/bin/env python3
"""
Automated Goose CLI interaction script
This script can be:
1. Run directly to create a calculator
2. Imported and used with custom prompts

Usage as module:
    from goose import run_goose_automation
    result = run_goose_automation("create a web scraper in python")

Usage as script:
    python goose.py
"""

import subprocess
import time
import os
import signal
import sys
import threading
from pathlib import Path
import select

class GooseAutomator:
    def __init__(self, goose_path="/Users/bhavya/.local/bin/goose"):
        self.goose_path = goose_path
        self.process = None
        self.generated_file = None
        self.output_buffer = []
        self.monitoring = False
        
    def monitor_output(self):
        """Monitor Goose output in a separate thread"""
        while self.monitoring and self.process:
            try:
                if self.process.stdout:
                    line = self.process.stdout.readline()
                    if line:
                        print(f"🐦 Goose: {line.strip()}")
                        self.output_buffer.append(line.strip())
                    else:
                        time.sleep(0.1)
            except Exception as e:
                print(f"⚠️ Output monitoring error: {e}")
                break
                
    def start_goose_session(self):
        """Start an interactive Goose session"""
        print("🚀 Starting Goose session...")
        try:
            self.process = subprocess.Popen(
                [self.goose_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Combine stdout and stderr
                text=True,
                bufsize=0,  # Unbuffered
                universal_newlines=True
            )
            
            # Start output monitoring in a separate thread
            self.monitoring = True
            monitor_thread = threading.Thread(target=self.monitor_output, daemon=True)
            monitor_thread.start()
            
            # Wait for goose to initialize and show its prompt
            print("⏳ Waiting for Goose to initialize...")
            time.sleep(5)
            print("✅ Goose session started successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start Goose session: {e}")
            return False
    
    def send_prompt(self, prompt):
        """Send a prompt to the Goose session"""
        if not self.process:
            print("❌ No active Goose session")
            return False
            
        try:
            print(f"📝 Sending prompt: '{prompt}'")
            print("=" * 60)
            
            # Send the prompt
            self.process.stdin.write(prompt + "\n")
            self.process.stdin.flush()
            
            # Wait for goose to process and respond
            print("⏳ Waiting for Goose to generate code...")
            print("(This may take 30-60 seconds depending on the complexity)")
            
            # Wait longer for code generation
            time.sleep(30)
            
            # Check if files were created during this time
            print("🔍 Checking for newly created files...")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send prompt: {e}")
            return False
    
    def find_generated_file(self, file_patterns=None):
        """Find the generated file based on patterns or recent modification"""
        print("🔍 Searching for generated file...")
        
        current_dir = Path(".")
        
        # Use provided patterns or default ones
        if file_patterns is None:
            file_patterns = [
                "*.py",  # Any Python file
                "*.js",  # JavaScript files
                "*.html", # HTML files
                "*.css", # CSS files
                "*.txt", # Text files
                "*.md"   # Markdown files
            ]
        
        # Find all files matching the patterns (excluding this script)
        found_files = []
        for pattern in file_patterns:
            for file_path in current_dir.glob(pattern):
                if file_path.name != "goose.py":
                    found_files.append(file_path)
        
        if found_files:
            # Sort by modification time, get the most recent
            recent_file = max(found_files, key=lambda f: f.stat().st_mtime)
            
            # Check if it was modified recently (within last 2 minutes)
            recent_time = recent_file.stat().st_mtime
            current_time = time.time()
            
            if current_time - recent_time < 120:  # 2 minutes
                self.generated_file = recent_file
                print(f"📁 Found recently modified file: {self.generated_file}")
                return True
        
        # List all files for debugging
        all_files = list(current_dir.glob("*"))
        print(f"📂 All files in directory: {[f.name for f in all_files]}")
        
        print("❌ Could not find generated file")
        return False
    
    def execute_file_background(self):
        """Execute the generated file in the background"""
        if not self.generated_file or not self.generated_file.exists():
            print("❌ No file to execute")
            return False
        
        try:
            print(f"🏃 Executing file: {self.generated_file}")
            
            # First, let's see what's in the file
            print("📄 File content preview:")
            print("-" * 40)
            try:
                with open(self.generated_file, 'r') as f:
                    content = f.read()
                    print(content[:500] + ("..." if len(content) > 500 else ""))
            except Exception as e:
                print(f"Could not read file: {e}")
            print("-" * 40)
            
            # Determine how to execute based on file extension
            file_extension = self.generated_file.suffix.lower()
            
            if file_extension == '.py':
                # Python file
                exec_cmd = [sys.executable, str(self.generated_file)]
            elif file_extension == '.js':
                # JavaScript file (requires node)
                exec_cmd = ['node', str(self.generated_file)]
            elif file_extension in ['.html', '.htm']:
                # HTML file (open in browser)
                import webbrowser
                webbrowser.open(str(self.generated_file.absolute()))
                print(f"✅ Opened {self.generated_file} in browser")
                return True
            else:
                print(f"⚠️ Don't know how to execute {file_extension} files")
                return False
            
            # Start the file
            file_process = subprocess.Popen(
                exec_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            print(f"✅ File started with PID: {file_process.pid}")
            
            # Try to get some output
            try:
                stdout, stderr = file_process.communicate(timeout=5)
                if stdout:
                    print("📤 File output:")
                    print(stdout)
                if stderr:
                    print("⚠️ File errors:")
                    print(stderr)
                    
                if file_process.returncode == 0:
                    print("✅ File executed successfully!")
                else:
                    print(f"⚠️ File exited with code: {file_process.returncode}")
                    
            except subprocess.TimeoutExpired:
                print("⏱️ File is running interactively...")
                print("💡 You can interact with it in a separate terminal if needed")
                # Don't kill it if it's interactive
                return True
                
            return True
            
        except Exception as e:
            print(f"❌ Failed to execute file: {e}")
            return False
    
    def cleanup(self):
        """Clean up the Goose session"""
        self.monitoring = False
        
        if self.process:
            print("🧹 Cleaning up Goose session...")
            try:
                # Try to send exit command gracefully
                if self.process.poll() is None:
                    self.process.stdin.write("exit\n")
                    self.process.stdin.flush()
                    time.sleep(2)
                
                # Force terminate if still running
                if self.process.poll() is None:
                    self.process.terminate()
                    time.sleep(1)
                    
                if self.process.poll() is None:
                    self.process.kill()
                    
                print("✅ Goose session cleaned up")
            except Exception as e:
                print(f"⚠️ Error during cleanup: {e}")
    
    def run_automation(self, prompt, file_patterns=None):
        """Run the complete automation workflow with a custom prompt"""
        print("🤖 Starting Goose Automation Workflow")
        print("=" * 50)
        print(f"📋 Prompt: {prompt}")
        print("=" * 50)
        
        try:
            # Step 1: Start Goose session
            if not self.start_goose_session():
                return False, None
            
            # Step 2: Send custom prompt
            if not self.send_prompt(prompt):
                return False, None
            
            # Step 3: Wait a bit more and find the file
            print("⏳ Giving Goose more time to finish...")
            time.sleep(10)
            
            if not self.find_generated_file(file_patterns):
                print("⚠️ Could not find generated file automatically")
                
                # Try to send another command to goose to finish
                print("🔄 Trying to complete the task...")
                self.process.stdin.write("\n")  # Send enter
                self.process.stdin.flush()
                time.sleep(10)
                
                # Try finding the file again
                if not self.find_generated_file(file_patterns):
                    return False, None
            
            # Step 4: Execute file
            if not self.execute_file_background():
                return False, self.generated_file
            
            print("\n🎉 Automation completed successfully!")
            print(f"Generated file: {self.generated_file}")
            
            return True, self.generated_file
            
        except KeyboardInterrupt:
            print("\n⏹️ Automation interrupted by user")
            return False, None
        except Exception as e:
            print(f"\n❌ Automation failed: {e}")
            return False, None
        finally:
            self.cleanup()

# Main functions for importing and direct use
def run_goose_automation(prompt, file_patterns=None, goose_path="/Users/bhavya/.local/bin/goose"):
    """
    Main function to run Goose automation with a custom prompt.
    
    Args:
        prompt (str): The prompt to send to Goose
        file_patterns (list, optional): List of file patterns to look for (e.g., ['*.py', '*.js'])
        goose_path (str, optional): Path to the Goose executable
    
    Returns:
        tuple: (success: bool, generated_file: Path or None)
        
    Examples:
        # Create a calculator
        success, file = run_goose_automation("create calculator in python")
        
        # Create a web scraper
        success, file = run_goose_automation("create a web scraper for news", ['*.py'])
        
        # Create a webpage
        success, file = run_goose_automation("create a simple HTML page", ['*.html'])
    """
    print(f"🎯 Goose Automation - Custom Prompt")
    print(f"📝 Task: {prompt}")
    print("-" * 50)
    
    # Create and run the automator
    automator = GooseAutomator(goose_path)
    success, generated_file = automator.run_automation(prompt, file_patterns)
    
    if success:
        print(f"\n✨ Task completed! Generated file: {generated_file}")
    else:
        print("\n💥 Task failed. Please check the error messages above.")
        print("💡 Tip: You can also try running 'goose' manually to test the connection.")
    
    return success, generated_file

def main():
    """Main function for direct script execution"""
    print("🎯 Goose CLI Automation Script v3.0")
    print("This script will:")
    print("1. Start a Goose session")
    print("2. Ask Goose to create a calculator in Python")
    print("3. Execute the generated calculator")
    print("-" * 50)
    
    # Default prompt for direct execution
    default_prompt = "create calculator in python"
    success, generated_file = run_goose_automation(default_prompt)
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
