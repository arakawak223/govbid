import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import User, Bid

settings = get_settings()
logger = logging.getLogger(__name__)


async def send_new_bids_notification(
    db: AsyncSession,
    new_bids: list[Bid],
) -> int:
    """Send email notifications to users about new bids

    Args:
        db: Database session
        new_bids: List of new bid objects

    Returns:
        Number of emails sent
    """
    if not new_bids:
        return 0

    if not settings.resend_api_key:
        logger.warning("Resend API key not configured, skipping notifications")
        return 0

    # Get users with notifications enabled
    result = await db.execute(
        select(User).where(User.notification_enabled == True)
    )
    users = result.scalars().all()

    if not users:
        return 0

    try:
        import resend
        resend.api_key = settings.resend_api_key
    except ImportError:
        logger.error("Resend library not installed")
        return 0

    emails_sent = 0

    # Build email content
    bid_list_html = "<ul>"
    for bid in new_bids[:10]:  # Limit to 10 bids per email
        bid_list_html += f"""
        <li>
            <strong>{bid.title}</strong><br>
            自治体: {bid.municipality}<br>
            カテゴリ: {bid.category or '未分類'}<br>
            <a href="{bid.announcement_url}">詳細を見る</a>
        </li>
        """
    bid_list_html += "</ul>"

    if len(new_bids) > 10:
        bid_list_html += f"<p>...他 {len(new_bids) - 10} 件</p>"

    for user in users:
        try:
            resend.Emails.send({
                "from": settings.email_from,
                "to": user.email,
                "subject": f"【GovBid】新着案件のお知らせ ({len(new_bids)}件)",
                "html": f"""
                <h2>新着入札案件のお知らせ</h2>
                <p>{user.name} 様</p>
                <p>新しい入札案件が {len(new_bids)} 件見つかりました。</p>
                {bid_list_html}
                <p>
                    <a href="http://localhost:3000">GovBidで全ての案件を確認</a>
                </p>
                <hr>
                <p style="color: #666; font-size: 12px;">
                    このメールは自動送信されています。
                    通知を停止するには、GovBidの設定から通知をOFFにしてください。
                </p>
                """,
            })
            emails_sent += 1
            logger.info(f"Notification sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send notification to {user.email}: {e}")

    return emails_sent
