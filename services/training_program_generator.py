"""Service for generating training programs from Google Sheets."""
from typing import Dict, List, Optional, Any
from loguru import logger
import aiohttp
import csv
import io
from config import (
    TRAINING_PLAN_WOMEN,
    TRAINING_PLAN_MEN,
)
import re


class TrainingProgramGenerator:
    """Generator for training programs based on client data."""
    
    def __init__(self):
        """Initialize generator - uses public CSV access to Google Sheets."""
        logger.info("TrainingProgramGenerator initialized - using public CSV access")
    
    async def get_program_from_sheets(
        self,
        gender: str,
        age: int,
        experience: str,
        goal: str,
        location: str = "дом"
    ) -> Optional[Dict[str, Any]]:
        """
        Get training program from Google Sheets based on client parameters.
        
        Args:
            gender: 'male' or 'female'
            age: client age
            experience: 'beginner', 'intermediate', 'advanced'
            goal: 'muscle', 'weight_loss', 'endurance', 'general'
            location: 'дом' or 'зал'
        
        Returns:
            Dict with program data or None
        """
        
        try:
            # Determine which sheet to use
            sheet_name = "Men_12w_2" if gender == "male" else "Women_12w_2"
            
            # Map client parameters to table columns
            age_group = self._get_age_group(age)
            experience_ru = self._map_experience(experience)
            goal_ru = self._map_goal(goal)
            location_ru = location if location in ["дом", "зал"] else "дом"
            
            # Extract sheet ID from URL
            url = TRAINING_PLAN_MEN if gender == "male" else TRAINING_PLAN_WOMEN
            match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
            if match:
                sheet_id = match.group(1)
            else:
                logger.error("Could not extract sheet ID from URL")
                return None
            
            # Get data using public CSV access
            records = await self._get_records_from_csv(sheet_id, sheet_name)
            
            # Find matching program
            matching_program = None
            for record in records:
                if (record.get("Age_Group") == age_group and
                    record.get("Experience") == experience_ru and
                    record.get("Goal") == goal_ru and
                    record.get("Location") == location_ru):
                    matching_program = record
                    break
            
            # If no exact match, try to find closest
            if not matching_program:
                logger.warning(f"No exact match found, trying closest...")
                matching_program = self._find_closest_program(
                    records, age_group, experience_ru, goal_ru, location_ru
                )
            
            if matching_program:
                logger.info(f"Found program: {matching_program.get('Profile', 'Unknown')}")
                return self._format_program_data(matching_program, records)
            
            logger.error("No matching program found")
            return None
            
        except Exception as e:
            logger.error(f"Error getting program from sheets: {e}")
            return None
    
    def _get_age_group(self, age: int) -> str:
        """Map age to age group."""
        if age < 17:
            return "17-25"
        elif age < 26:
            return "17-25"
        elif age < 36:
            return "26-35"
        elif age < 46:
            return "36-45"
        elif age < 56:
            return "46-55"
        else:
            return "56+"
    
    def _map_experience(self, experience: str) -> str:
        """Map experience level to Russian."""
        mapping = {
            "beginner": "новичок",
            "intermediate": "средний",
            "advanced": "продвинутый"
        }
        return mapping.get(experience, "новичок")
    
    def _map_goal(self, goal: str) -> str:
        """Map goal to Russian."""
        mapping = {
            "muscle": "набор массы",
            "weight_loss": "похудение",
            "endurance": "выносливость",
            "general": "рекомпозиция"
        }
        return mapping.get(goal, "рекомпозиция")
    
    def _find_closest_program(
        self,
        records: List[Dict],
        age_group: str,
        experience: str,
        goal: str,
        location: str
    ) -> Optional[Dict]:
        """Find closest matching program."""
        # Priority: experience > location > age > goal
        for exp in [experience, "новичок"]:
            for loc in [location, "дом"]:
                for record in records:
                    if (record.get("Experience") == exp and
                        record.get("Location") == loc):
                        return record
        
        # Last resort: return first available
        return records[0] if records else None
    
    async def _get_records_from_csv(self, sheet_id: str, sheet_name: str) -> List[Dict]:
        """
        Get records from Google Sheets using public CSV export.
        
        Args:
            sheet_id: Google Sheet ID
            sheet_name: Name of the worksheet
        
        Returns:
            List of records as dictionaries
        """
        try:
            # Google Sheets CSV export URL
            # Format: https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(csv_url, timeout=30) as response:
                    if response.status != 200:
                        logger.error(f"Error fetching CSV: {response.status}")
                        return []
                    
                    csv_text = await response.text()
                    
                    # Parse CSV
                    csv_reader = csv.DictReader(io.StringIO(csv_text))
                    records = list(csv_reader)
                    
                    logger.info(f"Got {len(records)} records from CSV export")
                    return records
                    
        except Exception as e:
            logger.error(f"Error getting records from CSV: {e}")
            return []
    
    def _format_program_data(
        self,
        program_template: Dict,
        all_records: List[Dict]
    ) -> Dict[str, Any]:
        """Format program data for further processing."""
        profile = program_template.get("Profile", "")
        
        # Get all weeks for this profile
        program_weeks = []
        for record in all_records:
            if record.get("Profile") == profile:
                program_weeks.append(record)
        
        # Group by week
        weeks_data = {}
        for week_record in program_weeks:
            week_num = week_record.get("Week", 1)
            if week_num not in weeks_data:
                weeks_data[week_num] = []
            weeks_data[week_num].append(week_record)
        
        return {
            "profile": profile,
            "age_group": program_template.get("Age_Group", ""),
            "goal": program_template.get("Goal", ""),
            "experience": program_template.get("Experience", ""),
            "location": program_template.get("Location", ""),
            "weeks": weeks_data,
            "raw_data": program_weeks
        }


# Global instance
program_generator = TrainingProgramGenerator()
