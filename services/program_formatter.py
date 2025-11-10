"""Service for formatting training programs using LLM."""
from typing import Dict, Any
from loguru import logger
from services.ai_service import ai_service
from config import TRAINER_NAME, TRAINER_TELEGRAM, TRAINER_PHONE


class ProgramFormatter:
    """Format training programs using LLM."""
    
    @staticmethod
    async def format_program(
        program_data: Dict[str, Any],
        client_name: str = "Клиент"
    ) -> str:
        """
        Format training program using LLM.
        
        Args:
            program_data: Program data from generator
            client_name: Client's name
        
        Returns:
            Formatted program text
        """
        # Build prompt for LLM
        prompt = f"""
Создай красивую программу тренировок на основе следующих данных:

Профиль: {program_data.get('profile', 'Unknown')}
Возрастная группа: {program_data.get('age_group', '')}
Цель: {program_data.get('goal', '')}
Опыт: {program_data.get('experience', '')}
Локация: {program_data.get('location', '')}

Данные программы тренировок:

{ProgramFormatter._format_program_data_for_llm(program_data)}

Создай программу в следующем формате:

1. ЗАГОЛОВОК - красивое название программы с именем клиента
2. ВВЕДЕНИЕ - краткое описание программы (2-3 предложения)
3. ОСНОВНЫЕ РЕКОМЕНДАЦИИ - список важных рекомендаций перед началом
4. ТАБЛИЦА ТРЕНИРОВОК - структурированная таблица по неделям и дням
5. ТЕХНИЧЕСКИЕ ПРИМЕЧАНИЯ - важные моменты по технике выполнения
6. КОНТАКТЫ ТРЕНЕРА - информация для связи с тренером {TRAINER_NAME}
7. ЧЕК-ЛИСТ ДЛЯ ТРЕНИРОВОК - что нужно проверить перед тренировкой

Используй эмодзи для улучшения читаемости. Сделай программу профессиональной, но понятной.
"""
        
        system_prompt = """Ты - профессиональный фитнес-тренер, который создает персонализированные программы тренировок.
Твоя задача - оформить программу тренировок так, чтобы она была:
- Понятной для клиента
- Профессиональной
- Мотивирующей
- Содержащей все необходимые детали

Используй структурированный формат с четкими разделами."""
        
        try:
            formatted_program = await ai_service.generate_response(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=4000,
                temperature=0.7
            )
            return formatted_program
        except Exception as e:
            logger.error(f"Error formatting program: {e}")
            return ProgramFormatter._fallback_format(program_data)
    
    @staticmethod
    def _format_program_data_for_llm(program_data: Dict[str, Any]) -> str:
        """Format program data for LLM prompt."""
        weeks_data = program_data.get('weeks', {})
        formatted = []
        
        for week_num in sorted(weeks_data.keys()):
            week_records = weeks_data[week_num]
            formatted.append(f"\nНЕДЕЛЯ {week_num}:")
            
            for record in week_records:
                day = record.get('Day', '')
                session = record.get('Session', '')
                microcycle = record.get('Microcycle', '')
                deload = record.get('Deload', 0)
                
                formatted.append(f"\n  День {day} - {session} ({microcycle})")
                if deload == 1:
                    formatted.append("  [РАЗГРУЗОЧНАЯ НЕДЕЛЯ -20% объёма]")
                
                # Exercises
                for i in range(1, 6):
                    ex_name = record.get(f'Ex{i}_Name', '')
                    if ex_name:
                        ex_sets = record.get(f'Ex{i}_Sets', '')
                        ex_reps = record.get(f'Ex{i}_Reps', '')
                        ex_pattern = record.get(f'Ex{i}_Pattern', '')
                        ex_alt = record.get(f'Ex{i}_Alt', '')
                        ex_notes = record.get(f'Ex{i}_Notes', '')
                        
                        formatted.append(f"    {i}. {ex_name}")
                        formatted.append(f"       Подходы: {ex_sets}, Повторения: {ex_reps}")
                        if ex_pattern:
                            formatted.append(f"       Паттерн: {ex_pattern}")
                        if ex_alt:
                            formatted.append(f"       Альтернативы: {ex_alt}")
                        if ex_notes:
                            formatted.append(f"       Примечания: {ex_notes}")
        
        return "\n".join(formatted)
    
    @staticmethod
    def _fallback_format(program_data: Dict[str, Any]) -> str:
        """Fallback formatting if LLM fails."""
        return f"""
# Программа тренировок

Профиль: {program_data.get('profile', 'Unknown')}
Цель: {program_data.get('goal', '')}
Опыт: {program_data.get('experience', '')}
Локация: {program_data.get('location', '')}

[Программа будет сформирована вручную тренером]

Контакты тренера:
📱 Telegram: {TRAINER_TELEGRAM}
📞 WhatsApp: {TRAINER_PHONE}
"""
