from __future__ import annotations
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from loguru import logger
from database.models_crm import SocialPost
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID, VK_ACCESS_TOKEN, VK_GROUP_ID
import requests


class SocialScheduler:
    @staticmethod
    def list_posts(db: Session, status: Optional[str] = None) -> List[SocialPost]:
        query = db.query(SocialPost).order_by(SocialPost.scheduled_at.asc().nullslast())
        if status:
            query = query.filter(SocialPost.status == status)
        return query.all()

    @staticmethod
    def schedule_post(db: Session, post: SocialPost) -> SocialPost:
        post.status = "scheduled"
        post.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(post)
        return post

    @staticmethod
    def process_scheduled(db: Session, limit: int = 10) -> int:
        now = datetime.utcnow()
        posts = (
            db.query(SocialPost)
            .filter(SocialPost.status == "scheduled")
            .filter(SocialPost.scheduled_at <= now)
            .order_by(SocialPost.scheduled_at.asc())
            .limit(limit)
            .all()
        )
        processed = 0
        for post in posts:
            try:
                if SocialScheduler._send_post(post):
                    post.status = "sent"
                    post.error = None
                else:
                    post.status = "failed"
                    post.error = post.error or "Failed to send"
                post.updated_at = datetime.utcnow()
                db.commit()
                processed += 1
            except Exception as e:
                logger.error(f"Social post error {post.id}: {e}")
                post.status = "failed"
                post.error = str(e)
                post.updated_at = datetime.utcnow()
                db.commit()
        return processed

    @staticmethod
    def _send_post(post: SocialPost) -> bool:
        platform = (post.platform or "telegram").lower()
        if platform == "telegram":
            return SocialScheduler._send_telegram(post)
        if platform == "vk":
            return SocialScheduler._send_vk(post)
        # Placeholder for Instagram
        logger.warning(f"Social post platform {platform} not implemented; marking as failed")
        post.error = f"Platform {platform} not yet supported"
        return False

    @staticmethod
    def _send_telegram(post: SocialPost) -> bool:
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
            raise RuntimeError("TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNEL_ID not configured")
        caption = ""
        if post.title:
            caption += f"*{post.title}*\n\n"
        caption += post.content
        try:
            if post.media_url:
                # Send photo with caption
                resp = requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
                    json={
                        "chat_id": TELEGRAM_CHANNEL_ID,
                        "photo": post.media_url,
                        "caption": caption,
                        "parse_mode": "Markdown",
                    },
                    timeout=20,
                )
            else:
                # Send text message
                resp = requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": TELEGRAM_CHANNEL_ID,
                        "text": caption,
                        "parse_mode": "Markdown",
                    },
                    timeout=15,
                )
            if not resp.ok:
                raise RuntimeError(resp.text)
            return True
        except Exception as e:
            logger.error(f"Telegram post send error: {e}")
            return False

    @staticmethod
    def _send_vk(post: SocialPost) -> bool:
        if not VK_ACCESS_TOKEN or not VK_GROUP_ID:
            raise RuntimeError("VK_ACCESS_TOKEN or VK_GROUP_ID not configured")
        # Build message: title + content
        message = ""
        if post.title:
            message += f"{post.title}\n\n"
        message += post.content
        owner_id = VK_GROUP_ID
        try:
            attachments = None
            if post.media_url:
                # 1) Get upload server
                srv_resp = requests.get(
                    "https://api.vk.com/method/photos.getWallUploadServer",
                    params={
                        "group_id": str(abs(int(owner_id))),
                        "access_token": VK_ACCESS_TOKEN,
                        "v": "5.199",
                    },
                    timeout=15,
                )
                srv_json = srv_resp.json()
                if "error" in srv_json:
                    raise RuntimeError(f"VK getWallUploadServer error: {srv_json}")
                upload_url = srv_json["response"]["upload_url"]

                # 2) Download media and upload to VK
                file_resp = requests.get(post.media_url, timeout=20)
                file_resp.raise_for_status()
                files = {"photo": ("image.jpg", file_resp.content)}
                up_resp = requests.post(upload_url, files=files, timeout=30)
                up_json = up_resp.json()
                if "photo" not in up_json or "server" not in up_json or "hash" not in up_json:
                    raise RuntimeError(f"VK upload error: {up_json}")

                # 3) Save photo
                save_resp = requests.post(
                    "https://api.vk.com/method/photos.saveWallPhoto",
                    data={
                        "group_id": str(abs(int(owner_id))),
                        "photo": up_json["photo"],
                        "server": up_json["server"],
                        "hash": up_json["hash"],
                        "access_token": VK_ACCESS_TOKEN,
                        "v": "5.199",
                    },
                    timeout=20,
                )
                save_json = save_resp.json()
                if "error" in save_json:
                    raise RuntimeError(f"VK saveWallPhoto error: {save_json}")
                photo = save_json["response"][0]
                attachments = f"photo{photo['owner_id']}_{photo['id']}"

            # 4) Post to wall
            wall_params = {
                "owner_id": owner_id,  # e.g. -123456789 for community
                "from_group": 1,
                "message": message,
                "access_token": VK_ACCESS_TOKEN,
                "v": "5.199",
            }
            if attachments:
                wall_params["attachments"] = attachments
            resp = requests.post("https://api.vk.com/method/wall.post", data=wall_params, timeout=20)
            data = resp.json()
            if not resp.ok or "error" in data:
                raise RuntimeError(str(data))
            return True
        except Exception as e:
            logger.error(f"VK post send error: {e}")
            return False

