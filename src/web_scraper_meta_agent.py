#!/usr/bin/env python3
"""
Web Scraper Meta Agent - Link Collection & Requirements Analysis
Uses GPT-4o to understand user scraping needs and collect target URLs.
"""

import os
import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from web_page_analyzer import WebPageAnalyzer

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

I'll help you build a custom web scraper by understanding exactly what you need.

Tell me about your project - what are you trying to achieve? Are you:
• Building a business tool?
• Doing research or analysis?
• Monitoring competitors?
• Collecting data for a personal project?

I'm genuinely curious about your goals and what you're working on!"""
        
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """🕷️ Web Scraper Meta Agent Help

I help you create custom web scrapers by:

🔍 **Step 1: Link Collection**
- Share URLs you want to scrape
- I'll analyze and categorize them

🎯 **Step 2: Requirements Gathering**  
- Define what data to extract
- Set frequency and format preferences
- Specify target elements

⚡ **Step 3: Scraper Generation**
- Generate custom scraping code
- Provide ready-to-use solution

**Commands:**
• /start - Begin new scraping project
• /status - Check current project status
• /reset - Start over with new project

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
            
            # Add technical requirements
            if tech_requirements:
                details_message += f"\n\n⚙️ **Technical Specifications:**"
                details_message += f"\n• **Method:** {tech_requirements.get('scraping_method', 'Standard HTTP scraping')}"
                details_message += f"\n• **Complexity:** {tech_requirements.get('complexity_level', 'Medium').title()}"
                details_message += f"\n• **Setup Time:** {tech_requirements.get('estimated_setup_time', '2-4 hours')}"
                
                considerations = tech_requirements.get('special_considerations', [])
                if considerations:
                    details_message += f"\n• **Special Handling:** {', '.join(considerations)}"
            
            # Add next steps
            next_steps = analysis.get("next_steps", [])
            if next_steps:
                details_message += f"\n\n🚀 **What Happens Next:**"
                for i, step in enumerate(next_steps, 1):
                    details_message += f"\n{i}. {step}"
            
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
    
    async def _handle_project_confirmation(self, query, project: ScrapingProject):
        """Handle project confirmation"""
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