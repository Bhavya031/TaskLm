#!/usr/bin/env python3
"""
TaskMind Main Agent - Conversational Problem Understanding & Routing
Uses OpenAI GPT-4o to understand user problems and route to specialized agents.
"""

import os
import json
import logging
from typing import Dict, List
from dataclasses import dataclass
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

@dataclass
class SpecializedAgent:
    """Represents a specialized agent that can handle specific tasks"""
    name: str
    emoji: str
    description: str
    keywords: List[str]
    boilerplate_path: str

class TaskMindMainAgent:
    """Main Agent that uses GPT-4o to understand problems and route to specialized agents"""
    
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.telegram_token = os.getenv('MAIN_AGENT_TOKEN')
        
        # Define specialized agents with their Telegram bot usernames
        self.specialized_agents = {
            'web_scraper': SpecializedAgent(
                name="Web Scraper Agent",
                emoji="🕷️",
                description="Data extraction, web scraping, crawling websites, parsing HTML/JSON",
                keywords=["scrape", "crawl", "extract", "web data", "parse", "html", "json", "api"],
                boilerplate_path="@web_scraper_meta_bot"
            ),
            'gdrive': SpecializedAgent(
                name="Google Drive Agent", 
                emoji="📁",
                description="Cloud file management, backup, sync, organize files in Google Drive",
                keywords=["file", "storage", "backup", "sync", "organize", "cloud", "drive", "upload", "google"],
                boilerplate_path="@gdrive_meta_bot"
            ),
            'whisper': SpecializedAgent(
                name="Whisper Audio Agent",
                emoji="🎵", 
                description="Speech-to-text transcription, audio analysis, voice processing",
                keywords=["audio", "transcribe", "speech", "voice", "whisper", "sound"],
                boilerplate_path="@whisper_meta_bot"
            ),
            'ffmpeg': SpecializedAgent(
                name="FFmpeg Media Agent",
                emoji="🎬",
                description="Video/audio processing, editing, conversion, media manipulation",
                keywords=["video", "audio", "ffmpeg", "convert", "edit", "media", "mp4", "processing"],
                boilerplate_path="@ffmpeg_meta_bot"
            ),
            'pdf_processor': SpecializedAgent(
                name="PDF Processor Agent",
                emoji="📄",
                description="Document manipulation, PDF processing, text extraction, document analysis",
                keywords=["pdf", "document", "text", "extract", "process", "file", "doc"],
                boilerplate_path="@pdf_processor_meta_bot"
            )
        }
        
        # User conversation state
        self.user_conversations = {}
    
    def analyze_user_problem(self, user_message: str, chat_history: List[Dict] = None) -> Dict:
        """Use GPT-4o to analyze user's problem and suggest appropriate agents"""
        
        agents_list = "\n".join([
            f"- {agent.emoji} {agent.name} (key: {key}): {agent.description}"
            for key, agent in self.specialized_agents.items()
        ])
        
        system_prompt = f"""You are TaskMind, an AI assistant that helps users solve technical problems by routing them to specialized agents.

Available Specialized Agents:
{agents_list}

Your job is to:
1. Understand the user's problem through conversation
2. Ask clarifying questions if needed
3. When you have enough information, recommend 1-3 most suitable specialized agents
4. Explain why each agent would be helpful for their specific problem

IMPORTANT: You MUST respond with ONLY valid JSON. No extra text, no markdown, just JSON.

JSON format:
{{
    "needs_more_info": boolean,
    "clarifying_questions": ["question1", "question2"],
    "response_message": "conversational response to user",
    "recommended_agents": ["agent_key1", "agent_key2"],
    "confidence": "high/medium/low"
}}

Keep responses conversational and helpful. Ask specific questions to better understand their use case."""

        messages = [{"role": "system", "content": system_prompt}]
        
        # Add chat history if available (limit to last 10 messages to avoid token limits)
        if chat_history:
            recent_history = chat_history[-10:] if len(chat_history) > 10 else chat_history
            messages.extend(recent_history)
        
        messages.append({"role": "user", "content": user_message})
        
        try:
            logger.info(f"Calling OpenAI with message: {user_message[:100]}...")
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.3,  # Lower temperature for more consistent JSON
                max_tokens=800,
                response_format={"type": "json_object"}  # Force JSON response
            )
            
            response_content = response.choices[0].message.content.strip()
            logger.info(f"OpenAI response: {response_content[:200]}...")
            
            # Parse JSON response
            analysis = json.loads(response_content)
            
            # Validate required fields
            required_fields = ["needs_more_info", "response_message", "confidence"]
            for field in required_fields:
                if field not in analysis:
                    analysis[field] = self._get_default_field_value(field)
            
            # Ensure lists exist
            if "clarifying_questions" not in analysis:
                analysis["clarifying_questions"] = []
            if "recommended_agents" not in analysis:
                analysis["recommended_agents"] = []
            
            logger.info(f"Analysis successful: {analysis.get('confidence', 'unknown')} confidence")
            return analysis
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}. Response was: {response_content if 'response_content' in locals() else 'No response'}")
            return self._create_fallback_analysis(user_message)
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return self._create_fallback_analysis(user_message)
    
    def _get_default_field_value(self, field: str):
        """Get default value for missing fields"""
        defaults = {
            "needs_more_info": False,
            "response_message": "I understand you need help. Let me connect you with our specialists.",
            "confidence": "medium",
            "clarifying_questions": [],
            "recommended_agents": []
        }
        return defaults.get(field, None)
    
    def _create_fallback_analysis(self, user_message: str) -> Dict:
        """Create fallback analysis when OpenAI fails"""
        # Simple keyword-based analysis as fallback
        message_lower = user_message.lower()
        
        # Basic keyword matching
        if any(word in message_lower for word in ["scrape", "crawl", "web", "extract", "data"]):
            recommended = ["web_scraper"]
            response = "I see you're interested in web scraping and data extraction. Our Web Scraper Agent can help you with that!"
            
        elif any(word in message_lower for word in ["audio", "transcribe", "speech", "voice", "sound", "whisper"]):
            recommended = ["whisper"]
            response = "It sounds like you need audio processing capabilities. Our Whisper Audio Agent specializes in transcription and analysis!"
            
        elif any(word in message_lower for word in ["video", "media", "ffmpeg", "convert", "edit", "processing"]):
            recommended = ["ffmpeg"]
            response = "I understand you're working with media content. Our FFmpeg Media Agent can help with video/audio processing!"
            
        elif any(word in message_lower for word in ["file", "storage", "backup", "cloud", "sync", "drive", "google"]):
            recommended = ["gdrive"]
            response = "File management and cloud storage - our Google Drive Agent is perfect for that!"
            
        elif any(word in message_lower for word in ["pdf", "document", "doc", "text", "extract"]):
            recommended = ["pdf_processor"]
            response = "Document processing - our PDF Processor Agent can help with document manipulation and text extraction!"
            
        else:
            recommended = ["web_scraper", "gdrive", "whisper"]
            response = "I'd like to understand your project better. Could you tell me more about what you're trying to build?"
        
        return {
            "needs_more_info": len(recommended) > 2,
            "clarifying_questions": ["What specific features do you need?", "What's your main goal with this project?"] if len(recommended) > 2 else [],
            "response_message": response,
            "recommended_agents": recommended,
            "confidence": "medium"
        }
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        self.user_conversations[user_id] = []
        
        welcome_message = """🧠 Welcome to TaskMind!

I'm here to understand your technical problem and connect you with the right specialized agent.

You can:
• Describe your problem naturally and I'll help route you
• Use the menu below for quick access to commands
• Type /help for detailed information

What problem are you trying to solve? 🤔"""
        
        # Create main menu keyboard
        keyboard = [
            [
                InlineKeyboardButton("🆘 Help", callback_data="cmd_help"),
                InlineKeyboardButton("🤖 List Agents", callback_data="cmd_list_bot")
            ],
            [
                InlineKeyboardButton("💬 Start Conversation", callback_data="cmd_conversation"),
                InlineKeyboardButton("🛑 Stop Bot", callback_data="cmd_stop")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """🤖 TaskMind Help

I can help you with:
• Understanding your technical problems through conversation
• Recommending the right specialized agent for your needs
• Connecting you with agents that can generate actual code

**Available Specialized Agents:**
"""
        for agent in self.specialized_agents.values():
            help_text += f"\n{agent.emoji} **{agent.name}**\n   {agent.description}\n"
        
        help_text += "\n💡 Just describe your problem naturally - I'll ask questions to understand and help!"
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command"""
        user_id = update.effective_user.id
        
        # Clear user conversation history
        if user_id in self.user_conversations:
            del self.user_conversations[user_id]
        
        stop_message = """🛑 TaskMind Bot Stopped

Your conversation history has been cleared.

To restart, use /start or simply send a new message.

Thank you for using TaskMind! 👋"""
        
        await update.message.reply_text(stop_message)
    
    async def list_bot_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list_bot command"""
        list_message = """🤖 Available Specialized Agents

Here are all the agents I can connect you with:

"""
        
        for i, (key, agent) in enumerate(self.specialized_agents.items(), 1):
            list_message += f"""**{i}. {agent.emoji} {agent.name}**
   📋 {agent.description}

"""
        
        list_message += """💡 **How to use:**
• Describe your problem naturally and I'll recommend the best agent
• Use /start to begin a conversation
• Use /help for more detailed information"""
        
        # Add quick select buttons
        keyboard = []
        for agent_key, agent in self.specialized_agents.items():
            keyboard.append([
                InlineKeyboardButton(
                    f"{agent.emoji} Select {agent.name}",
                    callback_data=f"quick_select_{agent_key}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("🔄 Back to Main Menu", callback_data="cmd_start")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(list_message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle user messages with GPT-4o analysis"""
        user_id = update.effective_user.id
        user_message = update.message.text
        
        # Initialize conversation history if needed
        if user_id not in self.user_conversations:
            self.user_conversations[user_id] = []
        
        # Add user message to history
        self.user_conversations[user_id].append({"role": "user", "content": user_message})
        
        # Analyze with GPT-4o
        analysis = self.analyze_user_problem(user_message, self.user_conversations[user_id])
        
        # Add assistant response to history
        self.user_conversations[user_id].append({"role": "assistant", "content": analysis["response_message"]})
        
        # Send response
        await update.message.reply_text(analysis["response_message"])
        
        # If ready to recommend agents, show options
        if not analysis.get("needs_more_info", True) and analysis.get("recommended_agents"):
            await self._show_agent_recommendations(update, analysis["recommended_agents"])
    
    async def _show_agent_recommendations(self, update: Update, recommended_agent_keys: List[str]):
        """Show recommended agents as interactive buttons"""
        keyboard = []
        
        for agent_key in recommended_agent_keys:
            if agent_key in self.specialized_agents:
                agent = self.specialized_agents[agent_key]
                keyboard.append([
                    InlineKeyboardButton(
                        f"{agent.emoji} {agent.name}",
                        callback_data=f"select_agent_{agent_key}"
                    )
                ])
        
        # Add option to continue conversation
        keyboard.append([
            InlineKeyboardButton("🤔 Tell me more about my problem", callback_data="continue_conversation")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🎯 Based on our conversation, here are my recommendations:",
            reply_markup=reply_markup
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        # Handle menu commands
        if query.data == "cmd_help":
            await self._show_help_inline(query)
        elif query.data == "cmd_list_bot":
            await self._show_list_bot_inline(query)
        elif query.data == "cmd_conversation":
            await query.edit_message_text("💬 Great! Just tell me about your problem and I'll help you find the right agent.\n\nWhat are you trying to build or accomplish?")
        elif query.data == "cmd_stop":
            await self._handle_stop_inline(query)
        elif query.data == "cmd_start":
            await self._show_start_menu(query)
        
        # Handle agent selection
        elif query.data.startswith("select_agent_"):
            agent_key = query.data.replace("select_agent_", "")
            await self._route_to_agent(query, agent_key)
        elif query.data.startswith("quick_select_"):
            agent_key = query.data.replace("quick_select_", "")
            await self._route_to_agent(query, agent_key)
        
        # Handle conversation flow
        elif query.data == "continue_conversation":
            await query.edit_message_text("Please tell me more about your specific requirements or use case. What details should I know?")
        elif query.data == "choose_different":
            await self._show_list_bot_inline(query)
    
    async def _route_to_agent(self, query, agent_key: str):
        """Route user to selected specialized agent"""
        if agent_key not in self.specialized_agents:
            await query.edit_message_text("❌ Agent not found. Please try again.")
            return
        
        agent = self.specialized_agents[agent_key]
        
        # Direct to agent details without intermediate message
        await self._show_agent_details(query, agent)
    
    async def _show_agent_details(self, query, agent: SpecializedAgent):
        """Show details about the selected agent"""
        details = f"""🎯 {agent.emoji} {agent.name} Ready!

Capabilities: {agent.description}

What happens next:
✅ You'll be redirected to the specialized {agent.name}
🤖 The agent will understand your specific requirements
⚡ You'll get custom solutions tailored to your needs

Ready to connect to {agent.boilerplate_path}?"""

        keyboard = [
            [InlineKeyboardButton("🚀 Go to Agent", url=f"https://t.me/{agent.boilerplate_path[1:]}")],
            [InlineKeyboardButton("🔄 Choose different agent", callback_data="choose_different")],
            [InlineKeyboardButton("💬 Continue conversation", callback_data="continue_conversation")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(details, reply_markup=reply_markup)
    
    async def _show_help_inline(self, query):
        """Show help message inline"""
        help_text = """🤖 TaskMind Help

**Available Commands:**
• `/start` - Show main menu and start fresh
• `/help` - Show this help message
• `/list_bot` - List all available agents
• `/stop` - Stop bot and clear conversation

**How to Use:**
• Describe your problem naturally and I'll analyze it
• I'll ask clarifying questions to understand your needs
• I'll recommend the best specialized agent for your task
• You can then proceed with that agent's capabilities

**Available Specialized Agents:**
"""
        for agent in self.specialized_agents.values():
            help_text += f"\n{agent.emoji} **{agent.name}**\n   {agent.description}\n"
        
        help_text += "\n💡 Just describe your problem naturally - I'll ask questions to understand and help!"
        
        keyboard = [[InlineKeyboardButton("🔄 Back to Main Menu", callback_data="cmd_start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def _show_list_bot_inline(self, query):
        """Show bot list inline"""
        list_message = """🤖 Available Specialized Agents

Here are all the agents I can connect you with:

"""
        
        for i, (key, agent) in enumerate(self.specialized_agents.items(), 1):
            list_message += f"""**{i}. {agent.emoji} {agent.name}**
   📋 {agent.description}

"""
        
        list_message += """💡 **Quick Actions:**
• Click any agent below to select it directly
• Use 'Back to Menu' to return to main options"""
        
        # Add quick select buttons
        keyboard = []
        for agent_key, agent in self.specialized_agents.items():
            keyboard.append([
                InlineKeyboardButton(
                    f"{agent.emoji} Select {agent.name}",
                    callback_data=f"quick_select_{agent_key}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("🔄 Back to Main Menu", callback_data="cmd_start")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(list_message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def _handle_stop_inline(self, query):
        """Handle stop command inline"""
        user_id = query.from_user.id
        
        # Clear user conversation history
        if user_id in self.user_conversations:
            del self.user_conversations[user_id]
        
        stop_message = """🛑 TaskMind Bot Stopped

Your conversation history has been cleared.

To restart, use /start or click the button below.

Thank you for using TaskMind! 👋"""
        
        keyboard = [[InlineKeyboardButton("🔄 Restart Bot", callback_data="cmd_start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(stop_message, reply_markup=reply_markup)
    
    async def _show_start_menu(self, query):
        """Show start menu inline"""
        welcome_message = """🧠 Welcome to TaskMind!

I'm here to understand your technical problem and connect you with the right specialized agent.

You can:
• Describe your problem naturally and I'll help route you
• Use the menu below for quick access to commands
• Type /help for detailed information

What would you like to do? 🤔"""
        
        # Create main menu keyboard
        keyboard = [
            [
                InlineKeyboardButton("🆘 Help", callback_data="cmd_help"),
                InlineKeyboardButton("🤖 List Agents", callback_data="cmd_list_bot")
            ],
            [
                InlineKeyboardButton("💬 Start Conversation", callback_data="cmd_conversation"),
                InlineKeyboardButton("🛑 Stop Bot", callback_data="cmd_stop")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(welcome_message, reply_markup=reply_markup)
    
    async def setup_bot_menu(self, application):
        """Setup the bot menu commands (left side menu in Telegram)"""
        commands = [
            BotCommand("start", "🚀 Start TaskMind and show main menu"),
            BotCommand("help", "🆘 Get help and see available commands"),
            BotCommand("list_bot", "🤖 List all available specialized agents"),
            BotCommand("stop", "🛑 Stop bot and clear conversation history")
        ]
        
        try:
            await application.bot.set_my_commands(commands)
            print("✅ Bot menu commands set successfully")
        except Exception as e:
            print(f"⚠️ Failed to set bot menu: {e}")
    
    def run(self):
        """Start the main agent"""
        if not self.telegram_token:
            print("❌ Please set MAIN_AGENT_TOKEN in your environment variables")
            return
        
        if not os.getenv('OPENAI_API_KEY'):
            print("❌ Please set OPENAI_API_KEY in your environment variables")
            return
        
        # Create application
        app = Application.builder().token(self.telegram_token).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("stop", self.stop_command))
        app.add_handler(CommandHandler("list_bot", self.list_bot_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Setup bot menu on startup
        async def post_init(application):
            await self.setup_bot_menu(application)
        
        app.post_init = post_init
        
        print("🧠 TaskMind Main Agent starting...")
        print("🤖 Using GPT-4o for problem understanding")
        print(f"📱 Available specialized agents: {len(self.specialized_agents)}")
        print("🍕 Setting up bot menu...")
        
        # Start the bot
        app.run_polling()

if __name__ == "__main__":
    agent = TaskMindMainAgent()
    agent.run() 