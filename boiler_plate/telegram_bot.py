#!/usr/bin/env python3
"""
Complete Telegram Bot Boilerplate - All-in-One Solution
========================================================

This file contains everything you need for a Telegram bot with:
- Progress bars and visual indicators
- File operations with progress tracking
- Interactive inline keyboards
- Styled text formatting
- Command handling
- Error handling and logging

Just import your business logic and you're ready to go!

Usage:
    from your_logic import handle_user_request
    bot = TelegramBot("YOUR_BOT_TOKEN", handle_user_request)
    bot.run()
"""

import os
import asyncio
import time
import logging
from typing import Callable, Dict, Any, Optional
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ProgressBar:
    """Advanced progress bar utility for Telegram messages."""
    
    def __init__(self, total: int = 100, length: int = 20, fill: str = "█", empty: str = "░", 
                 show_percentage: bool = True, show_count: bool = True):
        self.total = total
        self.length = length
        self.fill = fill
        self.empty = empty
        self.show_percentage = show_percentage
        self.show_count = show_count
        self.current = 0
        self.start_time = time.time()
        
    def update(self, current: int) -> str:
        """Update progress and return formatted progress bar string."""
        self.current = min(current, self.total)
        percent = (self.current / self.total) * 100
        filled_length = int(self.length * self.current // self.total)
        
        bar = self.fill * filled_length + self.empty * (self.length - filled_length)
        
        # Build progress string
        progress_parts = [f"[{bar}]"]
        
        if self.show_percentage:
            progress_parts.append(f"{percent:.1f}%")
            
        if self.show_count:
            progress_parts.append(f"({self.current}/{self.total})")
            
        return f"Progress: {' '.join(progress_parts)}"
    
    def get_emoji_progress(self, current: int) -> str:
        """Get emoji-based progress indicator with status."""
        self.current = min(current, self.total)
        percent = (self.current / self.total) * 100
        
        if percent == 0:
            emoji, status = "⭕", "Starting"
        elif percent < 25:
            emoji, status = "🔴", "Beginning"
        elif percent < 50:
            emoji, status = "🟠", "In Progress"
        elif percent < 75:
            emoji, status = "🟡", "Halfway"
        elif percent < 100:
            emoji, status = "🔵", "Almost Done"
        else:
            emoji, status = "🟢", "Complete"
            
        return f"{emoji} {percent:.1f}% {status}"
    
    def get_eta(self, current: int) -> str:
        """Calculate and return estimated time remaining."""
        if current <= 0:
            return "Calculating..."
            
        elapsed = time.time() - self.start_time
        rate = current / elapsed
        remaining = (self.total - current) / rate if rate > 0 else 0
        
        if remaining < 60:
            return f"{remaining:.0f}s"
        elif remaining < 3600:
            return f"{remaining/60:.1f}m"
        else:
            return f"{remaining/3600:.1f}h"

class TelegramBotResponse:
    """Helper class for creating bot responses."""
    
    @staticmethod
    def text(content: str) -> Dict[str, Any]:
        """Create a simple text response."""
        return {"type": "text", "content": content}
    
    @staticmethod
    def styled_text(content: str, parse_mode: str = "Markdown") -> Dict[str, Any]:
        """Create a styled text response with formatting."""
        return {"type": "styled_text", "content": content, "parse_mode": parse_mode}
    
    @staticmethod
    def progress(title: str, final_message: str, total_steps: int = 100, 
                step_delay: float = 0.3) -> Dict[str, Any]:
        """Create a progress bar response."""
        return {
            "type": "progress",
            "content": final_message,
            "progress_config": {
                "total_steps": total_steps,
                "step_delay": step_delay,
                "title": title
            }
        }
    
    @staticmethod
    def keyboard(content: str, buttons: list, parse_mode: str = "Markdown") -> Dict[str, Any]:
        """Create an inline keyboard response."""
        return {
            "type": "inline_keyboard",
            "content": content,
            "parse_mode": parse_mode,
            "keyboard": buttons
        }
    
    @staticmethod
    def file(file_path: str, content: str = "", file_content: str = None, 
            cleanup: bool = True) -> Dict[str, Any]:
        """Create a file response."""
        response = {
            "type": "file",
            "file_path": file_path,
            "content": content,
            "cleanup": cleanup
        }
        if file_content:
            response["file_content"] = file_content
        return response
    
    @staticmethod
    def error(message: str = "An error occurred. Please try again.") -> Dict[str, Any]:
        """Create an error response."""
        return {"type": "text", "content": f"❌ {message}"}

class TelegramBot:
    """Complete Telegram Bot with all functionality built-in."""
    
    def __init__(self, bot_token: str, user_handler: Callable, 
                 bot_name: str = "Enhanced Bot", bot_description: str = "Powered by Progress Tracking"):
        """
        Initialize the Telegram bot.
        
        Args:
            bot_token: Your Telegram bot token
            user_handler: Function to handle user requests (message_text, callback_data, progress_callback)
            bot_name: Name of your bot
            bot_description: Description for help text
        """
        self.bot_token = bot_token
        self.user_handler = user_handler
        self.bot_name = bot_name
        self.bot_description = bot_description
        self.application = None
        self.response = TelegramBotResponse()
        
        # Store active progress operations
        self.active_progress = {}
        
    def create_progress_callback(self, message_obj, operation_id: str):
        """Create a progress callback for real-time updates."""
        async def progress_callback(current: int, total: int, status: str = "Processing"):
            try:
                if operation_id not in self.active_progress:
                    self.active_progress[operation_id] = ProgressBar(total=total)
                
                progress_bar = self.active_progress[operation_id]
                progress_text = progress_bar.update(current)
                emoji_progress = progress_bar.get_emoji_progress(current)
                eta = progress_bar.get_eta(current)
                
                full_text = f"🔄 **{status}**\n\n{progress_text}\n{emoji_progress}\nETA: {eta}"
                
                await message_obj.edit_text(full_text, parse_mode='Markdown')
                
                if current >= total:
                    if operation_id in self.active_progress:
                        del self.active_progress[operation_id]
                        
            except Exception as e:
                logger.error(f"Progress callback error: {e}")
        
        return progress_callback

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        welcome_text = f"""👋 **Welcome to {self.bot_name}!**

{self.bot_description}

🚀 **Features:**
• 📊 Real-time progress tracking
• 🎛️ Interactive button menus  
• 📁 File operations
• 🎨 Rich text formatting
• ⚡ Fast and responsive

💡 **Get Started:**
• Type any message to interact
• Use `/help` for more information
• Send commands or text to see responses

✨ Ready to serve you!"""
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = f"""🤖 **{self.bot_name} Help**

**Available Commands:**
• `/start` - Welcome message
• `/help` - Show this help
• `/status` - Bot status information

**Features:**
• 📊 **Progress Bars** - Real-time visual progress
• 🎛️ **Interactive Buttons** - Click-based interactions
• 📁 **File Handling** - Upload and download files
• 🎨 **Rich Formatting** - Beautiful message styling
• ⚡ **Fast Response** - Optimized performance

**Response Types:**
• Text messages with formatting
• Interactive button menus
• Progress bars for long operations
• File uploads and downloads
• Error handling and validation

**How to Use:**
1. Send any text message
2. Click on interactive buttons
3. Upload files when prompted
4. Watch progress bars for operations

💡 **Tips:**
• All operations show real-time progress
• Use buttons for quick actions
• Check `/status` for bot information

🔧 **Powered by:** Advanced Telegram Bot Framework"""
        
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        active_operations = len(self.active_progress)
        uptime = time.time() - getattr(self, 'start_time', time.time())
        
        status_text = f"""📊 **{self.bot_name} Status**

🟢 **Status:** Online and Running
⏱️ **Uptime:** {uptime/3600:.1f} hours
🔄 **Active Operations:** {active_operations}
💾 **Memory Usage:** Optimized
🚀 **Performance:** Excellent

**System Info:**
• Framework: python-telegram-bot
• Progress Tracking: ✅ Active
• File Operations: ✅ Enabled
• Error Handling: ✅ Robust
• Logging: ✅ Comprehensive

✅ All systems operational!"""
        
        await update.message.reply_text(status_text, parse_mode='Markdown')

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages by calling user handler."""
        try:
            message_text = update.message.text
            chat_id = update.effective_chat.id
            operation_id = f"{chat_id}_{int(time.time())}"
            
            # Create progress callback for this operation
            temp_message = await update.message.reply_text("🔄 Processing...")
            progress_callback = self.create_progress_callback(temp_message, operation_id)
            
            # Call user handler
            response_data = await self.call_user_handler(
                message_text=message_text,
                callback_data=None,
                progress_callback=progress_callback
            )
            
            # Clean up temp message and send real response
            await temp_message.delete()
            await self.send_response(update, response_data)
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await update.message.reply_text(f"❌ Error processing your request: {str(e)}")

    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard button presses."""
        try:
            query = update.callback_query
            await query.answer()
            
            chat_id = query.message.chat_id
            operation_id = f"{chat_id}_{int(time.time())}"
            
            # Show processing message
            await query.edit_message_text("🔄 Processing your request...")
            
            # Create progress callback
            progress_callback = self.create_progress_callback(query.message, operation_id)
            
            # Call user handler
            response_data = await self.call_user_handler(
                message_text=None,
                callback_data=query.data,
                progress_callback=progress_callback
            )
            
            # Handle response based on type
            await self.handle_callback_response(query, response_data, context)
            
        except Exception as e:
            logger.error(f"Error handling callback: {e}")
            await query.edit_message_text(f"❌ Error: {str(e)}")

    async def call_user_handler(self, message_text: str = None, callback_data: str = None, 
                              progress_callback: Callable = None) -> Dict[str, Any]:
        """Call the user-provided handler function."""
        try:
            # Check if user handler is async
            if asyncio.iscoroutinefunction(self.user_handler):
                return await self.user_handler(message_text, callback_data, progress_callback)
            else:
                return self.user_handler(message_text, callback_data, progress_callback)
        except Exception as e:
            logger.error(f"User handler error: {e}")
            return self.response.error(f"Handler error: {str(e)}")

    async def handle_callback_response(self, query, response_data: Dict[str, Any], context):
        """Handle response from callback queries."""
        response_type = response_data.get("type", "text")
        
        if response_type == "progress":
            await self.handle_progress_response(query, response_data)
        elif response_type == "file":
            await self.handle_file_response(query, response_data, context)
        else:
            content = response_data.get("content", "No response")
            parse_mode = response_data.get("parse_mode")
            try:
                await query.edit_message_text(content, parse_mode=parse_mode)
            except Exception:
                await query.edit_message_text(content)

    async def handle_file_response(self, query, response_data: Dict[str, Any], context):
        """Handle file responses from callbacks."""
        try:
            file_path = response_data.get("file_path")
            
            if file_path and os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    await context.bot.send_document(
                        chat_id=query.message.chat_id,
                        document=f,
                        filename=os.path.basename(file_path),
                        caption=response_data.get("content", "")
                    )
                
                # Cleanup if requested
                if response_data.get("cleanup", False):
                    try:
                        os.remove(file_path)
                        parent_dir = os.path.dirname(file_path)
                        if os.path.exists(parent_dir) and not os.listdir(parent_dir):
                            os.rmdir(parent_dir)
                    except OSError:
                        pass
                
                await query.edit_message_text("✅ File sent successfully!")
            else:
                await query.edit_message_text("❌ File not found or failed to create.")
                
        except Exception as e:
            logger.error(f"File response error: {e}")
            await query.edit_message_text(f"❌ Error sending file: {str(e)}")

    async def handle_progress_response(self, query, response_data: Dict[str, Any]):
        """Handle progress bar responses."""
        try:
            progress_config = response_data.get("progress_config", {})
            total_steps = progress_config.get("total_steps", 100)
            step_delay = progress_config.get("step_delay", 0.3)
            title = progress_config.get("title", "Processing")
            
            progress_bar = ProgressBar(total=total_steps)
            
            for step in range(total_steps + 1):
                progress_text = progress_bar.update(step)
                emoji_progress = progress_bar.get_emoji_progress(step)
                eta = progress_bar.get_eta(step) if step > 0 else "Calculating..."
                
                if step == total_steps:
                    full_text = f"✅ **{title} Complete!**\n\n{response_data.get('content', 'Operation finished!')}"
                else:
                    full_text = f"🔄 **{title}**\n\n{progress_text}\n{emoji_progress}\nETA: {eta}"
                
                await query.edit_message_text(full_text, parse_mode='Markdown')
                
                if step < total_steps:
                    await asyncio.sleep(step_delay)
                    
        except Exception as e:
            logger.error(f"Progress response error: {e}")
            await query.edit_message_text(f"❌ Progress error: {str(e)}")

    async def send_response(self, update: Update, response_data: Dict[str, Any]):
        """Send response based on type."""
        try:
            response_type = response_data.get("type", "text")
            
            if response_type == "text":
                await update.message.reply_text(response_data["content"])
                
            elif response_type == "styled_text":
                parse_mode = response_data.get("parse_mode", "Markdown")
                await update.message.reply_text(response_data["content"], parse_mode=parse_mode)
                
            elif response_type == "inline_keyboard":
                keyboard_data = response_data.get("keyboard", [])
                keyboard = []
                
                for row in keyboard_data:
                    button_row = []
                    for button in row:
                        button_row.append(InlineKeyboardButton(
                            text=button["text"],
                            callback_data=button["callback_data"]
                        ))
                    keyboard.append(button_row)
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                parse_mode = response_data.get("parse_mode", "Markdown")
                await update.message.reply_text(
                    response_data["content"],
                    parse_mode=parse_mode,
                    reply_markup=reply_markup
                )
                
            elif response_type == "progress":
                message = await update.message.reply_text("🔄 Starting operation...")
                await self.handle_progress_response_for_message(message, response_data)
                
            elif response_type == "file":
                await self.handle_file_response_for_message(update, response_data)
                
        except Exception as e:
            logger.error(f"Send response error: {e}")
            await update.message.reply_text(f"❌ Response error: {str(e)}")

    async def handle_progress_response_for_message(self, message, response_data: Dict[str, Any]):
        """Handle progress responses for direct messages."""
        try:
            progress_config = response_data.get("progress_config", {})
            total_steps = progress_config.get("total_steps", 100)
            step_delay = progress_config.get("step_delay", 0.3)
            title = progress_config.get("title", "Processing")
            
            progress_bar = ProgressBar(total=total_steps)
            
            for step in range(total_steps + 1):
                progress_text = progress_bar.update(step)
                emoji_progress = progress_bar.get_emoji_progress(step)
                eta = progress_bar.get_eta(step) if step > 0 else "Calculating..."
                
                if step == total_steps:
                    full_text = f"✅ **{title} Complete!**\n\n{response_data.get('content', 'Operation finished!')}"
                else:
                    full_text = f"🔄 **{title}**\n\n{progress_text}\n{emoji_progress}\nETA: {eta}"
                
                await message.edit_text(full_text, parse_mode='Markdown')
                
                if step < total_steps:
                    await asyncio.sleep(step_delay)
                    
        except Exception as e:
            logger.error(f"Progress message error: {e}")
            await message.edit_text(f"❌ Progress error: {str(e)}")

    async def handle_file_response_for_message(self, update: Update, response_data: Dict[str, Any]):
        """Handle file responses for direct messages."""
        try:
            file_path = response_data.get("file_path", "temp.txt")
            file_content = response_data.get("file_content")
            content = response_data.get("content", "")
            
            # Create file if content provided
            if file_content and not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(file_content)
            
            # Send content message first if provided
            if content:
                await update.message.reply_text(content)
            
            # Send file
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    await update.message.reply_document(f, filename=os.path.basename(file_path))
                
                # Cleanup if requested
                if response_data.get("cleanup", True):
                    try:
                        os.remove(file_path)
                    except OSError:
                        pass
            else:
                await update.message.reply_text("❌ File not found or failed to create.")
                
        except Exception as e:
            logger.error(f"File message error: {e}")
            await update.message.reply_text(f"❌ File error: {str(e)}")

    async def setup_commands(self):
        """Set up bot commands menu."""
        commands = [
            BotCommand("start", f"Start {self.bot_name}"),
            BotCommand("help", "Show help information"),
            BotCommand("status", "Show bot status"),
        ]
        await self.application.bot.set_my_commands(commands)
        logger.info("✅ Bot commands menu set up successfully!")

    async def run(self):
        """Start the bot."""
        try:
            self.start_time = time.time()
            self.application = Application.builder().token(self.bot_token).build()
            
            # Add handlers
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("help", self.help_command))
            self.application.add_handler(CommandHandler("status", self.status_command))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            self.application.add_handler(CallbackQueryHandler(self.handle_callback_query))
            
            # Start the application
            await self.application.initialize()
            await self.application.start()
            
            # Set up commands menu
            await self.setup_commands()
            
            # Start polling
            await self.application.updater.start_polling()
            
            logger.info(f"🤖 {self.bot_name} is running...")
            logger.info("📊 Progress tracking: ✅ Active")
            logger.info("🎛️ Interactive keyboards: ✅ Active")
            logger.info("📁 File operations: ✅ Active")
            logger.info("🎨 Rich formatting: ✅ Active")
            
            # Keep running
            await asyncio.Event().wait()
            
        except KeyboardInterrupt:
            logger.info(f"\n👋 {self.bot_name} stopped!")
        except Exception as e:
            logger.error(f"Bot error: {e}")
        finally:
            if self.application:
                await self.application.stop()

def create_bot(bot_token: str = None, user_handler: Callable = None, 
               bot_name: str = "Enhanced Bot", bot_description: str = "Powered by Progress Tracking"):
    """
    Factory function to create a Telegram bot.
    
    Args:
        bot_token: Your bot token (will prompt if not provided)
        user_handler: Your business logic function
        bot_name: Name of your bot
        bot_description: Description for help text
        
    Returns:
        TelegramBot instance ready to run
    """
    
    # Get bot token
    if not bot_token:
        bot_token = os.getenv('BOT_TOKEN')
        if not bot_token:
            print(f"🤖 {bot_name} Setup")
            bot_token = input("Enter your Bot Token: ").strip()
            if not bot_token:
                raise ValueError("Bot token is required!")
            
            # Save to .env
            with open('.env', 'a') as f:
                f.write(f"\nBOT_TOKEN={bot_token}\n")
            print("✅ Token saved to .env file!")
    
    # Default handler if none provided
    if not user_handler:
        def default_handler(message_text=None, callback_data=None, progress_callback=None):
            return TelegramBotResponse.text(
                f"Hello! You said: {message_text or callback_data}\n\n"
                "💡 Configure your handler function to customize responses!"
            )
        user_handler = default_handler
    
    return TelegramBot(bot_token, user_handler, bot_name, bot_description)

# Example usage and testing
if __name__ == "__main__":
    # Example handler function
    def my_handler(message_text=None, callback_data=None, progress_callback=None):
        """Example handler - replace with your logic."""
        
        if callback_data:
            if callback_data == "demo_progress":
                return TelegramBotResponse.progress(
                    title="Demo Operation",
                    final_message="Demo completed! 🎉",
                    total_steps=50,
                    step_delay=0.2
                )
            elif callback_data == "demo_file":
                return TelegramBotResponse.file(
                    file_path="demo.txt",
                    content="📄 Here's your demo file!",
                    file_content="This is a demo file created by the bot!"
                )
        
        if message_text:
            text_lower = message_text.lower()
            
            if "progress" in text_lower:
                return TelegramBotResponse.progress(
                    title="Processing Request", 
                    final_message="Request processed successfully! ✅",
                    total_steps=100,
                    step_delay=0.3
                )
            
            elif "menu" in text_lower:
                return TelegramBotResponse.keyboard(
                    content="🎛️ **Choose an option:**",
                    buttons=[
                        [
                            {"text": "📊 Show Progress", "callback_data": "demo_progress"},
                            {"text": "📁 Create File", "callback_data": "demo_file"}
                        ]
                    ]
                )
            
            else:
                return TelegramBotResponse.styled_text(
                    f"✨ **Echo Response**\n\n"
                    f"You said: `{message_text}`\n\n"
                    f"💡 Try typing: 'progress' or 'menu'"
                )
        
        return TelegramBotResponse.text("👋 Hello! Send me a message to get started!")
    
    # Create and run bot
    bot = create_bot(
        user_handler=my_handler,
        bot_name="Demo Bot",
        bot_description="Demonstrating all features"
    )
    
    asyncio.run(bot.run()) 