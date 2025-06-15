#!/usr/bin/env python3
"""
Web Scraper Meta Agent - Link Collection & Requirements Analysis
Uses GPT-4o to understand user scraping needs and collect target URLs.
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from web_page_analyzer import WebPageAnalyzer
from goose_prompt_generator import generate_goose_prompt

# Import goose automation with fallback
try:
    from goose import run_goose_automation
except ImportError:
    try:
        import sys
        sys.path.append('..')
        from goose import run_goose_automation
    except ImportError:
        logger.error("Could not import goose.py - make sure it's in the correct path")
        run_goose_automation = None

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

@dataclass
class ScrapingProject:
    """Represents a user's scraping project with requirements and links"""
    user_id: int
    project_name: str = ""
    target_urls: List[str] = None
    data_requirements: Dict = None
    scraping_frequency: str = ""
    output_format: str = ""
    specific_elements: List[str] = None
    context_history: List[Dict] = None
    status: str = "link_collection"  # link_collection, requirements_gathering, ready_for_scraping
    
    def __post_init__(self):
        if self.target_urls is None:
            self.target_urls = []
        if self.data_requirements is None:
            self.data_requirements = {}
        if self.specific_elements is None:
            self.specific_elements = []
        if self.context_history is None:
            self.context_history = []

class WebScraperMetaAgent:
    """Meta Agent for Web Scraping - Handles requirement analysis and link collection"""
    
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.telegram_token = os.getenv('WEB_SCRAPER_META_TOKEN')
        self.web_analyzer = WebPageAnalyzer()
        
        # User projects storage
        self.user_projects: Dict[int, ScrapingProject] = {}
    
    def analyze_scraping_requirements(self, user_message: str, project: ScrapingProject) -> Dict:
        """Use GPT-4o to analyze user's scraping requirements and guide the conversation"""
        
        exchange_count = len(project.context_history) // 2  # Count user-assistant pairs
        
        # Check if we should move to final summary stage
        if exchange_count >= 3 and project.target_urls and project.data_requirements.get("page_analyses"):
            return self._generate_final_project_summary(project, user_message)
        
        system_prompt = f"""You are a Web Scraping Requirements Analyst. Have a deep, probing conversation with users to understand exactly what they want to scrape and why.

CURRENT CONVERSATION STAGE: Exchange {exchange_count + 1} of 3 total exchanges needed.

Your approach:
1. EXCHANGE 1: Ask about their goal/project - what are they trying to achieve? Be curious about their business case or personal need.
2. EXCHANGE 2: Dig deeper into specifics - what exact data, which websites, how they'll use the data
3. EXCHANGE 3: Confirm understanding, clarify final details, and prepare for scraper generation

If URLs are provided early, focus specifically on those sites and ask detailed questions about what data they want from those exact pages.

IMPORTANT: If page analysis data is available (showing what data types are found on their pages), reference this information in your questions. For example: "I can see the pages have product prices and reviews - are you interested in tracking price changes over time?" or "The analysis shows contact information is available - do you need all contact details or specific fields?"

Be genuinely curious and ask follow-up questions that show you're thinking about their specific use case.

Respond in JSON format:
{{
    "stage": "conversation_deepening" | "requirements_clarification" | "technical_details" | "ready_to_proceed",
    "response_message": "conversational response - be genuinely curious and dig deeper",
    "probing_questions": ["deeper follow-up question that shows understanding"],
    "detected_urls": ["url1", "url2"] (if any URLs found in message),
    "understanding_level": "surface|getting_deeper|good_understanding|complete",
    "next_focus": "business_case|specific_data|technical_requirements|confirmation",
    "insights_gathered": ["key insight 1", "key insight 2"]
}}

BE CONVERSATIONAL, CURIOUS, AND DIG DEEP. Don't just collect requirements - understand their actual needs and challenges."""

        # Build conversation context
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add project context if available
        if project.context_history:
            messages.extend(project.context_history[-8:])  # Last 8 messages for context
        
        # Add current project info as context
        page_analyses = project.data_requirements.get("page_analyses", {})
        analysis_summary = ""
        if page_analyses:
            analysis_summary = "\n- Page analysis available for: " + ", ".join([url.split("//")[1].split("/")[0] for url in page_analyses.keys()])
            
            # Add key findings from analyses
            all_fields = []
            page_types = []
            for url, analysis in page_analyses.items():
                if "extractable_data" in analysis:
                    all_fields.extend(analysis["extractable_data"].get("primary_fields", []))
                if "page_type" in analysis:
                    page_types.append(analysis["page_type"])
            
            if all_fields:
                unique_fields = list(set(all_fields))[:8]  # Top 8 unique fields
                analysis_summary += f"\n- Available data types: {', '.join(unique_fields)}"
            if page_types:
                unique_types = list(set(page_types))
                analysis_summary += f"\n- Page types: {', '.join(unique_types)}"
        
        project_context = f"""
Current project info:
- URLs collected: {len(project.target_urls)} ({project.target_urls[:3]}{'...' if len(project.target_urls) > 3 else ''})
- Project name: {project.project_name or 'Not set'}
- Status: {project.status}{analysis_summary}
"""
        
        messages.append({"role": "system", "content": project_context})
        messages.append({"role": "user", "content": user_message})
        
        try:
            logger.info(f"Analyzing scraping requirements for user message: {user_message[:100]}...")
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.4,
                max_tokens=800,
                response_format={"type": "json_object"}
            )
            
            response_content = response.choices[0].message.content.strip()
            analysis = json.loads(response_content)
            
            # Validate and set defaults
            required_fields = ["stage", "response_message", "next_action", "confidence"]
            for field in required_fields:
                if field not in analysis:
                    analysis[field] = self._get_default_value(field)
            
            # Ensure lists exist
            if "probing_questions" not in analysis:
                analysis["probing_questions"] = []
            if "detected_urls" not in analysis:
                analysis["detected_urls"] = []
            if "insights_gathered" not in analysis:
                analysis["insights_gathered"] = []
            
            logger.info(f"Analysis complete - Stage: {analysis.get('stage')}, Confidence: {analysis.get('confidence')}")
            return analysis
            
        except Exception as e:
            logger.error(f"GPT-4o analysis error: {e}")
            return self._create_fallback_analysis(user_message, project)
    
    def _get_default_value(self, field: str):
        """Get default values for missing fields"""
        defaults = {
            "stage": "conversation_deepening",
            "response_message": "I'd love to help you with web scraping! Tell me about your project - what are you trying to achieve and why do you need this data?",
            "understanding_level": "surface",
            "next_focus": "business_case",
            "probing_questions": [],
            "detected_urls": [],
            "insights_gathered": []
        }
        return defaults.get(field, None)
    
    def _create_fallback_analysis(self, user_message: str, project: ScrapingProject) -> Dict:
        """Create fallback analysis when GPT-4o fails"""
        import re
        
        # Simple URL detection
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        detected_urls = re.findall(url_pattern, user_message)
        
        if detected_urls:
            response = f"Great! I can see you want to work with {detected_urls[0]}{'and others' if len(detected_urls) > 1 else ''}. Tell me more about your project - what specific information are you looking to extract from these sites and what will you do with that data?"
            understanding = "getting_deeper"
            focus = "specific_data"
        else:
            response = "I'd love to help you with web scraping! Tell me about your project - what are you trying to achieve? Are you building something for business, research, or personal use?"
            understanding = "surface"
            focus = "business_case"
        
        return {
            "stage": "conversation_deepening",
            "response_message": response,
            "probing_questions": ["What's the ultimate goal of collecting this data?"],
            "detected_urls": detected_urls,
            "understanding_level": understanding,
            "next_focus": focus,
            "insights_gathered": []
        }
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        
        # Initialize new project
        self.user_projects[user_id] = ScrapingProject(user_id=user_id)
        
        welcome_message = """🕷️ Welcome to Web Scraper Meta Agent!

I'll help you build a custom web scraper using AI automation:

🎯 **What I do:**
• Understand your scraping requirements
• Analyze target websites
• Generate optimized Goose prompts
• Create complete scraper code automatically

Tell me about your project - what are you trying to achieve? Are you:
• Building a business tool?
• Doing research or analysis?
• Monitoring competitors?
• Collecting data for a personal project?

I'm genuinely curious about your goals and what you're working on!

💬 **Need general help?** Visit our main bot: @faltu031_bot"""
        
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """🕷️ Web Scraper Meta Agent Help

I help you create custom web scrapers using AI automation:

🔍 **Step 1: Requirements Analysis**
- Share URLs you want to scrape
- I'll analyze page structure and data
- Deep conversation about your needs

🎯 **Step 2: Prompt Generation**  
- Generate optimized Goose AI prompts
- Include all technical specifications
- Schema and requirements mapping

🤖 **Step 3: Automated Scraper Creation**
- Use Goose AI for code generation
- Complete scraper with documentation
- Ready-to-run solution

**Commands:**
• /start - Begin new scraping project
• /status - Check current project status
• /reset - Start over with new project
• /testgoose - Check Goose availability

**Features:**
• AI-powered requirement analysis
• Automatic code generation
• Complete project documentation
• Error handling and validation

💬 **Need more help?** Visit @faltu031_bot

Just paste URLs or describe what you want to scrape!"""
        
        await update.message.reply_text(help_text)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_projects:
            await update.message.reply_text("No active project found. Use /start to begin!")
            return
        
        project = self.user_projects[user_id]
        
        status_message = f"""📊 Project Status

🏷️ **Project Name:** {project.project_name or 'Not set'}
🔗 **URLs Collected:** {len(project.target_urls)}
📈 **Stage:** {project.status.replace('_', ' ').title()}

**Target URLs:**"""
        
        if project.target_urls:
            for i, url in enumerate(project.target_urls[:5], 1):
                status_message += f"\n{i}. {url}"
            if len(project.target_urls) > 5:
                status_message += f"\n... and {len(project.target_urls) - 5} more"
        else:
            status_message += "\nNone yet - share some URLs to get started!"
        
        if len(project.target_urls) > 0:
            status_message += f"\n\n💬 Continue our conversation about what specific data you need from these sites!"
        else:
            status_message += f"\n\n💬 Tell me about your scraping project to get started!"
        
        await update.message.reply_text(status_message)
    
    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /reset command"""
        user_id = update.effective_user.id
        self.user_projects[user_id] = ScrapingProject(user_id=user_id)
        
        await update.message.reply_text("🔄 Project reset! Use /start to begin a new scraping project.")
    
    async def test_goose_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /testgoose command to check Goose availability"""
        await update.message.reply_text("🔍 Testing Goose availability...")
        
        # Check if goose automation function is available
        if run_goose_automation is None:
            status_message = """❌ **Goose Module Status: Not Available**

The goose.py module could not be imported.

**Debug Info:**
• Current working directory checked
• Python path checked
• Import paths verified

🔧 **To fix this:**
1. Make sure goose.py is in the same directory
2. Check Python import paths
3. Verify all dependencies

💬 **Need help?** Visit @faltu031_bot"""
        else:
            # Test CLI availability
            goose_available, goose_status = await self._check_goose_availability()
            
            if goose_available:
                status_message = f"""✅ **Goose Status: Available**

**Module:** ✅ goose.py imported successfully
**CLI:** ✅ {goose_status}

🚀 **Ready to generate scrapers!**
Use /start to begin a new project."""
            else:
                status_message = f"""⚠️ **Goose Status: Partial**

**Module:** ✅ goose.py imported successfully
**CLI:** ❌ {goose_status}

🔧 **To fix CLI issue:**
1. Install Goose CLI tool
2. Make sure it's in your PATH
3. Test with: `goose --version`

💬 **Need help?** Visit @faltu031_bot"""
        
        await update.message.reply_text(status_message, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle user messages with GPT-4o analysis"""
        user_id = update.effective_user.id
        user_message = update.message.text
        
        # Initialize project if needed
        if user_id not in self.user_projects:
            self.user_projects[user_id] = ScrapingProject(user_id=user_id)
        
        project = self.user_projects[user_id]
        
        # Add to conversation history
        project.context_history.append({"role": "user", "content": user_message})
        
        # Analyze with GPT-4o
        analysis = self.analyze_scraping_requirements(user_message, project)
        
        # Handle different stages
        if analysis.get("stage") == "project_summary_and_schema":
            await self._handle_final_summary(update, analysis, project)
            return
        
        # Process detected URLs and analyze them
        if analysis.get("detected_urls"):
            new_urls = [url for url in analysis["detected_urls"] if url not in project.target_urls]
            if new_urls:
                project.target_urls.extend(new_urls)
                logger.info(f"Added {len(new_urls)} URLs to project for user {user_id}")
                
                # Analyze the new URLs to understand page structure
                await self._analyze_and_present_urls(update, new_urls, project)
        
        # Update project status based on analysis
        if analysis.get("stage"):
            project.status = analysis["stage"]
        
        # Add assistant response to history
        project.context_history.append({"role": "assistant", "content": analysis["response_message"]})
        
        # Send response with follow-up question combined (only one message)
        response_message = analysis["response_message"]
        
        # Add follow-up question to the same message if we're still in conversation phase
        if analysis.get("probing_questions") and len(project.context_history) < 6:  # Reduced to 3 exchanges max
            follow_up = analysis["probing_questions"][0] if analysis["probing_questions"] else ""
            if follow_up:
                response_message += f"\n\n{follow_up.strip()}"
        
        await update.message.reply_text(response_message)
    
    async def _handle_final_summary(self, update: Update, analysis: Dict, project: ScrapingProject):
        """Handle the final project summary stage"""
        
        # Send the main summary message
        response_message = analysis.get("response_message", "")
        if response_message:
            await update.message.reply_text(response_message, parse_mode='Markdown')
        
        # Add detailed breakdown if available
        project_summary = analysis.get("project_summary", {})
        data_schema = analysis.get("data_schema", {})
        tech_requirements = analysis.get("technical_requirements", {})
        
        if project_summary and data_schema:
            # Create detailed breakdown message
            details_message = f"""📋 **DETAILED BREAKDOWN:**

🎯 **Project Details:**
• **Name:** {project_summary.get('project_name', 'Unnamed Project')}
• **Objective:** {project_summary.get('objective', 'Data extraction')}
• **Use Case:** {project_summary.get('use_case', 'Analysis and monitoring')}
• **Frequency:** {project_summary.get('frequency', 'As needed')}

📊 **Complete Data Schema:**"""
            
            # Add primary data fields
            primary_data = data_schema.get("primary_data", [])
            if primary_data:
                details_message += "\n\n**Primary Fields:**"
                for field in primary_data:
                    details_message += f"\n• `{field.get('field_name', 'unknown')}` ({field.get('data_type', 'string')}) - {field.get('description', 'No description')}"
            
            # Add secondary data fields
            secondary_data = data_schema.get("secondary_data", [])
            if secondary_data:
                details_message += "\n\n**Additional Fields:**"
                for field in secondary_data[:5]:  # Limit to 5
                    details_message += f"\n• `{field.get('field_name', 'unknown')}` ({field.get('data_type', 'string')}) - {field.get('description', 'No description')}"
                if len(secondary_data) > 5:
                    details_message += f"\n• ... and {len(secondary_data) - 5} more fields"
            

            
            await update.message.reply_text(details_message, parse_mode='Markdown')
        
        # Add final question with options
        final_question = analysis.get("final_question", "Is there anything else you'd like to clarify or modify?")
        
        # Create inline keyboard for common follow-up actions
        keyboard = [
            [InlineKeyboardButton("✅ Looks Perfect!", callback_data="confirm_project")],
            [InlineKeyboardButton("🔧 Modify Something", callback_data="modify_project")],
            [InlineKeyboardButton("❓ Ask Questions", callback_data="ask_questions")],
            [InlineKeyboardButton("📊 Show Full Schema", callback_data="show_full_schema")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"💬 **{final_question}**\n\nChoose an option below or just type your response:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # Update project status
        project.status = "awaiting_final_confirmation"
        
        # Store the analysis for potential scraper generation
        project.data_requirements["final_analysis"] = analysis
    
    async def _analyze_and_present_urls(self, update: Update, urls: List[str], project: ScrapingProject):
        """Analyze URLs using Firecrawl and present findings to user"""
        
        # Send initial message
        await update.message.reply_text("🔍 Let me analyze these pages to understand what data is available...")
        
        try:
            # Analyze URLs (limit to first 3 to avoid overwhelming)
            urls_to_analyze = urls[:3]
            
            for i, url in enumerate(urls_to_analyze, 1):
                try:
                    # Show progress
                    if len(urls_to_analyze) > 1:
                        await update.message.reply_text(f"📊 Analyzing page {i}/{len(urls_to_analyze)}: {url}")
                    
                    # Analyze the page
                    result = self.web_analyzer.analyze_page_structure(url)
                    
                    if result.get("success") and result.get("analysis"):
                        analysis = result["analysis"]
                        
                        # Create user-friendly summary
                        summary = self._create_analysis_summary(url, analysis)
                        await update.message.reply_text(summary)
                        
                        # Store analysis in project for future reference
                        if "page_analyses" not in project.data_requirements:
                            project.data_requirements["page_analyses"] = {}
                        project.data_requirements["page_analyses"][url] = analysis
                        
                    else:
                        error_msg = result.get("error", "Unknown error")
                        await update.message.reply_text(f"⚠️ Couldn't analyze {url}: {error_msg}")
                        
                except Exception as e:
                    logger.error(f"Error analyzing URL {url}: {str(e)}")
                    await update.message.reply_text(f"⚠️ Had trouble analyzing {url} - we can still work with it though!")
            
            # Provide next steps
            if len(urls) > 3:
                await update.message.reply_text(f"📝 I analyzed the first 3 URLs. I can analyze the remaining {len(urls) - 3} if needed.")
            
            await update.message.reply_text("💡 Based on what I found, what specific data are you most interested in extracting?")
            
        except Exception as e:
            logger.error(f"Error in URL analysis: {str(e)}")
            await update.message.reply_text("⚠️ Had some trouble with the analysis, but let's continue our conversation about what you need!")
    
    def _create_analysis_summary(self, url: str, analysis: Dict) -> str:
        """Create a user-friendly summary of page analysis"""
        
        page_type = analysis.get("page_type", "unknown")
        main_content = analysis.get("main_content_type", "content")
        data_richness = analysis.get("data_richness", "medium")
        complexity = analysis.get("scraping_complexity", "moderate")
        
        # Get extractable data
        extractable = analysis.get("extractable_data", {})
        primary_fields = extractable.get("primary_fields", [])
        secondary_fields = extractable.get("secondary_fields", [])
        
        # Create summary
        summary = f"""📋 **Analysis of {url}**

🏷️ **Page Type:** {page_type.replace('_', ' ').title()}
📄 **Content:** {main_content}
💎 **Data Richness:** {data_richness.title()}
⚙️ **Complexity:** {complexity.title()}

🎯 **Main Data Available:**"""
        
        if primary_fields:
            for field in primary_fields[:5]:  # Show top 5
                summary += f"\n• {field}"
            if len(primary_fields) > 5:
                summary += f"\n• ... and {len(primary_fields) - 5} more fields"
        else:
            summary += "\n• General content and text"
        
        if secondary_fields:
            summary += f"\n\n📊 **Additional Data:**"
            for field in secondary_fields[:3]:  # Show top 3
                summary += f"\n• {field}"
        
        # Add insights if available
        insights = analysis.get("key_insights", [])
        if insights:
            summary += f"\n\n💡 **Key Insights:**"
            for insight in insights[:2]:  # Show top 2
                summary += f"\n• {insight}"
        
        return summary
    
    async def _show_status_inline(self, query):
        """Show project status inline"""
        user_id = query.from_user.id
        project = self.user_projects.get(user_id)
        
        if not project:
            await query.edit_message_text("No active project. Start a conversation to begin!")
            return
            
        status_message = f"""📊 Current Project Status

🔗 URLs collected: {len(project.target_urls)}
📈 Conversation exchanges: {len(project.context_history) // 2}
📋 Understanding level: {project.status.replace('_', ' ').title()}

Continue our conversation to build your scraper!"""
        
        await query.edit_message_text(status_message)
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # Initialize project if needed
        if user_id not in self.user_projects:
            self.user_projects[user_id] = ScrapingProject(user_id=user_id)
        
        project = self.user_projects[user_id]
        
        if query.data == "reset_project":
            await self._reset_project_inline(query)
        elif query.data == "show_status":
            await self._show_status_inline(query)
        elif query.data == "confirm_project":
            await self._handle_project_confirmation(query, project)
        elif query.data == "modify_project":
            await self._handle_project_modification(query, project)
        elif query.data == "ask_questions":
            await self._handle_project_questions(query, project)
        elif query.data == "show_full_schema":
            await self._show_full_schema(query, project)
        elif query.data == "view_goose_prompt":
            await self._show_goose_prompt(query, project)
        elif query.data == "copy_prompt":
            await self._handle_copy_prompt(query, project)
        elif query.data == "use_with_goose":
            await self._handle_use_with_goose(query, project)
        elif query.data == "back_to_summary":
            await self._handle_back_to_summary(query, project)
        elif query.data == "generate_scraper":
            await self._handle_generate_scraper(query, project)
        elif query.data == "view_file_details":
            await self._handle_view_file_details(query, project)
    
    async def _handle_project_confirmation(self, query, project: ScrapingProject):
        """Handle project confirmation"""
        confirmation_message = f"""✅ **Project Confirmed!**

Perfect! Your web scraping project is ready for implementation.

🤖 **Goose Prompt Generated:** I've created an optimized prompt for Goose AI automation based on your requirements.

🚀 **What happens next:**
1. Use the generated Goose prompt for AI automation
2. Get a complete scraper solution with documentation
3. The scraper will be tested with your target URLs
4. Receive usage examples and deployment instructions

📧 **Your project summary and Goose prompt have been saved and are ready to use.**

Choose your next step:"""
        
        # Create next action buttons
        keyboard = [
            [InlineKeyboardButton("🔥 Generate Scraper Now!", callback_data="generate_scraper")],
            [InlineKeyboardButton("🤖 View Goose Prompt", callback_data="view_goose_prompt")],
            [InlineKeyboardButton("💾 Save for Later", callback_data="save_project")],
            [InlineKeyboardButton("📄 Export Summary", callback_data="export_summary")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            confirmation_message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        project.status = "confirmed_ready_for_generation"
        
        # Generate goose prompt based on project details
        await self._generate_and_store_goose_prompt(project)
    
    async def _generate_and_store_goose_prompt(self, project: ScrapingProject):
        """Generate goose prompt from project details and store it"""
        try:
            # Extract project details for goose prompt generation
            final_analysis = project.data_requirements.get("final_analysis", {})
            project_summary = final_analysis.get("project_summary", {})
            data_schema = final_analysis.get("data_schema", {})
            tech_requirements = final_analysis.get("technical_requirements", {})
            
            # Create detailed user request string for goose prompt generation
            user_request = f"""
Build a web scraper with the following specifications:

PROJECT DETAILS:
- Project Name: {project_summary.get('project_name', 'Web Scraping Project')}
- Objective: {project_summary.get('objective', 'Extract data from websites')}
- Target Websites: {', '.join(project_summary.get('target_websites', []))}
- Use Case: {project_summary.get('use_case', 'Data analysis')}
- Frequency: {project_summary.get('frequency', 'As needed')}

TARGET URLS:
{chr(10).join([f"- {url}" for url in project.target_urls])}

DATA SCHEMA TO EXTRACT:
Primary Data Fields:
{chr(10).join([f"- {field.get('field_name', 'unknown')} ({field.get('data_type', 'string')}): {field.get('description', 'No description')}" for field in data_schema.get('primary_data', [])])}

Secondary Data Fields:
{chr(10).join([f"- {field.get('field_name', 'unknown')} ({field.get('data_type', 'string')}): {field.get('description', 'No description')}" for field in data_schema.get('secondary_data', [])])}

TECHNICAL REQUIREMENTS:
- Scraping Method: {tech_requirements.get('scraping_method', 'Standard HTTP scraping')}
- Complexity Level: {tech_requirements.get('complexity_level', 'Medium')}
- Special Considerations: {', '.join(tech_requirements.get('special_considerations', ['Standard handling']))}
- Output Format: JSON with structured data

Please create a complete, production-ready web scraper that can extract this data reliably and efficiently.
""".strip()

            # Generate goose prompt
            logger.info("Generating goose prompt for confirmed project...")
            goose_prompt = generate_goose_prompt(user_request)
            
            if goose_prompt:
                # Store the goose prompt in project data
                project.data_requirements["goose_prompt"] = goose_prompt
                project.data_requirements["goose_user_request"] = user_request
                logger.info("Goose prompt generated and stored successfully")
            else:
                logger.error("Failed to generate goose prompt")
                
        except Exception as e:
            logger.error(f"Error generating goose prompt: {e}")
    
    async def _handle_project_modification(self, query, project: ScrapingProject):
        """Handle project modification request"""
        modification_message = f"""🔧 **What would you like to modify?**

Choose what you'd like to change about your scraping project:

**Current Project:**
• **URLs:** {len(project.target_urls)} target URLs
• **Status:** {project.status.replace('_', ' ').title()}
• **Data Fields:** {len(project.data_requirements.get('page_analyses', {}))} analyzed pages

**What needs adjusting?**"""
        
        keyboard = [
            [InlineKeyboardButton("🔗 Add/Remove URLs", callback_data="modify_urls")],
            [InlineKeyboardButton("📊 Change Data Fields", callback_data="modify_fields")],
            [InlineKeyboardButton("⏱️ Update Frequency", callback_data="modify_frequency")],
            [InlineKeyboardButton("📁 Change Output Format", callback_data="modify_output")],
            [InlineKeyboardButton("💬 Start Over Discussion", callback_data="restart_conversation")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            modification_message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def _handle_project_questions(self, query, project: ScrapingProject):
        """Handle project questions"""
        questions_message = f"""❓ **Common Questions About Your Project**

Here are some things you might want to know:

**Technical Questions:**
• How will the scraper handle dynamic content?
• What happens if a website changes its structure?
• How often can I run the scraper safely?
• Will it work with JavaScript-heavy sites?

**Data Questions:**
• What format will the output data be in?
• How do I handle missing or optional fields?
• Can I filter or transform the data during scraping?

**Practical Questions:**
• How do I deploy and run the scraper?
• What if I need to scale to more URLs?
• How do I handle rate limiting and errors?

💬 **Type your specific question, or I can address these common ones!**"""
        
        keyboard = [
            [InlineKeyboardButton("⚡ Technical Details", callback_data="tech_questions")],
            [InlineKeyboardButton("📊 Data Handling", callback_data="data_questions")],
            [InlineKeyboardButton("🚀 Deployment", callback_data="deploy_questions")],
            [InlineKeyboardButton("↩️ Back to Summary", callback_data="back_to_summary")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            questions_message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def _show_full_schema(self, query, project: ScrapingProject):
        """Show complete data schema"""
        
        final_analysis = project.data_requirements.get("final_analysis", {})
        data_schema = final_analysis.get("data_schema", {})
        
        if not data_schema:
            await query.edit_message_text(
                "📊 **Schema not available yet.** Complete the conversation to generate your full data schema!",
                parse_mode='Markdown'
            )
            return
        
        schema_message = f"""📊 **COMPLETE DATA SCHEMA**

This is the full structure of data you'll receive from your scraper:

```json
{{"""
        
        # Add all primary fields
        primary_data = data_schema.get("primary_data", [])
        secondary_data = data_schema.get("secondary_data", [])
        
        all_fields = primary_data + secondary_data
        
        for i, field in enumerate(all_fields):
            field_name = field.get('field_name', f'field_{i}')
            data_type = field.get('data_type', 'string')
            description = field.get('description', 'No description')
            optional = field.get('optional', False)
            
            optional_marker = '?' if optional else ''
            schema_message += f'''
  "{field_name}"{optional_marker}: "{data_type}", // {description}'''
        
        schema_message += '''
}
```

**Output Structure:**
''' + data_schema.get('output_structure', 'JSON format with structured fields')
        
        # Add technical details
        tech_req = final_analysis.get('technical_requirements', {})
        if tech_req:
            schema_message += f"""

⚙️ **Technical Implementation:**
• **Method:** {tech_req.get('scraping_method', 'HTTP scraping')}
• **Complexity:** {tech_req.get('complexity_level', 'Medium')}
• **Considerations:** {', '.join(tech_req.get('special_considerations', ['Standard handling']))}"""
        
        keyboard = [[InlineKeyboardButton("↩️ Back to Summary", callback_data="back_to_summary")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            schema_message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def _show_goose_prompt(self, query, project: ScrapingProject):
        """Show the generated goose prompt"""
        
        goose_prompt = project.data_requirements.get("goose_prompt")
        
        if not goose_prompt:
            await query.edit_message_text(
                "🤖 **Goose Prompt Not Available**\n\nThe goose prompt hasn't been generated yet. Please confirm your project first to generate the optimized prompt.",
                parse_mode='Markdown'
            )
            return
        
        # Truncate prompt if too long for Telegram
        if len(goose_prompt) > 3500:  # Leave room for formatting
            prompt_preview = goose_prompt[:3500] + "\n\n... [TRUNCATED - Full prompt available in project data]"
        else:
            prompt_preview = goose_prompt
        
        goose_message = f"""🤖 **GENERATED GOOSE PROMPT**

This optimized prompt can be used with Goose AI automation to build your web scraper:

```
{prompt_preview}
```

💡 **How to use:**
1. Copy this prompt
2. Use it with Goose AI automation
3. Goose will generate the complete scraper code
4. Follow the implementation steps provided

🎯 **This prompt contains all your project requirements and technical specifications for optimal results.**"""
        
        keyboard = [
            [InlineKeyboardButton("📋 Copy Prompt", callback_data="copy_prompt")],
            [InlineKeyboardButton("🚀 Use with Goose", callback_data="use_with_goose")],
            [InlineKeyboardButton("↩️ Back to Summary", callback_data="back_to_summary")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            goose_message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def _handle_copy_prompt(self, query, project: ScrapingProject):
        """Handle copy prompt request"""
        goose_prompt = project.data_requirements.get("goose_prompt")
        
        if goose_prompt:
            # For Telegram, we can't directly copy to clipboard, so show instructions
            copy_message = f"""📋 **Copy Goose Prompt**

Here's your complete goose prompt ready to copy:

```
{goose_prompt}
```

💡 **Instructions:**
1. Select and copy the text above
2. Paste it into your Goose AI automation tool
3. Run the automation to generate your scraper

📧 The prompt has been optimized for best results with Goose."""
            
            keyboard = [[InlineKeyboardButton("↩️ Back", callback_data="view_goose_prompt")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                copy_message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await query.answer("❌ No prompt available", show_alert=True)
    
    async def _handle_use_with_goose(self, query, project: ScrapingProject):
        """Handle using prompt with Goose automation"""
        use_message = f"""🚀 **Using with Goose Automation**

Your project is ready for Goose AI automation!

🎯 **What you'll get:**
• Complete web scraper code
• Requirements.txt file
• Documentation
• Usage examples
• Error handling
• Data validation

📋 **Steps to use:**
1. Copy the generated prompt
2. Open your Goose AI automation tool
3. Paste the prompt and run
4. Follow the generated implementation

⚡ **The prompt contains all technical specifications and requirements for optimal scraper generation.**

Ready to proceed?"""
        
        keyboard = [
            [InlineKeyboardButton("📋 Get Prompt", callback_data="copy_prompt")],
            [InlineKeyboardButton("🤖 View Prompt", callback_data="view_goose_prompt")],
            [InlineKeyboardButton("↩️ Back to Summary", callback_data="back_to_summary")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            use_message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def _handle_back_to_summary(self, query, project: ScrapingProject):
        """Handle back to summary navigation"""
        # Recreate the confirmation message and buttons
        confirmation_message = f"""✅ **Project Confirmed!**

Perfect! Your web scraping project is ready for implementation.

🚀 **What happens next:**
1. I'll generate custom scraper code based on your requirements
2. You'll receive a complete solution with documentation
3. The scraper will be tested with your target URLs
4. You'll get usage examples and deployment instructions

📧 **Your project summary has been saved and will be used to create your custom scraper.**

Would you like me to proceed with generating the scraper code now?"""
        
        # Create next action buttons
        keyboard = [
            [InlineKeyboardButton("🔥 Generate Scraper Now!", callback_data="generate_scraper")],
            [InlineKeyboardButton("🤖 View Goose Prompt", callback_data="view_goose_prompt")],
            [InlineKeyboardButton("💾 Save for Later", callback_data="save_project")],
            [InlineKeyboardButton("📄 Export Summary", callback_data="export_summary")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            confirmation_message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def _handle_generate_scraper(self, query, project: ScrapingProject):
        """Handle scraper generation using Goose automation with step tracking"""
        
        # Check if goose prompt is available
        goose_prompt = project.data_requirements.get("goose_prompt")
        if not goose_prompt:
            await query.edit_message_text(
                "❌ **No Goose prompt available**\n\nPlease confirm your project first to generate the required prompt.",
                parse_mode='Markdown'
            )
            return
        
        try:
            # Step 0: Check if goose automation function is available
            if run_goose_automation is None:
                error_message = """❌ **Goose Module Not Available**

The goose.py module could not be imported.

🔧 **To fix this:**
1. Make sure goose.py is in the same directory
2. Check that all imports are working
3. Verify Python path configuration

🤖 **Need help?** Visit @faltu031_bot"""
                
                keyboard = [
                    [InlineKeyboardButton("💬 Get Help @faltu031_bot", url="https://t.me/faltu031_bot")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(error_message, reply_markup=reply_markup, parse_mode='Markdown')
                return
            
            # Step 1: Check Goose availability
            await self._update_generation_status(query, "🔍 **Step 1:** Checking Goose availability...")
            
            goose_available, goose_error = await self._check_goose_availability()
            if not goose_available:
                error_message = f"""❌ **Goose Not Available**

{goose_error}

🔧 **To fix this:**
1. Install Goose: `pip install goose-ai`
2. Make sure Goose is in your PATH
3. Test with: `goose --version`

🤖 **Need help?** Visit @faltu031_bot"""
                
                keyboard = [
                    [InlineKeyboardButton("🔄 Try Again", callback_data="generate_scraper")],
                    [InlineKeyboardButton("💬 Get Help @faltu031_bot", url="https://t.me/faltu031_bot")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(error_message, reply_markup=reply_markup, parse_mode='Markdown')
                return
            
            # Step 2: Starting Goose session
            await self._update_generation_status(query, "🚀 **Step 2:** Starting Goose session...")
            await asyncio.sleep(2)  # Let user see the step
            
            # Step 3: Sending prompt
            await self._update_generation_status(query, "📝 **Step 3:** Sending optimized prompt to Goose...")
            await asyncio.sleep(2)
            
            # Step 4: Generation in progress
            await self._update_generation_status(query, "⚙️ **Step 4:** Goose is generating your scraper...\n\n⏳ This may take 30-90 seconds")
            
            # Run goose automation in a separate thread to avoid blocking
            import concurrent.futures
            
            # Create executor for running blocking goose automation
            with concurrent.futures.ThreadPoolExecutor() as executor:
                logger.info("Starting Goose automation for scraper generation...")
                
                # Run the goose automation in thread
                future = executor.submit(
                    run_goose_automation,
                    goose_prompt, 
                    ['*.py', '*.txt', '*.md', '*.json']
                )
                
                # Wait with timeout and periodic updates
                timeout_seconds = 120  # 2 minutes timeout
                elapsed = 0
                
                while elapsed < timeout_seconds:
                    if future.done():
                        break
                    
                    await asyncio.sleep(5)
                    elapsed += 5
                    
                    # Update progress every 15 seconds
                    if elapsed % 15 == 0:
                        progress_msg = f"⚙️ **Step 4:** Goose is generating your scraper...\n\n⏳ Time elapsed: {elapsed}s / {timeout_seconds}s\n\n*Please wait, generation in progress...*"
                        await self._update_generation_status(query, progress_msg)
                
                # Get result
                if future.done():
                    success, generated_file = future.result()
                else:
                    # Timeout
                    await self._update_generation_status(query, "⏰ **Timeout:** Goose is taking longer than expected...")
                    success, generated_file = False, None
            
            # Step 5: Processing results
            await self._update_generation_status(query, "🔍 **Step 5:** Processing generation results...")
            await asyncio.sleep(1)
            
            if success and generated_file:
                # Success message with file info
                success_message = f"""✅ **Scraper Generated Successfully!**

🎉 Your custom web scraper has been created!

📁 **Generated File:** `{generated_file.name}`
📂 **Location:** `{generated_file.parent}`

🚀 **What's included:**
• Complete web scraper code
• Requirements and dependencies
• Usage instructions
• Error handling
• Data validation

🤖 **Ready to use your scraper?**
Check the generated file and follow the instructions to start scraping!

---

💬 **Need more help?** Visit our main bot: @faltu031_bot"""
                
                keyboard = [
                    [InlineKeyboardButton("📁 View File Details", callback_data="view_file_details")],
                    [InlineKeyboardButton("🔄 Generate Another", callback_data="reset_project")],
                    [InlineKeyboardButton("💬 Chat with @faltu031_bot", url="https://t.me/faltu031_bot")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    success_message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
                # Update project status
                project.status = "scraper_generated"
                project.data_requirements["generated_file"] = str(generated_file)
                
                logger.info(f"Scraper generated successfully: {generated_file}")
                
            else:
                # Generation failed
                failure_message = f"""❌ **Scraper Generation Failed**

😞 I encountered an issue while generating your scraper.

**Possible causes:**
• Goose session timeout or disconnection
• Network connectivity issues
• Goose service unavailable
• Complex prompt requiring manual intervention

🔧 **What you can try:**
• Check your internet connection
• Verify Goose is properly installed and running
• Try generating again in a few minutes
• Use the generated prompt manually with Goose

🤖 **Need help?** Visit our main bot: @faltu031_bot

The generated prompt is still available if you want to try manually or with other tools."""
                
                keyboard = [
                    [InlineKeyboardButton("🔄 Try Again", callback_data="generate_scraper")],
                    [InlineKeyboardButton("🤖 View Goose Prompt", callback_data="view_goose_prompt")],
                    [InlineKeyboardButton("💬 Get Help @faltu031_bot", url="https://t.me/faltu031_bot")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    failure_message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
                logger.error("Scraper generation failed")
                
        except Exception as e:
            logger.error(f"Error during scraper generation: {e}")
            
            # Escape error message for Markdown
            error_msg = str(e).replace('`', '').replace('*', '').replace('_', '').replace('[', '').replace(']', '')
            
            error_message = f"""💥 **Unexpected Error**

An error occurred during scraper generation:
```
{error_msg}
```

**Debug Information:**
• Error Type: {type(e).__name__}
• Step: Goose automation process

🔧 **What you can try:**
• Try again in a few minutes
• Check the logs for more details
• Verify Goose installation
• Use the Goose prompt manually

🤖 **Need assistance?** Visit: @faltu031_bot"""
            
            keyboard = [
                [InlineKeyboardButton("🔄 Try Again", callback_data="generate_scraper")],
                [InlineKeyboardButton("🤖 View Goose Prompt", callback_data="view_goose_prompt")],
                [InlineKeyboardButton("💬 Get Support @faltu031_bot", url="https://t.me/faltu031_bot")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                error_message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    async def _update_generation_status(self, query, status_message: str):
        """Update the user with current generation status"""
        try:
            await query.edit_message_text(status_message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error updating status: {e}")
    
    async def _check_goose_availability(self) -> tuple[bool, str]:
        """Check if Goose is available and properly configured"""
        try:
            # First try the common installation path
            goose_path = "/Users/bhavya/.local/bin/goose"
            
            if Path(goose_path).exists():
                goose_cmd = goose_path
            else:
                # Try to find goose in PATH using which command
                try:
                    result = await asyncio.create_subprocess_exec(
                        'which', 'goose',
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await result.communicate()
                    
                    if result.returncode == 0:
                        goose_cmd = 'goose'
                    else:
                        return False, "Goose executable not found in PATH or expected location"
                except Exception as e:
                    return False, f"Error searching for Goose: {str(e)}"
            
            # Try to run goose --version to verify it works
            try:
                version_result = await asyncio.create_subprocess_exec(
                    goose_cmd, '--version',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                version_stdout, version_stderr = await version_result.communicate()
                
                if version_result.returncode == 0:
                    version_info = version_stdout.decode().strip()
                    return True, f"Goose available: {version_info}"
                else:
                    error_msg = version_stderr.decode().strip() if version_stderr else "Unknown error"
                    return False, f"Goose found but not working: {error_msg}"
                    
            except Exception as e:
                return False, f"Error testing Goose: {str(e)}"
                
        except Exception as e:
            return False, f"Error checking Goose: {str(e)}"
    
    async def _handle_view_file_details(self, query, project: ScrapingProject):
        """Handle viewing file details of generated scraper"""
        
        generated_file_path = project.data_requirements.get("generated_file")
        if not generated_file_path:
            await query.edit_message_text(
                "❌ **No generated file found**\n\nPlease generate a scraper first.",
                parse_mode='Markdown'
            )
            return
        
        try:
            from pathlib import Path
            generated_file = Path(generated_file_path)
            
            if not generated_file.exists():
                await query.edit_message_text(
                    f"❌ **File not found**\n\nThe file `{generated_file.name}` could not be located.",
                    parse_mode='Markdown'
                )
                return
            
            # Get file info
            file_size = generated_file.stat().st_size
            file_extension = generated_file.suffix
            
            # Read first few lines of the file for preview
            try:
                with open(generated_file, 'r', encoding='utf-8') as f:
                    content_lines = f.readlines()
                    preview_lines = content_lines[:10]  # First 10 lines
                    preview = ''.join(preview_lines)
                    if len(content_lines) > 10:
                        preview += f"\n... ({len(content_lines) - 10} more lines)"
            except Exception as e:
                preview = f"Could not read file content: {e}"
            
            details_message = f"""📁 **Generated File Details**

**File Information:**
• **Name:** `{generated_file.name}`
• **Type:** `{file_extension}` file
• **Size:** {file_size} bytes
• **Lines:** {len(content_lines) if 'content_lines' in locals() else 'Unknown'}
• **Location:** `{generated_file.parent}`

**Content Preview:**
```python
{preview[:800]}{'...' if len(preview) > 800 else ''}
```

🚀 **How to use:**
1. Navigate to the file location
2. Install requirements: `pip install -r requirements.txt`
3. Run the scraper: `python {generated_file.name}`
4. Follow any additional instructions in the file

💬 **Need help?** Visit @faltu031_bot for support!"""
            
            keyboard = [
                [InlineKeyboardButton("🔄 Generate Another", callback_data="reset_project")],
                [InlineKeyboardButton("↩️ Back", callback_data="generate_scraper")],
                [InlineKeyboardButton("💬 Chat @faltu031_bot", url="https://t.me/faltu031_bot")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                details_message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error viewing file details: {e}")
            await query.edit_message_text(
                f"❌ **Error viewing file details**\n\n`{str(e)}`\n\n💬 Visit @faltu031_bot for help!",
                parse_mode='Markdown'
            )
    
    async def _reset_project_inline(self, query):
        """Reset project inline"""
        user_id = query.from_user.id
        self.user_projects[user_id] = ScrapingProject(user_id=user_id)
        
        await query.edit_message_text("🔄 Project reset! Send me URLs to start a new scraping project.")
    
    def _generate_final_project_summary(self, project: ScrapingProject, user_message: str) -> Dict:
        """Generate comprehensive project summary with schema details"""
        
        # Create detailed project summary
        summary_prompt = f"""Based on our conversation, create a comprehensive project summary with detailed schema for this web scraping project.

PROJECT CONTEXT:
- URLs: {project.target_urls}
- Conversation history: {project.context_history[-6:]}  # Last 6 messages
- Page analyses: {project.data_requirements.get('page_analyses', {})}

Create a JSON response with:
{{
    "stage": "project_summary_and_schema",
    "response_message": "Complete project summary with schema - be detailed and clear",
    "project_summary": {{
        "project_name": "inferred project name",
        "objective": "what they're trying to achieve",
        "target_websites": ["list of domains"],
        "use_case": "how they'll use the data",
        "frequency": "how often they need data"
    }},
    "data_schema": {{
        "primary_data": [
            {{"field_name": "exact field name", "data_type": "string|number|date|boolean", "description": "what this field contains", "source": "where on page this comes from"}}
        ],
        "secondary_data": [
            {{"field_name": "field name", "data_type": "type", "description": "description", "optional": true}}
        ],
        "output_structure": "detailed explanation of how data will be structured"
    }},
    "technical_requirements": {{
        "scraping_method": "method to use",  
        "complexity_level": "low|medium|high",
        "special_considerations": ["any special handling needed"],
        "estimated_setup_time": "time estimate"
    }},
    "next_steps": ["what happens next"],
    "final_question": "Is there anything else you'd like to clarify or modify about this scraping project?"
}}

Be thorough and specific - this is their final project specification."""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": summary_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content.strip())
            
        except Exception as e:
            logger.error(f"Error generating project summary: {e}")
            return self._create_fallback_summary(project)
    
    def _create_fallback_summary(self, project: ScrapingProject) -> Dict:
        """Create fallback summary when GPT-4o fails"""
        
        # Extract basic info from project
        domains = list(set([url.split("//")[1].split("/")[0] for url in project.target_urls]))
        
        # Basic schema from page analyses
        all_fields = []
        page_analyses = project.data_requirements.get("page_analyses", {})
        for analysis in page_analyses.values():
            if "extractable_data" in analysis:
                all_fields.extend(analysis["extractable_data"].get("primary_fields", []))
        
        unique_fields = list(set(all_fields))[:10]  # Top 10 unique fields
        
        schema_fields = []
        for field in unique_fields:
            schema_fields.append({
                "field_name": field,
                "data_type": "string",
                "description": f"Data from {field} field",
                "source": "webpage content"
            })
        
        return {
            "stage": "project_summary_and_schema",
            "response_message": self._format_project_summary_message(project, domains, schema_fields),
            "project_summary": {
                "project_name": "Web Scraping Project",
                "objective": "Data extraction from target websites",
                "target_websites": domains,
                "use_case": "Data analysis and monitoring",
                "frequency": "As needed"
            },
            "data_schema": {
                "primary_data": schema_fields,
                "secondary_data": [],
                "output_structure": "JSON format with structured data fields"
            },
            "technical_requirements": {
                "scraping_method": "HTTP requests with parsing",
                "complexity_level": "medium",
                "special_considerations": ["Rate limiting", "Data validation"],
                "estimated_setup_time": "2-4 hours"
            },
            "next_steps": ["Generate scraper code", "Test and validate", "Deploy solution"],
            "final_question": "Is there anything else you'd like to clarify or modify about this scraping project?"
        }
    
    def _format_project_summary_message(self, project: ScrapingProject, domains: List[str], schema_fields: List[Dict]) -> str:
        """Format the final project summary message"""
        
        message = f"""🎯 **PROJECT SUMMARY & SCHEMA**

📋 **Your Scraping Project:**
• **Target Sites:** {', '.join(domains)}
• **Total URLs:** {len(project.target_urls)}
• **Project Goal:** Extract structured data for analysis

📊 **Data Schema (What You'll Get):**
```
{{"""
        
        for i, field in enumerate(schema_fields):
            message += f"""
  "{field['field_name']}": "{field['data_type']}", // {field['description']}"""
            if i >= 4:  # Limit to 5 fields in preview
                remaining = len(schema_fields) - 5
                if remaining > 0:
                    message += f"""
  // ... and {remaining} more fields"""
                break
        
        message += """
}
```

⚙️ **Technical Details:**
• **Method:** Web scraping with structured extraction
• **Output:** JSON format with clean, structured data
• **Frequency:** Configurable (one-time, daily, weekly, etc.)
• **Complexity:** Medium - handles dynamic content

🚀 **Next Steps:**
1. Generate custom scraper code
2. Test with your target URLs  
3. Provide ready-to-use solution
4. Include documentation and usage examples

❓ **Is there anything else you'd like to clarify or modify about this scraping project?**

Feel free to ask about:
• Specific data fields you need
• Output format preferences  
• Scheduling requirements
• Any special handling needed"""
        
        return message
    
    def run(self):
        """Start the web scraper meta agent"""
        if not self.telegram_token:
            print("❌ Please set WEB_SCRAPER_TOKEN in your environment variables")
            return
        
        if not os.getenv('OPENAI_API_KEY'):
            print("❌ Please set OPENAI_API_KEY in your environment variables")
            return
        
        if not os.getenv('FIRECRAWL_API_KEY'):
            print("⚠️  FIRECRAWL_API_KEY not set - URL analysis will be limited")
            print("   Get your API key from https://firecrawl.dev")
        
        # Create application
        app = Application.builder().token(self.telegram_token).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("status", self.status_command))
        app.add_handler(CommandHandler("reset", self.reset_command))
        app.add_handler(CommandHandler("testgoose", self.test_goose_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        print("🕷️ Web Scraper Meta Agent starting...")
        print("🤖 Using GPT-4o for requirements analysis")
        print("🔗 Ready to collect links and analyze scraping needs")
        
        # Start the bot
        app.run_polling()

if __name__ == "__main__":
    agent = WebScraperMetaAgent()
    agent.run() 