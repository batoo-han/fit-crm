"""Utility functions for handlers."""
from aiogram.types import CallbackQuery
from loguru import logger


async def safe_callback_answer(callback: CallbackQuery, text: str = "", show_alert: bool = False):
    """
    Safely answer callback query, handling expired queries.
    
    Args:
        callback: CallbackQuery object
        text: Optional text to show
        show_alert: Whether to show alert or notification
    """
    try:
        # Check if callback query is still valid
        if callback and hasattr(callback, 'id'):
            await callback.answer(text=text, show_alert=show_alert)
    except Exception as e:
        # Handle expired or invalid callback queries
        error_msg = str(e).lower()
        if "too old" in error_msg or "timeout" in error_msg or "invalid" in error_msg:
            logger.debug(f"Callback query expired (expected): {e}")
        else:
            logger.warning(f"Could not answer callback query: {e}")
        # Don't raise - just log the warning
