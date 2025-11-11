"""Service for managing payment status and pipeline automation."""
import json
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from loguru import logger

from database.db import get_db_session
from database.models import Payment, Client, TrainingProgram
from database.models_crm import ClientAction, ActionType, PipelineStage, PromoCode, PromoUsage
from services.payments_yookassa import get_yookassa_payment_status, parse_yookassa_status
from services.pipeline_service import PipelineAutomation
from config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY
from services.program_delivery import deliver_program_to_client


class PaymentService:
    """Service for checking payment status and updating pipeline."""
    
    @staticmethod
    def check_payment_status(payment: Payment) -> bool:
        """
        Check payment status from YooKassa and update if changed.
        
        Args:
            payment: Payment object to check
            
        Returns:
            True if status was updated
        """
        if not payment.payment_id:
            return False
        
        if payment.payment_method != "yookassa":
            return False
        
        if payment.status == "completed":
            # Already completed, no need to check
            return False
        
        try:
            import asyncio
            # Get payment status from YooKassa
            yookassa_data = asyncio.run(get_yookassa_payment_status(payment.payment_id))
            yookassa_status = yookassa_data.get("status", "pending")
            internal_status = parse_yookassa_status(yookassa_status)
            
            # Update payment status if changed
            if internal_status != payment.status:
                db = get_db_session()
                try:
                    payment.status = internal_status
                    if internal_status == "completed":
                        payment.completed_at = datetime.utcnow()
                        # Update pipeline and create action
                        PaymentService._handle_payment_completed(db, payment)
                    elif internal_status == "failed":
                        logger.info(f"Payment {payment.id} failed")
                    
                    db.commit()
                    logger.info(f"Payment {payment.id} status updated to {internal_status}")
                    return True
                except Exception as e:
                    logger.error(f"Error updating payment {payment.id}: {e}")
                    db.rollback()
                    return False
                finally:
                    db.close()
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking payment {payment.id} status: {e}")
            return False
    
    @staticmethod
    def _handle_payment_completed(db: Session, payment: Payment):
        """
        Handle completed payment - update pipeline and create action.
        
        Args:
            db: Database session
            payment: Completed payment
        """
        try:
            client = db.query(Client).filter(Client.id == payment.client_id).first()
            if not client:
                logger.warning(f"Client {payment.client_id} not found for payment {payment.id}")
                return
            
            # Create action
            action = ClientAction(
                client_id=client.id,
                action_type=ActionType.PAYMENT_RECEIVED.value,
                action_date=datetime.utcnow(),
                description=f"Получена оплата: {payment.amount}₽ ({payment.payment_type})",
                created_by=None  # Система
            )
            db.add(action)
            
            # Update pipeline through automation
            automation = PipelineAutomation(db)
            automation.handle_action_created(
                client=client,
                action=action,
                created_by=None,
                follow_up_hours_override=None,
            )
            
            # Mark program as paid if applicable
            if payment.payment_type in ["1month", "3months"]:
                # Find current program or create new paid program
                current_program = db.query(TrainingProgram).filter(
                    TrainingProgram.client_id == client.id,
                    TrainingProgram.program_type == payment.payment_type
                ).order_by(TrainingProgram.created_at.desc()).first()
                
                if current_program:
                    current_program.is_paid = True
                    logger.info(f"Marked program {current_program.id} as paid for client {client.id}")
                else:
                    # Create a placeholder paid program
                    # The actual program should be assigned by admin
                    logger.info(f"No program found for payment {payment.id}, program should be assigned manually")
            
            db.commit()
            logger.info(f"Handled completed payment {payment.id} for client {client.id}")

            # Register promo usage after commit to ensure payment id exists
            if payment.promo_code:
                promo = db.query(PromoCode).filter(PromoCode.code == payment.promo_code).first()
                if promo:
                    existing_usage = (
                        db.query(PromoUsage)
                        .filter(PromoUsage.payment_id == payment.id)
                        .first()
                    )
                    if not existing_usage:
                        promo.used_count = (promo.used_count or 0) + 1
                        usage = PromoUsage(
                            promo_code_id=promo.id,
                            client_id=client.id,
                            payment_id=payment.id,
                        )
                        db.add(usage)
                        db.commit()
                        logger.info(f"Promo code {promo.code} usage registered for payment {payment.id}")
            
            PaymentService._schedule_post_payment_workflow(payment.id, payment.payment_metadata)
            
        except Exception as e:
            logger.error(f"Error handling payment completion: {e}")
            db.rollback()
            raise
    
    @staticmethod
    async def check_pending_payments_async(limit: int = 100) -> int:
        """
        Async version of check_pending_payments.
        Check all pending payments and update their status.
        
        Args:
            limit: Maximum number of payments to check
            
        Returns:
            Number of payments updated
        """
        db = get_db_session()
        updated_count = 0
        try:
            # Get pending payments with YooKassa payment_id
            pending_payments = db.query(Payment).filter(
                Payment.status == "pending",
                Payment.payment_id.isnot(None),
                Payment.payment_method == "yookassa"
            ).limit(limit).all()
            
            logger.info(f"Checking {len(pending_payments)} pending payments")
            
            for payment in pending_payments:
                try:
                    # Get payment status from YooKassa (async)
                    yookassa_data = await get_yookassa_payment_status(payment.payment_id)
                    yookassa_status = yookassa_data.get("status", "pending")
                    internal_status = parse_yookassa_status(yookassa_status)
                    
                    # Update payment status if changed
                    if internal_status != payment.status:
                        payment.status = internal_status
                        if internal_status == "completed":
                            payment.completed_at = datetime.utcnow()
                            PaymentService._handle_payment_completed(db, payment)
                        elif internal_status == "failed":
                            logger.info(f"Payment {payment.id} failed")
                        
                        db.commit()
                        updated_count += 1
                        logger.info(f"Payment {payment.id} status updated to {internal_status}")
                        
                except Exception as e:
                    logger.error(f"Error checking payment {payment.id}: {e}")
                    db.rollback()
            
            logger.info(f"Updated {updated_count} payment statuses")
            return updated_count
            
        except Exception as e:
            logger.error(f"Error checking pending payments: {e}")
            db.rollback()
            return 0
        finally:
            db.close()
    
    @staticmethod
    def check_pending_payments(limit: int = 100) -> int:
        """
        Check all pending payments and update their status (sync wrapper).
        
        Args:
            limit: Maximum number of payments to check
            
        Returns:
            Number of payments updated
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            # If loop is running, we can't use run_until_complete
            # Return 0 and log warning - should use async version instead
            logger.warning("Event loop is running, use check_pending_payments_async instead")
            return 0
        
        return loop.run_until_complete(PaymentService.check_pending_payments_async(limit=limit))
    
    @staticmethod
    def _parse_metadata(metadata_raw: Optional[str]) -> Dict[str, Any]:
        if not metadata_raw:
            return {}
        try:
            return json.loads(metadata_raw)
        except Exception:
            logger.warning("Failed to parse payment metadata")
            return {}

    @staticmethod
    def _schedule_post_payment_workflow(payment_id: int, metadata_raw: Optional[str]) -> None:
        metadata = PaymentService._parse_metadata(metadata_raw)
        if not metadata or metadata.get("source") != "website":
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(asyncio.to_thread(PaymentService._process_purchase_completion, payment_id))
        except RuntimeError:
            PaymentService._process_purchase_completion(payment_id)

    @staticmethod
    def _process_purchase_completion(payment_id: int) -> None:
        db = get_db_session()
        try:
            payment = db.query(Payment).filter(Payment.id == payment_id).first()
            if not payment or payment.status != "completed":
                return
            metadata = PaymentService._parse_metadata(payment.payment_metadata)
            if not metadata or metadata.get("source") != "website":
                return
            if metadata.get("program_id"):
                logger.info(f"Program already issued for payment {payment_id}, skipping")
                return
            client = db.query(Client).filter(Client.id == payment.client_id).first()
            if not client:
                logger.warning(f"No client for payment {payment_id}")
                return

            if metadata.get("auto_program") and metadata.get("program_data") and metadata.get("formatted_program"):
                program_type = metadata.get("program_type") or "paid_monthly"
                program = TrainingProgram(
                    client_id=client.id,
                    program_type=program_type,
                    program_data=json.dumps(metadata["program_data"], ensure_ascii=False),
                    formatted_program=metadata["formatted_program"],
                    is_paid=True,
                    assigned_at=datetime.utcnow(),
                )
                db.add(program)
                db.commit()
                db.refresh(program)

                client.current_program_id = program.id
                db.commit()

                metadata["program_id"] = program.id
                payment.payment_metadata = json.dumps(metadata, ensure_ascii=False)
                db.commit()

                channels = metadata.get("delivery_channels") or []
                if channels:
                    deliver_program_to_client(program, client, channels, metadata.get("message"))
            else:
                if metadata.get("auto_program"):
                    logger.warning(f"No stored program data for payment {payment_id}; manual выдача требуется")
                metadata["processed"] = True
                payment.payment_metadata = json.dumps(metadata, ensure_ascii=False)
                db.commit()
        except Exception as e:
            logger.error(f"Error in post-payment workflow for payment {payment_id}: {e}")
            db.rollback()
        finally:
            db.close()

    @staticmethod
    def update_payment_from_webhook(payment_id: str, status: str, metadata: Optional[dict] = None) -> bool:
        """
        Update payment status from YooKassa webhook.
        
        Args:
            payment_id: YooKassa payment ID
            status: Payment status from YooKassa
            metadata: Optional metadata from webhook
            
        Returns:
            True if payment was updated
        """
        db = get_db_session()
        try:
            payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
            if not payment:
                logger.warning(f"Payment with YooKassa ID {payment_id} not found")
                return False
            
            internal_status = parse_yookassa_status(status)
            
            # Update payment status
            old_status = payment.status
            payment.status = internal_status
            if metadata:
                existing_meta = PaymentService._parse_metadata(payment.payment_metadata)
                merged_meta = existing_meta.copy()
                promo_code = metadata.get("promo_code")
                if promo_code:
                    payment.promo_code = promo_code
                discount = metadata.get("discount_amount")
                if discount is not None:
                    try:
                        payment.discount_amount = float(discount)
                    except (TypeError, ValueError):
                        logger.warning(f"Invalid discount amount in metadata: {discount}")
                final_amount = metadata.get("final_amount")
                if final_amount is not None:
                    try:
                        payment.final_amount = float(final_amount)
                    except (TypeError, ValueError):
                        logger.warning(f"Invalid final amount in metadata: {final_amount}")
                merged_meta.update(metadata)
                payment.payment_metadata = json.dumps(merged_meta, ensure_ascii=False)
            
            if internal_status == "completed" and old_status != "completed":
                payment.completed_at = datetime.utcnow()
                PaymentService._handle_payment_completed(db, payment)
            elif internal_status == "failed":
                logger.info(f"Payment {payment.id} failed via webhook")
            
            db.commit()
            logger.info(f"Payment {payment.id} updated from webhook: {old_status} → {internal_status}")
            if internal_status == "completed":
                PaymentService._schedule_post_payment_workflow(payment.id, payment.payment_metadata)
            return True
            
        except Exception as e:
            logger.error(f"Error updating payment from webhook: {e}")
            db.rollback()
            return False
        finally:
            db.close()

