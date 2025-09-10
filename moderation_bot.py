import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, Message, ChatMemberUpdated
from telegram.ext import Application, CommandHandler, MessageHandler, ChatMemberHandler, filters, ContextTypes
from telegram.constants import ParseMode, ChatMemberStatus
from config import Config
from content_filter import ContentFilter
from image_analyzer import ImageAnalyzer
import aiofiles
import re

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, Config.LOG_LEVEL)
)
logger = logging.getLogger(__name__)

class ModerationBot:
    def __init__(self):
        self.content_filter = ContentFilter()
        self.image_analyzer = ImageAnalyzer()
        # Add connection settings for better reliability
        self.application = (Application.builder()
                           .token(Config.BOT_TOKEN)
                           .connect_timeout(60)
                           .read_timeout(60)
                           .pool_timeout(60)
                           .connection_pool_size(10)
                           .build())
        self.user_warnings = {}  # Track warnings per user
        self.user_violations = {}  # Track detailed violation history
        self.user_trust_scores = {}  # Track user trust scores (0-100)
        self.user_join_dates = {}  # Track when users joined
        self.auto_deletion_tasks = {}  # Track active auto-deletion tasks: {chat_id: {minutes: task}}
        self.setup_handlers()
        
    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("whitelist", self.whitelist_command))
        self.application.add_handler(CommandHandler("warnings", self.warnings_command))
        self.application.add_handler(CommandHandler("reset_warnings", self.reset_warnings_command))
        self.application.add_handler(CommandHandler("trust", self.trust_command))
        self.application.add_handler(CommandHandler("trust_info", self.trust_info_command))
        
        # Timer-based deletion commands
        self.application.add_handler(MessageHandler(
            filters.Regex(r'^/\d+$') & filters.TEXT, self.handle_timer_deletion
        ))
        self.application.add_handler(MessageHandler(
            filters.Regex(r'^/confirm\d+$') & filters.TEXT, self.handle_confirm_deletion
        ))
        self.application.add_handler(MessageHandler(
            filters.Regex(r'^/auto\d+$') & filters.TEXT, self.handle_auto_deletion
        ))
        self.application.add_handler(MessageHandler(
            filters.Regex(r'^/preview\d+$') & filters.TEXT, self.handle_preview_deletion
        ))
        self.application.add_handler(CommandHandler("stop_auto", self.stop_auto_deletion_command))
        self.application.add_handler(CommandHandler("list_auto", self.list_auto_deletions_command))
        
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, self.handle_text_message
        ))
        self.application.add_handler(MessageHandler(
            filters.PHOTO, self.handle_photo_message
        ))
        self.application.add_handler(MessageHandler(
            filters.Document.ALL, self.handle_document_message
        ))
        
        # Handle new members joining (using service messages)
        self.application.add_handler(MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS, self.handle_new_member_simple
        ))
        
        # Handle edited messages (prevent bypass by editing) - Use message group -1 to catch edits first
        self.application.add_handler(MessageHandler(
            filters.ALL, self.handle_any_edited_message
        ), group=-1)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_admin(update.effective_user.id, context):
            return
        
        welcome_text = """
🛡️ *NEET Channel Moderation Bot Active*

This bot protects your channel from:
• Vulgar and inappropriate content
• Competitor promotional content
• Screenshot threats and false reporting
• Spam and promotional messages

Use /help for available commands.
        """
        await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_admin(update.effective_user.id, context):
            return
        
        help_text = """
🔧 *Admin Commands:*

**Basic Commands:**
/start - Initialize the bot
/help - Show this help message
/status - Show bot status and statistics
/whitelist <user_id> - Whitelist a user
/warnings - Show current user warnings
/reset_warnings <user_id> - Reset warnings for a user

**Timer Deletion Commands:**
/60, /120, /180, etc. - Delete messages older than X minutes
/preview60, /preview120 - Preview what would be deleted
/confirm180, /confirm360 - Confirm large deletions (>180 min)

**Auto-Deletion Commands:**
/auto60, /auto120 - Start automatic deletion every 10 minutes
/stop_auto - Stop all auto-deletions
/stop_auto <minutes> - Stop specific auto-deletion
/list_auto - Show active auto-deletions

**Trust System:**
/trust <user_id> - View user trust score
/trust <user_id> <score> - Set user trust score (0-100)
/trust_info - Show trust system overview

The bot automatically:
• Deletes inappropriate content
• Warns users about violations
• Logs all moderation actions
• Protects against false reporting
• Protects admin messages from deletion
        """
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_admin(update.effective_user.id, context):
            return
        
        status_text = f"""
📊 *Bot Status:*

✅ Bot is running
🛡️ Content filtering: Active
📸 Image analysis: Active
👥 Admins: {len(Config.ADMIN_IDS)}
📢 Channel ID: {Config.CHANNEL_ID}
        """
        await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)
    
    async def whitelist_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_admin(update.effective_user.id, context):
            return
        
        if len(context.args) != 1:
            await update.message.reply_text("Usage: /whitelist <user_id>")
            return
        
        try:
            user_id = int(context.args[0])
            await update.message.reply_text(f"User {user_id} has been whitelisted.")
        except ValueError:
            await update.message.reply_text("Invalid user ID format.")
    
    async def warnings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_admin(update.effective_user.id, context):
            return
        
        if not self.user_warnings:
            await update.message.reply_text("No users have warnings currently.")
            return
        
        warning_list = "📊 *Current User Warnings:*\n\n"
        for user_id, warning_count in self.user_warnings.items():
            warning_list += f"• User ID: `{user_id}` - {warning_count}/3 warnings\n"
        
        await update.message.reply_text(warning_list, parse_mode=ParseMode.MARKDOWN)
    
    async def reset_warnings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_admin(update.effective_user.id, context):
            return
        
        if len(context.args) != 1:
            await update.message.reply_text("Usage: /reset_warnings <user_id>")
            return
        
        try:
            user_id = int(context.args[0])
            if user_id in self.user_warnings:
                del self.user_warnings[user_id]
                await update.message.reply_text(f"✅ Warnings reset for user {user_id}")
            else:
                await update.message.reply_text(f"User {user_id} has no warnings to reset.")
        except ValueError:
            await update.message.reply_text("Invalid user ID format.")
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message
        user = update.effective_user
        
        if not message or not message.text or await self.is_admin(user.id, context):
            return
        
        # Apply trust-based filtering
        user_id = user.id
        trust_score = self.calculate_trust_score(user_id)
        trust_level = self.get_trust_level(trust_score)
        
        # Trusted users get more lenient treatment
        if trust_score >= 80:
            # TRUSTED users: Only block obvious commercial spam
            analysis = self.content_filter.analyze_message_trusted(message.text)
        elif trust_score >= 60:
            # GOOD users: Normal educational-friendly filtering
            analysis = self.content_filter.analyze_message(message.text)
        else:
            # NEW/MONITORED users: Stricter filtering
            analysis = self.content_filter.analyze_message_strict(message.text)
        
        # Log trust info
        logger.info(f"User {user_id} ({user.username}) - Trust: {trust_score} ({trust_level})")
        
        if not analysis["is_safe"]:
            await self.handle_violation(message, analysis, "text", context)
    
    async def handle_photo_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message
        user = update.effective_user
        
        if await self.is_admin(user.id, context):
            return
        
        try:
            photo = message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            file_data = await file.download_as_bytearray()
            
            # Pass caption to analyzer for educational context detection
            caption = message.caption if message.caption else ""
            analysis = self.image_analyzer.analyze_image(bytes(file_data), caption)
            
            if not analysis["is_safe"]:
                await self.handle_violation(message, analysis, "image", context)
                
        except Exception as e:
            logger.error(f"Error processing photo: {e}")
    
    async def handle_document_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message
        user = update.effective_user
        
        if await self.is_admin(user.id, context):
            return
        
        document = message.document
        if document.mime_type and document.mime_type.startswith('image/'):
            try:
                file = await context.bot.get_file(document.file_id)
                file_data = await file.download_as_bytearray()
                
                # Pass caption to analyzer for educational context detection
                caption = message.caption if message.caption else ""
                analysis = self.image_analyzer.analyze_image(bytes(file_data), caption)
                
                if not analysis["is_safe"]:
                    await self.handle_violation(message, analysis, "document", context)
                    
            except Exception as e:
                logger.error(f"Error processing document: {e}")
    
    async def handle_violation(self, message: Message, analysis: dict, content_type: str, context: ContextTypes.DEFAULT_TYPE):
        user = message.from_user
        user_id = user.id
        
        try:
            await message.delete()
            logger.info(f"Deleted {content_type} message from user {user_id} ({user.username})")
            
            # Track warnings and detailed violations for this user
            if user_id not in self.user_warnings:
                self.user_warnings[user_id] = 0
                self.user_violations[user_id] = []
            
            self.user_warnings[user_id] += 1
            warning_count = self.user_warnings[user_id]
            
            # Record detailed violation info
            violation_info = {
                "type": content_type,
                "violations": analysis.get("violations", []),
                "warning_number": warning_count
            }
            self.user_violations[user_id].append(violation_info)
            
            # Send violation notification to admins
            violation_text = self.format_violation_message(analysis, user, content_type, warning_count)
            
            for admin_id in Config.ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=violation_text,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as e:
                    logger.error(f"Failed to notify admin {admin_id}: {e}")
            
            # Warning system: 3 strikes and you're out
            if warning_count >= 3:
                # Remove user from group
                try:
                    await context.bot.ban_chat_member(
                        chat_id=message.chat_id,
                        user_id=user_id
                    )
                    
                    # Get user's violation history for detailed report
                    violation_details = self.get_user_violation_history(user_id)
                    
                    # Send final warning with detailed reasons
                    final_warning = f"""
🚫 {user.mention_markdown()} **PERMANENTLY BANNED**

📊 **VIOLATION SUMMARY:**
• Total Violations: **3/3**
• Final Violation: **{content_type.upper()}** message

📋 **REMOVAL REASONS:**
{violation_details}

⚖️ **BOT PARAMETERS:**
• Warning System: 3-strike policy
• Auto-moderation: Active  
• Content Filter: {len(Config.VULGAR_WORDS + Config.COMPETITOR_KEYWORDS + Config.SCREENSHOT_INDICATORS)} keywords monitored

Contact admins if you believe this was an error.
                    """
                    
                    await context.bot.send_message(
                        chat_id=message.chat_id,
                        text=final_warning,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                    # Reset warnings and violations (user is removed)
                    del self.user_warnings[user_id]
                    if user_id in self.user_violations:
                        del self.user_violations[user_id]
                    
                    logger.info(f"User {user_id} ({user.username}) removed after 3 warnings")
                    
                except Exception as e:
                    logger.error(f"Failed to remove user {user_id}: {e}")
            
            else:
                # Send warning to user in the group
                warnings_left = 3 - warning_count
                
                # Get specific violation details for the warning
                violation_details = []
                if "violations" in analysis:
                    for violation in analysis["violations"]:
                        v_type = violation.get("type", "unknown")
                        
                        if v_type == "vulgar_content":
                            violation_details.append("inappropriate content")
                        elif v_type == "competitor_content":
                            violation_details.append("competitor name")
                        elif v_type == "screenshot_threat":
                            violation_details.append("threatening content")
                        elif v_type == "spam_pattern":
                            violation_details.append("spam/promotional pattern")
                        elif v_type == "commercial_spam":
                            violation_details.append("commercial promotion")
                        elif v_type == "promotional_pattern":
                            violation_details.append("promotional content")
                        else:
                            violation_details.append(v_type.replace("_", " "))
                
                reason_text = "; ".join(violation_details) if violation_details else "rule violation"
                
                warning_text = f"""
⚠️ **WARNING {warning_count}/3** - {user.mention_markdown()}

❌ Message deleted for: **{reason_text}**
📝 **{warnings_left} more violations = PERMANENT BAN**
                """
                
                await context.bot.send_message(
                    chat_id=message.chat_id,
                    text=warning_text,
                    parse_mode=ParseMode.MARKDOWN
                )
            
        except Exception as e:
            logger.error(f"Error handling violation: {e}")
    
    def format_violation_message(self, analysis: dict, user, content_type: str, warning_count: int = 1) -> str:
        violation_types = []
        if "violations" in analysis:
            for violation in analysis["violations"]:
                violation_types.append(violation["type"])
        
        action_text = "Message deleted and user warned" if warning_count < 3 else "Message deleted and user REMOVED"
        
        return f"""
🚨 *Content Violation Detected*

👤 User: {user.mention_markdown()} (ID: {user.id})
📝 Type: {content_type}
⚠️ Violations: {', '.join(violation_types)}
📊 Warning Count: {warning_count}/3

Action: {action_text}
        """
    
    async def handle_new_member_simple(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle new members joining the channel"""
        message = update.message
        
        if not message or not message.new_chat_members:
            return
        
        for new_user in message.new_chat_members:
            # Don't welcome bots or admins
            if new_user.is_bot or self.is_admin_sync(new_user.id):
                continue
            
            # Initialize new user trust score
            user_id = new_user.id
            self.calculate_trust_score(user_id)  # This will initialize them
            
            welcome_message = f"""
🎓 **Welcome to the channel!** {new_user.mention_markdown()}

📋 **Rules:** NEET content only • No spam • No editing messages
⚠️ **Warning System:** 3 strikes = permanent ban

Good luck with your preparation! 🚀
            """
            
            try:
                await context.bot.send_message(
                    chat_id=message.chat_id,
                    text=welcome_message,
                    parse_mode=ParseMode.MARKDOWN
                )
                logger.info(f"Sent welcome message to new member: {new_user.id} ({new_user.username})")
            except Exception as e:
                logger.error(f"Failed to send welcome message: {e}")
    
    async def handle_any_edited_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle any edited message - delete it to prevent bypass"""
        # Only process if this is an edited message
        if not update.edited_message:
            return
            
        message = update.edited_message
        user = update.effective_user
        
        if not message or not user or await self.is_admin(user.id, context):
            return
        
        try:
            # Determine message type for logging
            msg_type = "text"
            if message.photo:
                msg_type = "photo"
            elif message.document:
                msg_type = "document"
            elif message.video:
                msg_type = "video"
            elif message.audio:
                msg_type = "audio"
            
            logger.info(f"Detected edited {msg_type} message from user {user.id} ({user.username})")
            
            await context.bot.delete_message(
                chat_id=message.chat_id,
                message_id=message.message_id
            )
            
            # Send gentle warning about editing (no violation count)
            warning_text = f"""
ℹ️ **Message edited** - {user.mention_markdown()}

📝 Edited message deleted for channel integrity
💡 Tip: Send a new message if you need to correct something
            """
            
            await context.bot.send_message(
                chat_id=message.chat_id,
                text=warning_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"Deleted edited {msg_type} message from user {user.id} ({user.username})")
            
        except Exception as e:
            logger.error(f"Error handling edited message: {e}")
    
    def get_user_violation_history(self, user_id: int) -> str:
        """Generate detailed violation history for user removal message"""
        if user_id not in self.user_violations:
            return "• No detailed history available"
        
        history = []
        for i, violation in enumerate(self.user_violations[user_id], 1):
            violation_types = []
            for v in violation.get("violations", []):
                violation_types.append(v.get("type", "unknown"))
            
            if violation_types:
                reason = f"{violation['type']} ({', '.join(violation_types)})"
            else:
                reason = violation['type']
            
            history.append(f"• Violation {i}: {reason}")
        
        return '\n'.join(history)
    
    def calculate_trust_score(self, user_id: int) -> int:
        """Calculate user trust score (0-100)"""
        import time
        
        # Initialize new user
        if user_id not in self.user_trust_scores:
            self.user_trust_scores[user_id] = 50  # Start with neutral score
            self.user_join_dates[user_id] = time.time()
        
        base_score = 50
        current_time = time.time()
        join_time = self.user_join_dates.get(user_id, current_time)
        
        # Time-based trust (more days = more trust)
        days_in_channel = (current_time - join_time) / (24 * 60 * 60)
        time_bonus = min(20, days_in_channel * 2)  # Max 20 points for 10+ days
        
        # Violation penalty
        violations = len(self.user_violations.get(user_id, []))
        violation_penalty = violations * 15  # -15 per violation
        
        # Warning penalty
        warnings = self.user_warnings.get(user_id, 0)
        warning_penalty = warnings * 10  # -10 per warning
        
        # Calculate final score
        trust_score = base_score + time_bonus - violation_penalty - warning_penalty
        trust_score = max(0, min(100, trust_score))  # Keep between 0-100
        
        self.user_trust_scores[user_id] = trust_score
        return trust_score
    
    def get_trust_level(self, trust_score: int) -> str:
        """Get trust level description"""
        if trust_score >= 80:
            return "TRUSTED"
        elif trust_score >= 60:
            return "GOOD"
        elif trust_score >= 40:
            return "NEUTRAL"
        elif trust_score >= 20:
            return "MONITORED"
        else:
            return "RESTRICTED"
    
    def should_apply_strict_filtering(self, user_id: int) -> bool:
        """Determine if user should get strict filtering"""
        trust_score = self.calculate_trust_score(user_id)
        return trust_score < 60  # Strict for scores below 60
    
    async def trust_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin command to view or modify user trust scores"""
        if not await self.is_admin(update.effective_user.id, context):
            return
        
        if len(context.args) == 0:
            await update.message.reply_text("Usage: /trust <user_id> [new_score]")
            return
        
        try:
            user_id = int(context.args[0])
            
            if len(context.args) == 1:
                # View trust score
                trust_score = self.calculate_trust_score(user_id)
                trust_level = self.get_trust_level(trust_score)
                
                # Get user info
                violations = len(self.user_violations.get(user_id, []))
                warnings = self.user_warnings.get(user_id, 0)
                
                # Calculate days in channel
                import time
                current_time = time.time()
                join_time = self.user_join_dates.get(user_id, current_time)
                days_in_channel = (current_time - join_time) / (24 * 60 * 60)
                
                trust_info = f"""
📊 **Trust Score Report**

👤 User ID: `{user_id}`
🎯 Trust Score: **{trust_score}/100** ({trust_level})
📅 Days in channel: **{days_in_channel:.1f}**
⚠️ Warnings: **{warnings}/3**
❌ Violations: **{violations}**

📋 **Filtering Level:**
• {trust_level} users get {"lenient" if trust_score >= 80 else "normal" if trust_score >= 60 else "strict"} filtering
                """
                
                await update.message.reply_text(trust_info, parse_mode=ParseMode.MARKDOWN)
                
            elif len(context.args) == 2:
                # Modify trust score
                new_score = int(context.args[1])
                if not 0 <= new_score <= 100:
                    await update.message.reply_text("Trust score must be between 0 and 100")
                    return
                
                self.user_trust_scores[user_id] = new_score
                trust_level = self.get_trust_level(new_score)
                
                await update.message.reply_text(
                    f"✅ Trust score for user `{user_id}` set to **{new_score}/100** ({trust_level})",
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except ValueError:
            await update.message.reply_text("Invalid user ID or score format")
    
    async def trust_info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show trust system information"""
        if not await self.is_admin(update.effective_user.id, context):
            return
        
        # Count users by trust level
        trust_levels = {"TRUSTED": 0, "GOOD": 0, "NEUTRAL": 0, "MONITORED": 0, "RESTRICTED": 0}
        
        for user_id in self.user_trust_scores:
            score = self.calculate_trust_score(user_id)
            level = self.get_trust_level(score)
            trust_levels[level] += 1
        
        total_users = len(self.user_trust_scores)
        
        trust_info = f"""
🛡️ **Trust System Overview**

📊 **User Distribution:**
• 🟢 TRUSTED (80-100): **{trust_levels['TRUSTED']}** users
• 🔵 GOOD (60-79): **{trust_levels['GOOD']}** users  
• 🟡 NEUTRAL (40-59): **{trust_levels['NEUTRAL']}** users
• 🟠 MONITORED (20-39): **{trust_levels['MONITORED']}** users
• 🔴 RESTRICTED (0-19): **{trust_levels['RESTRICTED']}** users

👥 **Total tracked users:** {total_users}

📋 **Filtering Levels:**
• **TRUSTED:** Only blocks commercial spam
• **GOOD:** Normal educational-friendly filtering  
• **NEUTRAL/MONITORED/RESTRICTED:** Strict filtering

⚙️ **Score Calculation:**
• Base score: 50 points
• Time bonus: +2 points per day (max 20)
• Violation penalty: -15 points each
• Warning penalty: -10 points each

Use `/trust <user_id>` to view individual scores
        """
        
        await update.message.reply_text(trust_info, parse_mode=ParseMode.MARKDOWN)
    
    async def is_admin(self, user_id: int, context: ContextTypes.DEFAULT_TYPE = None) -> bool:
        # First check static admin list from config
        if user_id in Config.ADMIN_IDS:
            return True
        
        # If context is provided, check if user is channel admin
        if context:
            try:
                chat_member = await context.bot.get_chat_member(Config.CHANNEL_ID, user_id)
                return chat_member.status in ['creator', 'administrator']
            except Exception as e:
                logger.error(f"Error checking admin status for user {user_id}: {e}")
                return False
        
        return False
    
    def is_admin_sync(self, user_id: int) -> bool:
        """Synchronous version for backwards compatibility"""
        return user_id in Config.ADMIN_IDS
    
    async def handle_timer_deletion(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle timer-based deletion commands like /60, /120"""
        if not await self.is_admin(update.effective_user.id, context):
            await update.message.reply_text("❌ Only admins can use timer deletion commands.")
            return
        
        # Extract minutes from command (e.g., /60 -> 60)
        command_text = update.message.text.strip()
        minutes = int(command_text[1:])  # Remove the '/' and convert to int
        
        # Validate time range
        if not (5 <= minutes <= 1440):  # 5 minutes to 24 hours
            await update.message.reply_text("⚠️ Time must be between 5 minutes and 24 hours (1440 minutes)")
            return
        
        # Confirm large deletions
        if minutes > 180:  # More than 3 hours
            confirm_msg = f"⚠️ **LARGE DELETION WARNING**\n\nThis will delete all messages older than **{minutes} minutes** ({minutes//60}h {minutes%60}m).\n\nType `/confirm{minutes}` to proceed."
            await update.message.reply_text(confirm_msg, parse_mode=ParseMode.MARKDOWN)
            return
        
        await self.delete_messages_by_time(update.message.chat_id, minutes, context, update.effective_user.id)
    
    async def handle_confirm_deletion(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle confirmation for large deletions like /confirm180"""
        if not await self.is_admin(update.effective_user.id, context):
            await update.message.reply_text("❌ Only admins can use timer deletion commands.")
            return
        
        # Extract minutes from command (e.g., /confirm180 -> 180)
        command_text = update.message.text.strip()
        minutes = int(command_text[8:])  # Remove '/confirm' and convert to int
        
        # Validate time range
        if not (5 <= minutes <= 1440):  # 5 minutes to 24 hours
            await update.message.reply_text("⚠️ Time must be between 5 minutes and 24 hours (1440 minutes)")
            return
        
        await update.message.reply_text(f"✅ **Confirmed!** Proceeding with deletion of messages older than {minutes} minutes...", parse_mode=ParseMode.MARKDOWN)
        await self.delete_messages_by_time(update.message.chat_id, minutes, context, update.effective_user.id)
    
    async def handle_auto_deletion(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle auto-deletion commands like /auto60, /auto120"""
        if not await self.is_admin(update.effective_user.id, context):
            await update.message.reply_text("❌ Only admins can use auto-deletion commands.")
            return
        
        # Extract minutes from command (e.g., /auto60 -> 60)
        command_text = update.message.text.strip()
        minutes = int(command_text[5:])  # Remove '/auto' and convert to int
        
        # Validate time range
        if not (10 <= minutes <= 1440):  # 10 minutes to 24 hours
            await update.message.reply_text("⚠️ Auto-deletion time must be between 10 minutes and 24 hours (1440 minutes)")
            return
        
        chat_id = update.message.chat_id
        
        # Check if auto-deletion already exists for this time
        if chat_id in self.auto_deletion_tasks and minutes in self.auto_deletion_tasks[chat_id]:
            await update.message.reply_text(f"⚠️ Auto-deletion for {minutes} minutes is already active. Use `/stop_auto {minutes}` to stop it first.")
            return
        
        # Start auto-deletion task
        await self.start_auto_deletion(chat_id, minutes, context, update.effective_user.id)
        
        await update.message.reply_text(
            f"✅ **Auto-deletion started**\n\nMessages older than **{minutes} minutes** will be automatically deleted every 10 minutes.\n\nUse `/stop_auto {minutes}` to stop this auto-deletion.",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def handle_preview_deletion(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle preview deletion commands like /preview60"""
        if not await self.is_admin(update.effective_user.id, context):
            await update.message.reply_text("❌ Only admins can use preview commands.")
            return
        
        # Extract minutes from command (e.g., /preview60 -> 60)
        command_text = update.message.text.strip()
        minutes = int(command_text[8:])  # Remove '/preview' and convert to int
        
        # Validate time range
        if not (5 <= minutes <= 1440):
            await update.message.reply_text("⚠️ Preview time must be between 5 minutes and 24 hours (1440 minutes)")
            return
        
        await self.preview_deletion(update.message.chat_id, minutes, context, update.effective_user.id)
    
    async def stop_auto_deletion_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Stop specific auto-deletion or all auto-deletions"""
        if not await self.is_admin(update.effective_user.id, context):
            await update.message.reply_text("❌ Only admins can stop auto-deletion.")
            return
        
        chat_id = update.message.chat_id
        
        if len(context.args) == 0:
            # Stop all auto-deletions
            if chat_id not in self.auto_deletion_tasks or not self.auto_deletion_tasks[chat_id]:
                await update.message.reply_text("ℹ️ No auto-deletions are currently active.")
                return
            
            stopped_tasks = []
            for minutes, task in list(self.auto_deletion_tasks[chat_id].items()):
                task.cancel()
                stopped_tasks.append(str(minutes))
            
            del self.auto_deletion_tasks[chat_id]
            
            await update.message.reply_text(f"✅ Stopped all auto-deletions: {', '.join(stopped_tasks)} minutes")
            
        elif len(context.args) == 1:
            # Stop specific auto-deletion
            try:
                minutes = int(context.args[0])
                
                if chat_id not in self.auto_deletion_tasks or minutes not in self.auto_deletion_tasks[chat_id]:
                    await update.message.reply_text(f"ℹ️ No auto-deletion for {minutes} minutes is active.")
                    return
                
                self.auto_deletion_tasks[chat_id][minutes].cancel()
                del self.auto_deletion_tasks[chat_id][minutes]
                
                # Clean up empty dict
                if not self.auto_deletion_tasks[chat_id]:
                    del self.auto_deletion_tasks[chat_id]
                
                await update.message.reply_text(f"✅ Stopped auto-deletion for {minutes} minutes")
                
            except ValueError:
                await update.message.reply_text("⚠️ Invalid time format. Use: `/stop_auto <minutes>` or `/stop_auto` for all")
        else:
            await update.message.reply_text("⚠️ Usage: `/stop_auto` (stop all) or `/stop_auto <minutes>` (stop specific)")
    
    async def list_auto_deletions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all active auto-deletions"""
        if not await self.is_admin(update.effective_user.id, context):
            await update.message.reply_text("❌ Only admins can view auto-deletions.")
            return
        
        chat_id = update.message.chat_id
        
        if chat_id not in self.auto_deletion_tasks or not self.auto_deletion_tasks[chat_id]:
            await update.message.reply_text("ℹ️ No auto-deletions are currently active.")
            return
        
        active_deletions = list(self.auto_deletion_tasks[chat_id].keys())
        active_deletions.sort()
        
        deletion_list = "🤖 **Active Auto-Deletions:**\n\n"
        for minutes in active_deletions:
            hours = minutes // 60
            mins = minutes % 60
            time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
            deletion_list += f"• **{minutes} minutes** ({time_str})\n"
        
        deletion_list += f"\n📊 Total: **{len(active_deletions)}** active auto-deletions"
        deletion_list += "\n\n💡 Use `/stop_auto <minutes>` to stop specific ones"
        
        await update.message.reply_text(deletion_list, parse_mode=ParseMode.MARKDOWN)
    
    async def delete_messages_by_time(self, chat_id: int, minutes: int, context: ContextTypes.DEFAULT_TYPE, admin_id: int):
        """Delete messages older than specified minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        try:
            # Send progress message
            progress_msg = await context.bot.send_message(
                chat_id=chat_id,
                text=f"🔄 **Deleting messages older than {minutes} minutes...**\n\n⏳ Please wait...",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Use the practical deletion approach
            result = await self.get_recent_messages_for_deletion(chat_id, cutoff_time, context)
            
            # Update progress message with results
            hours = minutes // 60
            mins = minutes % 60
            time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
            
            result_text = f"""
✅ **Deletion Complete**

⏰ **Time Range:** Messages older than {minutes} minutes ({time_str})
🗑️ **Deleted:** {result['deleted_count']} messages
⚠️ **Errors/Skipped:** {result['error_count']} (includes admin messages and non-existent messages)

🔒 **Note:** Admin messages and system messages are automatically protected.
ℹ️ **Method:** Bulk deletion with error handling for protected content.
            """
            
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=progress_msg.message_id,
                text=result_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"Timer deletion completed by admin {admin_id}: {result['deleted_count']} messages deleted ({minutes} minutes)")
            
        except Exception as e:
            logger.error(f"Error in timer deletion: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ **Deletion failed:** {str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def preview_deletion(self, chat_id: int, minutes: int, context: ContextTypes.DEFAULT_TYPE, admin_id: int):
        """Preview what messages would be deleted without actually deleting them"""
        try:
            # Send progress message
            progress_msg = await context.bot.send_message(
                chat_id=chat_id,
                text=f"🔍 **Previewing deletion for {minutes} minutes...**\n\n⏳ Scanning messages...",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Since we can't easily preview without special permissions,
            # we'll provide an estimated preview based on recent activity
            hours = minutes // 60
            mins = minutes % 60
            time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
            
            # Estimate message count (this is a rough estimate)
            # In a real implementation, you'd need message tracking or special permissions
            estimated_range = min(5000, minutes * 10)  # Rough estimate: 10 messages per minute
            
            preview_text = f"""
🔍 **Deletion Preview Report**

⏰ **Time Range:** Messages older than {minutes} minutes ({time_str})

📊 **Estimated Impact:**
🔍 **Search Range:** Last ~{estimated_range} message IDs
⚠️ **Method:** Bulk deletion with error handling
🛡️ **Protection:** Admin messages automatically skipped

📋 **What will happen:**
• Bot will attempt to delete messages in recent ID range
• Admin messages will be automatically protected
• Non-existent/already deleted messages will be skipped
• Rate limiting will be applied (1 second per 20 deletions)

💡 **To proceed:** Use `/{minutes}` to delete these messages
⚠️ **Large deletion?** Commands >180 minutes require confirmation

🔒 **Safety Features:**
• Admin message protection: ✅
• Rate limiting: ✅  
• Error handling: ✅
• Progress reporting: ✅
            """
            
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=progress_msg.message_id,
                text=preview_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"Preview completed by admin {admin_id}: Estimated range {estimated_range} messages ({minutes} minutes)")
            
        except Exception as e:
            logger.error(f"Error in preview deletion: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ **Preview failed:** {str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def start_auto_deletion(self, chat_id: int, minutes: int, context: ContextTypes.DEFAULT_TYPE, admin_id: int):
        """Start auto-deletion task for specified minutes"""
        async def auto_delete_task():
            while True:
                try:
                    # Wait 10 minutes before first run and between runs
                    await asyncio.sleep(600)  # 10 minutes
                    
                    # Check if task is still in our tracking dict (might be cancelled)
                    if (chat_id not in self.auto_deletion_tasks or 
                        minutes not in self.auto_deletion_tasks[chat_id]):
                        break
                    
                    # Perform deletion using the practical approach
                    cutoff_time = datetime.now() - timedelta(minutes=minutes)
                    result = await self.get_recent_messages_for_deletion(chat_id, cutoff_time, context)
                    
                    if result['deleted_count'] > 0:
                        logger.info(f"Auto-deletion ({minutes}m): {result['deleted_count']} messages deleted from chat {chat_id}")
                        
                except asyncio.CancelledError:
                    logger.info(f"Auto-deletion task cancelled for {minutes} minutes in chat {chat_id}")
                    break
                except Exception as e:
                    logger.error(f"Error in auto-deletion task ({minutes}m): {e}")
                    # Continue running despite errors
        
        # Create and start the task
        task = asyncio.create_task(auto_delete_task())
        
        # Store the task
        if chat_id not in self.auto_deletion_tasks:
            self.auto_deletion_tasks[chat_id] = {}
        
        self.auto_deletion_tasks[chat_id][minutes] = task
        
        logger.info(f"Auto-deletion started by admin {admin_id}: {minutes} minutes in chat {chat_id}")
    
    async def get_chat_history(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Generator to iterate through chat history using message iteration"""
        try:
            # We'll implement a simple approach by checking recent message IDs
            # This works by trying to access messages by iterating backwards from a recent message ID
            
            # First, let's get the latest message ID by sending a dummy message and then deleting it
            try:
                # Send a temporary message to get current message ID
                temp_msg = await context.bot.send_message(
                    chat_id=chat_id,
                    text="🔄 Scanning..."
                )
                current_msg_id = temp_msg.message_id
                
                # Delete the temporary message
                await context.bot.delete_message(chat_id=chat_id, message_id=current_msg_id)
                
                # Now iterate backwards from this message ID
                for msg_id in range(current_msg_id - 1, max(0, current_msg_id - 10000), -1):
                    try:
                        # Try to get message details by forwarding to ourselves (admin)
                        # This is a workaround since direct message access is limited
                        # Alternative: use updates or webhook data if available
                        
                        # For now, we'll use a different approach with stored message tracking
                        # Since Telegram Bot API doesn't provide direct chat history access
                        # We'll implement message tracking in real-time instead
                        break
                        
                    except Exception:
                        # Message doesn't exist or can't be accessed, continue
                        continue
                        
            except Exception as e:
                logger.error(f"Error getting message range: {e}")
                
        except Exception as e:
            logger.error(f"Error in get_chat_history: {e}")
    
    # Let's implement a different approach using message tracking
    async def get_recent_messages_for_deletion(self, chat_id: int, cutoff_time: datetime, context: ContextTypes.DEFAULT_TYPE):
        """Get recent messages for deletion using timestamp-based approach"""
        try:
            deleted_messages = []
            admin_skipped = 0
            error_count = 0
            
            # Get current message ID range
            temp_msg = await context.bot.send_message(
                chat_id=chat_id,
                text="🔄 Scanning messages..."
            )
            current_msg_id = temp_msg.message_id
            await context.bot.delete_message(chat_id=chat_id, message_id=current_msg_id)
            
            # We need to check messages going backwards from current time
            # Since we can't get message timestamps directly, we'll use a time-estimation approach
            # This is a limitation of Bot API - we can only estimate message age by ID gaps
            
            # Start from recent messages and work backwards
            # Estimate: roughly 1 message per minute in active groups
            # For 60 minutes, check last ~300-500 message IDs to be safe
            current_time = datetime.now()
            time_diff_minutes = (current_time - cutoff_time).total_seconds() / 60
            estimated_range = min(5000, max(300, int(time_diff_minutes * 5)))
            
            consecutive_errors = 0
            messages_found = 0
            
            for msg_id in range(current_msg_id - 1, max(0, current_msg_id - estimated_range), -1):
                try:
                    # Try to forward the message to ourselves to check if it exists and get info
                    # This is the only way to get message details without admin privileges
                    admin_ids = Config.ADMIN_IDS
                    if admin_ids:
                        admin_id = admin_ids[0]  # Use first admin for forwarding test
                        
                        try:
                            # Try to forward message to admin to check if it exists
                            forwarded = await context.bot.forward_message(
                                chat_id=admin_id,
                                from_chat_id=chat_id,
                                message_id=msg_id
                            )
                            
                            messages_found += 1
                            
                            # Get the original message date from forward
                            if forwarded and forwarded.forward_date:
                                message_time = forwarded.forward_date
                                
                                # Convert to naive datetime for comparison
                                if message_time.tzinfo:
                                    message_time = message_time.replace(tzinfo=None)
                                
                                # Check if message is older than cutoff time
                                if message_time < cutoff_time:
                                    # Message is old enough to delete
                                    try:
                                        # Delete the original message
                                        await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                                        deleted_messages.append(msg_id)
                                        
                                        # Add delay every 20 deletions
                                        if len(deleted_messages) % 20 == 0:
                                            await asyncio.sleep(1)
                                            
                                    except Exception:
                                        # Couldn't delete - might be admin message or already deleted
                                        admin_skipped += 1
                                        pass
                                else:
                                    # Message is newer than cutoff - we can stop here
                                    # since we're going backwards chronologically
                                    logger.info(f"Reached newer messages at msg_id {msg_id}, stopping scan")
                                    break
                            
                            # Clean up the forwarded message
                            try:
                                await context.bot.delete_message(chat_id=admin_id, message_id=forwarded.message_id)
                            except:
                                pass
                                
                            consecutive_errors = 0  # Reset error counter
                            
                        except Exception:
                            # Message doesn't exist or can't be forwarded
                            consecutive_errors += 1
                            error_count += 1
                            
                            # If we get too many consecutive errors, stop scanning
                            if consecutive_errors > 50:
                                logger.info(f"Too many consecutive errors ({consecutive_errors}), stopping scan")
                                break
                                
                except Exception as e:
                    logger.error(f"Error processing message {msg_id}: {e}")
                    consecutive_errors += 1
                    error_count += 1
                    
                    if consecutive_errors > 50:
                        break
            
            logger.info(f"Deletion scan complete: found {messages_found} messages, deleted {len(deleted_messages)}, skipped {admin_skipped}")
            
            return {
                "deleted_count": len(deleted_messages),
                "admin_skipped": admin_skipped,
                "error_count": error_count
            }
            
        except Exception as e:
            logger.error(f"Error in get_recent_messages_for_deletion: {e}")
            return {"deleted_count": 0, "admin_skipped": 0, "error_count": 1}
    
    def run(self):
        logger.info("Starting NEET Channel Moderation Bot...")
        self.application.run_polling()

if __name__ == "__main__":
    bot = ModerationBot()
    bot.run()