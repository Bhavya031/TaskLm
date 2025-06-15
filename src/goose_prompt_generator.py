#!/usr/bin/env python3
"""
Goose Prompt Generator using o3-mini
This script generates optimized prompts for Goose automation using the boilerplate context.

Usage:
    python goose_prompt_generator.py
    
    Or as a module:
    from goose_prompt_generator import generate_goose_prompt
    prompt = generate_goose_prompt("I want to build a weather app")
"""

import os
import sys
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

class GoosePromptGenerator:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Load the system prompt
        self.system_prompt = self._load_system_prompt()
        
    def _load_system_prompt(self) -> str:
        """Load the system prompt from PROMPT_GENERATOR.md"""
        prompt_file = Path("boiler_plate/PROMPT_GENERATOR.md")
        
        if not prompt_file.exists():
            raise FileNotFoundError(
                f"System prompt file not found: {prompt_file}\n"
                "Make sure you're running this from the correct directory."
            )
        
        with open(prompt_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        return content
    
    def generate_prompt(self, user_request: str, model: str = "o3-mini") -> str:
        """
        Generate an optimized Goose prompt based on user request
        
        Args:
            user_request (str): The user's description of what they want to build
            model (str): OpenAI model to use (default: o3-mini)
            
        Returns:
            str: Optimized prompt for Goose
        """
        
        print(f"🤖 Generating Goose prompt using {model}...")
        print(f"📝 User request: {user_request}")
        print("⏳ Processing with AI...")
        
        try:
            # Call o3-mini with system prompt and user request
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_request}
                ],
                
            )
            
            generated_prompt = response.choices[0].message.content
            
            print("✅ Prompt generated successfully!")
            return generated_prompt
            
        except Exception as e:
            print(f"❌ Error generating prompt: {e}")
            return None
    
    def interactive_mode(self):
        """Run in interactive mode to get user input and generate prompts"""
        print("🎯 Goose Prompt Generator - Interactive Mode")
        print("=" * 60)
        print("This tool generates optimized prompts for Goose AI automation.")
        print("Enter your project idea and get a comprehensive Goose prompt!")
        print("=" * 60)
        
        while True:
            print("\n" + "─" * 50)
            user_input = input("🚀 What do you want to build? (or 'quit' to exit): ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
                
            if not user_input:
                print("❌ Please enter a valid request!")
                continue
            
            # Generate the prompt
            generated_prompt = self.generate_prompt(user_input)
            
            if generated_prompt:
                print("\n" + "🎉 GENERATED GOOSE PROMPT:")
                print("=" * 80)
                print(generated_prompt)
                print("=" * 80)
                
                # Ask if user wants to save or use with goose
                action = input("\n📋 What would you like to do?\n1. Save to file\n2. Run with Goose automation\n3. Generate another prompt\nChoice (1/2/3): ").strip()
                
                if action == '1':
                    self._save_prompt(generated_prompt, user_input)
                elif action == '2':
                    self._run_with_goose(generated_prompt)
                # If 3 or anything else, continue the loop
            else:
                print("❌ Failed to generate prompt. Please try again.")
    
    def _save_prompt(self, prompt: str, original_request: str):
        """Save the generated prompt to a file"""
        # Create filename from original request
        safe_name = "".join(c for c in original_request if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_').lower()[:50]
        filename = f"generated_prompts/goose_prompt_{safe_name}.txt"
        
        # Create directory if it doesn't exist
        Path("generated_prompts").mkdir(exist_ok=True)
        
        # Save the prompt
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"# Original Request: {original_request}\n")
            f.write(f"# Generated on: {os.popen('date').read().strip()}\n\n")
            f.write(prompt)
        
        print(f"💾 Prompt saved to: {filename}")
    
    def _run_with_goose(self, prompt: str):
        """Run the generated prompt with Goose automation"""
        try:
            # Import the goose automation function
            from goose import run_goose_automation
            
            print("🚀 Running prompt with Goose automation...")
            success, generated_file = run_goose_automation(prompt)
            
            if success:
                print(f"✅ Goose automation completed! Generated: {generated_file}")
            else:
                print("❌ Goose automation failed. Check the output above.")
                
        except ImportError:
            print("❌ Could not import goose module. Make sure goose.py is available.")
        except Exception as e:
            print(f"❌ Error running Goose automation: {e}")

# Standalone functions for importing
def generate_goose_prompt(user_request: str, model: str = "o3-mini") -> str:
    """
    Generate a Goose-optimized prompt from a user request
    
    Args:
        user_request (str): What the user wants to build
        model (str): OpenAI model to use
        
    Returns:
        str: Optimized prompt for Goose
        
    Example:
        prompt = generate_goose_prompt("I want to build a weather app")
        print(prompt)
    """
    generator = GoosePromptGenerator()
    return generator.generate_prompt(user_request, model)

def batch_generate_prompts(requests: list, model: str = "o3-mini") -> dict:
    """
    Generate multiple prompts at once
    
    Args:
        requests (list): List of user requests
        model (str): OpenAI model to use
        
    Returns:
        dict: Dictionary mapping requests to generated prompts
        
    Example:
        requests = ["weather app", "todo list", "chat bot"]
        prompts = batch_generate_prompts(requests)
    """
    generator = GoosePromptGenerator()
    results = {}
    
    for request in requests:
        print(f"\n🔄 Processing: {request}")
        results[request] = generator.generate_prompt(request, model)
    
    return results

def main():
    """Main function for direct script execution"""
    # Check if OpenAI API key is available
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not found in environment variables!")
        print("💡 Please add your OpenAI API key to .env file:")
        print("   OPENAI_API_KEY=your_api_key_here")
        return 1
    
    # Check if system prompt file exists
    if not Path("boiler_plate/PROMPT_GENERATOR.md").exists():
        print("❌ System prompt file not found: boiler_plate/PROMPT_GENERATOR.md")
        print("💡 Make sure you're running this from the correct directory.")
        return 1
    
    # Handle command line arguments
    if len(sys.argv) > 1:
        # Direct prompt generation from command line
        user_request = " ".join(sys.argv[1:])
        generator = GoosePromptGenerator()
        prompt = generator.generate_prompt(user_request)
        
        if prompt:
            print("\n🎉 GENERATED GOOSE PROMPT:")
            print("=" * 80)
            print(prompt)
            print("=" * 80)
        else:
            return 1
    else:
        # Interactive mode
        generator = GoosePromptGenerator()
        generator.interactive_mode()
    
    return 0

if __name__ == "__main__":
    exit(main()) 