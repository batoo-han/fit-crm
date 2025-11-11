"""Service for FAQ management and AI-powered question matching."""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_
from loguru import logger
import json
from database.models_crm import FAQ
from services.ai_service import ai_service


class FAQService:
    """Service for managing FAQ and finding answers."""
    
    @staticmethod
    def search_faq(
        db: Session,
        query: str,
        category: Optional[str] = None,
        limit: int = 5
    ) -> List[FAQ]:
        """
        Search FAQ by query text.
        
        Args:
            db: Database session
            query: Search query
            category: Optional category filter
            limit: Maximum number of results
            
        Returns:
            List of FAQ items sorted by relevance
        """
        # Base query
        faq_query = db.query(FAQ).filter(FAQ.is_active == True)
        
        # Filter by category if provided
        if category:
            faq_query = faq_query.filter(FAQ.category == category)
        
        # Search in question and answer
        search_term = f"%{query.lower()}%"
        faq_items = faq_query.filter(
            or_(
                FAQ.question.ilike(search_term),
                FAQ.answer.ilike(search_term)
            )
        ).order_by(FAQ.priority.desc(), FAQ.use_count.desc()).limit(limit).all()
        
        # If no direct matches, try keyword matching
        if not faq_items:
            all_faq = faq_query.all()
            query_words = set(query.lower().split())
            
            scored_faq = []
            for faq in all_faq:
                score = 0
                # Check keywords
                if faq.keywords:
                    try:
                        keywords = json.loads(faq.keywords)
                        if isinstance(keywords, list):
                            for keyword in keywords:
                                if keyword.lower() in query_words:
                                    score += 2
                    except:
                        pass
                
                # Check question words
                question_words = set(faq.question.lower().split())
                common_words = query_words & question_words
                score += len(common_words)
                
                if score > 0:
                    scored_faq.append((score, faq))
            
            # Sort by score and return top results
            scored_faq.sort(key=lambda x: x[0], reverse=True)
            faq_items = [faq for _, faq in scored_faq[:limit]]
        
        return faq_items
    
    @staticmethod
    async def get_ai_answer(
        db: Session,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Get AI-generated answer for a question, using FAQ as context.
        
        Args:
            db: Database session
            question: User's question
            context: Optional context (client data, etc.)
            
        Returns:
            AI-generated answer or None if FAQ not found
        """
        # Search for similar FAQ items
        faq_items = FAQService.search_faq(db, question, limit=3)
        
        if not faq_items:
            return None
        
        # Build context from FAQ
        faq_context = "\n\n".join([
            f"Вопрос: {faq.question}\nОтвет: {faq.answer}"
            for faq in faq_items
        ])
        
        # Build system prompt
        system_prompt = """Ты - AI-ассистент фитнес-тренера. Твоя задача - отвечать на вопросы клиентов, используя информацию из базы знаний FAQ.

Используй предоставленные FAQ для ответа на вопрос клиента. Если вопрос не полностью соответствует FAQ, адаптируй ответ, сохраняя суть информации.

Будь дружелюбным, профессиональным и мотивирующим. Используй эмодзи умеренно."""
        
        # Build user prompt
        user_prompt = f"""Вопрос клиента: {question}

База знаний FAQ:
{faq_context}

Ответь на вопрос клиента, используя информацию из FAQ. Если вопрос не полностью покрывается FAQ, дополни ответ общей информацией, но не придумывай детали, которых нет в FAQ."""
        
        # Add client context if provided
        if context:
            context_str = "\n".join([f"{k}: {v}" for k, v in context.items() if v])
            user_prompt += f"\n\nКонтекст клиента:\n{context_str}"
        
        try:
            # Generate AI answer
            answer = await ai_service.generate_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=1000,
                temperature=0.7
            )
            
            # Increment use count for matched FAQ items
            for faq in faq_items:
                faq.use_count += 1
            db.commit()
            
            return answer
        except Exception as e:
            logger.error(f"Error generating AI answer: {e}")
            # Fallback to first FAQ answer
            if faq_items:
                faq_items[0].use_count += 1
                db.commit()
                return faq_items[0].answer
            return None
    
    @staticmethod
    def get_faq_by_id(db: Session, faq_id: int) -> Optional[FAQ]:
        """Get FAQ by ID."""
        return db.query(FAQ).filter(FAQ.id == faq_id).first()
    
    @staticmethod
    def get_all_faq(
        db: Session,
        category: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[FAQ]:
        """Get all FAQ items, optionally filtered."""
        query = db.query(FAQ)
        
        if category:
            query = query.filter(FAQ.category == category)
        if is_active is not None:
            query = query.filter(FAQ.is_active == is_active)
        
        return query.order_by(FAQ.priority.desc(), FAQ.question).all()
    
    @staticmethod
    def create_faq(
        db: Session,
        question: str,
        answer: str,
        category: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        priority: int = 0,
        created_by: Optional[int] = None
    ) -> FAQ:
        """Create new FAQ item."""
        faq = FAQ(
            question=question,
            answer=answer,
            category=category,
            keywords=json.dumps(keywords) if keywords else None,
            priority=priority,
            is_active=True,
            created_by=created_by
        )
        db.add(faq)
        db.commit()
        db.refresh(faq)
        logger.info(f"Created FAQ {faq.id}: {question[:50]}...")
        return faq
    
    @staticmethod
    def update_faq(
        db: Session,
        faq_id: int,
        question: Optional[str] = None,
        answer: Optional[str] = None,
        category: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        priority: Optional[int] = None,
        is_active: Optional[bool] = None,
        updated_by: Optional[int] = None
    ) -> Optional[FAQ]:
        """Update FAQ item."""
        faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
        if not faq:
            return None
        
        if question is not None:
            faq.question = question
        if answer is not None:
            faq.answer = answer
        if category is not None:
            faq.category = category
        if keywords is not None:
            faq.keywords = json.dumps(keywords) if keywords else None
        if priority is not None:
            faq.priority = priority
        if is_active is not None:
            faq.is_active = is_active
        if updated_by is not None:
            faq.updated_by = updated_by
        
        db.commit()
        db.refresh(faq)
        logger.info(f"Updated FAQ {faq_id}")
        return faq
    
    @staticmethod
    def delete_faq(db: Session, faq_id: int) -> bool:
        """Delete FAQ item."""
        faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
        if not faq:
            return False
        
        db.delete(faq)
        db.commit()
        logger.info(f"Deleted FAQ {faq_id}")
        return True


