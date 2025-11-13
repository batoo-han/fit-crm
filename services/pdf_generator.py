"""Service for generating PDF files from training programs."""
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, KeepTogether
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from typing import Optional
import os
from datetime import datetime
from loguru import logger
from markdown import markdown
from html import unescape
import re

# Register fonts with Cyrillic support
def register_cyrillic_font():
    """Register a font that supports Cyrillic characters."""
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        
        # Try to find and register DejaVu Sans (common font with Cyrillic support)
        # Common paths for DejaVu Sans on different systems
        font_paths = [
            # Windows
            'C:/Windows/Fonts/arial.ttf',
            'C:/Windows/Fonts/arialbd.ttf',
            # Linux
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            # macOS
            '/Library/Fonts/Arial.ttf',
            '/System/Library/Fonts/Supplemental/Arial.ttf',
        ]
        
        # Try to register Arial (common on Windows) or DejaVu Sans
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('CyrillicFont', font_path))
                    logger.info(f"Registered Cyrillic font: {font_path}")
                    return 'CyrillicFont'
                except Exception as e:
                    logger.warning(f"Could not register font {font_path}: {e}")
                    continue
        
        # Try to register bold version separately
        bold_paths = [
            'C:/Windows/Fonts/arialbd.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
        ]
        for font_path in bold_paths:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('CyrillicFontBold', font_path))
                    logger.info(f"Registered Cyrillic bold font: {font_path}")
                except:
                    pass
        
        # If no font found, use default - we'll handle encoding differently
        logger.warning("No Cyrillic font found, using default with encoding workaround")
        return None
    except Exception as e:
        logger.warning(f"Could not register Cyrillic font: {e}")
        return None

# Register font on import
CYRILLIC_FONT_NAME = register_cyrillic_font()


class PDFGenerator:
    """Generate PDF files from training programs."""
    
    @staticmethod
    def generate_pdf(
        program_text: str,
        output_path: str,
        client_name: str = "Клиент",
        program_data: Optional[dict] = None,
        trainer_info: Optional[dict] = None,
        footer_template: Optional[str] = None
    ) -> bool:
        """
        Generate PDF from formatted program text.
        
        Args:
            program_text: Formatted program text (markdown or plain text)
            output_path: Path to save PDF
            client_name: Client's name
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create PDF document with landscape orientation
            doc = SimpleDocTemplate(
                output_path,
                pagesize=landscape(A4),
                rightMargin=40,
                leftMargin=40,
                topMargin=40,
                bottomMargin=40
            )
            
            # Container for PDF elements
            story = []
            styles = getSampleStyleSheet()
            
            # Use registered Cyrillic font or fallback
            font_name = CYRILLIC_FONT_NAME if CYRILLIC_FONT_NAME else 'Helvetica'
            
            # Custom styles with Cyrillic font support
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=HexColor('#1a1a1a'),
                spaceAfter=30,
                alignment=TA_CENTER,
                fontName=font_name
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=16,
                textColor=HexColor('#2c3e50'),
                spaceAfter=12,
                spaceBefore=12,
                fontName=font_name
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=11,
                leading=14,
                spaceAfter=6,
                fontName=font_name
            )
            
            # Helper function to escape HTML and handle Cyrillic
            def escape_html(text):
                """Escape HTML special characters."""
                text = text.replace('&', '&amp;')
                text = text.replace('<', '&lt;')
                text = text.replace('>', '&gt;')
                return text
            
            # Add header with trainer info
            if trainer_info:
                header_data = []
                if trainer_info.get("name"):
                    header_data.append(f"Тренер: {trainer_info['name']}")
                if trainer_info.get("phone"):
                    header_data.append(f"Телефон: {trainer_info['phone']}")
                if trainer_info.get("telegram"):
                    header_data.append(f"Телеграм: {trainer_info['telegram']}")
                if trainer_info.get("date"):
                    header_data.append(f"Дата составления программы: {trainer_info['date']}")
                
                if header_data:
                    header_text = " | ".join(header_data)
                    header_style = ParagraphStyle(
                        'Header',
                        parent=styles['Normal'],
                        fontSize=10,
                        textColor=HexColor('#666666'),
                        alignment=TA_LEFT,
                        fontName=font_name
                    )
                    story.append(Paragraph(escape_html(header_text), header_style))
                    story.append(Spacer(1, 12))
            
            # Add title with program duration and gender
            title_text = "Программа тренировок"
            if program_data and isinstance(program_data, dict):
                weeks = program_data.get("weeks", {})
                week_count = len(weeks) if weeks else 0
                profile = program_data.get("profile", "")
                
                if week_count > 0:
                    # Склонение слова "неделя"
                    if week_count == 1:
                        week_word = "неделю"
                    elif week_count in [2, 3, 4]:
                        week_word = "недели"
                    else:
                        week_word = "недель"
                    
                    title_text += f" на {week_count} {week_word}"
                
                # Определение пола из profile
                if profile:
                    if profile.startswith("Women_") or profile.startswith("W_"):
                        title_text += " для женщин"
                    elif profile.startswith("Men_") or profile.startswith("M_"):
                        title_text += " для мужчин"
            
            story.append(Paragraph(escape_html(title_text), title_style))
            story.append(Spacer(1, 20))
            
            # If we have structured program_data, generate tables
            if program_data and isinstance(program_data, dict) and "weeks" in program_data:
                logger.info("Generating PDF from structured program_data with tables")
                story.extend(PDFGenerator._generate_tables_from_data(program_data, title_style, heading_style, normal_style, font_name))
                
                # Add footer template on new page if provided
                if footer_template:
                    story.append(PageBreak())
                    footer_style = ParagraphStyle(
                        'Footer',
                        parent=styles['Normal'],
                        fontSize=10,
                        leading=14,
                        fontName=font_name
                    )
                    # Split footer into paragraphs
                    footer_lines = footer_template.split('\n')
                    for line in footer_lines:
                        if line.strip():
                            story.append(Paragraph(escape_html(line.strip()), footer_style))
                        else:
                            story.append(Spacer(1, 6))
            else:
                # Fallback to text parsing
                logger.info("Generating PDF from formatted text (fallback)")
                # Parse and add content
                lines = program_text.split('\n')
                current_section = []
                
                # Log for debugging
                logger.info(f"Processing {len(lines)} lines of program text for PDF")
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        if current_section:
                            story.append(Spacer(1, 6))
                        current_section = []
                        continue
                    
                    # Escape HTML and ensure proper encoding
                    line_escaped = escape_html(line)
                    
                    # Check for headings
                    if line.startswith('# '):
                        if current_section:
                            story.append(Paragraph('<br/>'.join(escape_html(s) for s in current_section), normal_style))
                            current_section = []
                        story.append(Paragraph(escape_html(line[2:]), title_style))
                        story.append(Spacer(1, 12))
                    
                    elif line.startswith('## '):
                        if current_section:
                            story.append(Paragraph('<br/>'.join(escape_html(s) for s in current_section), normal_style))
                            current_section = []
                        story.append(Paragraph(escape_html(line[3:]), heading_style))
                        story.append(Spacer(1, 8))
                    
                    elif line.startswith('### '):
                        if current_section:
                            story.append(Paragraph('<br/>'.join(escape_html(s) for s in current_section), normal_style))
                            current_section = []
                        heading3_style = ParagraphStyle(
                            'CustomHeading3',
                            parent=styles['Heading3'],
                            fontSize=14,
                            fontName=font_name
                        )
                        story.append(Paragraph(escape_html(line[4:]), heading3_style))
                        story.append(Spacer(1, 6))
                    
                    # Check for lists
                    elif line.startswith('- ') or line.startswith('* ') or line.startswith('• '):
                        if current_section:
                            story.append(Paragraph('<br/>'.join(escape_html(s) for s in current_section), normal_style))
                            current_section = []
                        item_text = re.sub(r'^[-*•]\s+', '', line)
                        story.append(Paragraph(f"• {escape_html(item_text)}", normal_style))
                    
                    elif line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                        if current_section:
                            story.append(Paragraph('<br/>'.join(escape_html(s) for s in current_section), normal_style))
                            current_section = []
                        item_text = re.sub(r'^\d+\.\s+', '', line)
                        story.append(Paragraph(f"• {escape_html(item_text)}", normal_style))
                    
                    else:
                        # Regular paragraph
                        current_section.append(line)
                
                # Add remaining content
                if current_section:
                    story.append(Paragraph('<br/>'.join(escape_html(s) for s in current_section), normal_style))
            
            # Check if story is empty
            if not story:
                logger.warning(f"PDF story is empty for {output_path}, adding placeholder")
                story.append(Paragraph("Программа тренировок", title_style))
                story.append(Spacer(1, 12))
                story.append(Paragraph("Содержимое программы будет добавлено позже.", normal_style))
            
            # Build PDF
            try:
                logger.info(f"Building PDF with {len(story)} elements")
                doc.build(story)
                logger.info(f"PDF generated successfully: {output_path}, file size: {os.path.getsize(output_path) if os.path.exists(output_path) else 0} bytes")
                return True
            except Exception as build_error:
                logger.error(f"Error building PDF document: {build_error}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                return False
            
        except Exception as e:
            logger.error(f"Error generating PDF: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    @staticmethod
    def generate_program_pdf(
        program_text: str,
        client_id: int,
        client_name: str = "Клиент",
        program_data: Optional[dict] = None,
        trainer_info: Optional[dict] = None,
        footer_template: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate PDF for client and return file path.
        
        Args:
            program_text: Formatted program text
            client_id: Client ID
            client_name: Client's name
        
        Returns:
            Path to generated PDF or None
        """
        try:
            # Create output directory - используем /app/data/programs в контейнере или data/programs локально
            # Проверяем, находимся ли мы в контейнере (WORKDIR /app)
            if os.path.exists("/app"):
                output_dir = "/app/data/programs"
            else:
                output_dir = "data/programs"
            
            try:
                os.makedirs(output_dir, exist_ok=True)
                logger.info(f"Output directory ready: {output_dir}")
            except Exception as dir_error:
                logger.error(f"Failed to create output directory {output_dir}: {dir_error}")
                # Попробуем альтернативный путь
                if output_dir.startswith("/app"):
                    alt_dir = "data/programs"
                else:
                    alt_dir = "/app/data/programs"
                try:
                    os.makedirs(alt_dir, exist_ok=True)
                    output_dir = alt_dir
                    logger.info(f"Using alternative output directory: {output_dir}")
                except Exception as alt_dir_error:
                    logger.error(f"Failed to create alternative directory {alt_dir}: {alt_dir_error}")
                    # Используем текущую директорию как последний вариант
                    output_dir = "."
                    logger.warning(f"Using current directory for PDF output: {output_dir}")
            
            # Generate meaningful filename: <id клиента>_<кол-во недель>_weeks_<дата - DDMMYYYY>_<номер - 0001>
            date_str = datetime.now().strftime("%d%m%Y")
            
            # Extract number of weeks from program_data
            weeks_count = 0
            if program_data and isinstance(program_data, dict) and "weeks" in program_data:
                weeks_count = len(program_data.get("weeks", {}))
            
            # Generate base filename
            base_filename = f"{client_id}_{weeks_count}_weeks_{date_str}"
            
            # Find next available number (0001, 0002, etc.)
            file_number = 1
            while True:
                filename = f"{base_filename}_{file_number:04d}.pdf"
                output_path = os.path.join(output_dir, filename)
                if not os.path.exists(output_path):
                    break
                file_number += 1
                # Safety limit to avoid infinite loop
                if file_number > 9999:
                    # Fallback to timestamp if too many files
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{base_filename}_{timestamp}.pdf"
                    output_path = os.path.join(output_dir, filename)
                    break
            
            logger.info(f"Generating PDF: {output_path}")
            
            # Generate PDF
            success = PDFGenerator.generate_pdf(program_text, output_path, client_name, program_data, trainer_info, footer_template)
            
            if success and os.path.exists(output_path):
                logger.info(f"PDF generated successfully: {output_path}")
                return output_path
            else:
                logger.error(f"PDF generation failed or file not found: {output_path}")
                return None
                
        except Exception as e:
            logger.error(f"Error in generate_program_pdf: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    @staticmethod
    def _generate_tables_from_data(program_data: dict, title_style, heading_style, normal_style, font_name) -> list:
        """Generate PDF elements from structured program_data with tables."""
        from reportlab.lib import colors
        
        # Helper function to escape HTML
        def escape_html(text):
            """Escape HTML special characters."""
            if not text:
                return ""
            text = str(text)
            text = text.replace('&', '&amp;')
            text = text.replace('<', '&lt;')
            text = text.replace('>', '&gt;')
            return text
        
        elements = []
        weeks = program_data.get("weeks", {})
        
        # Process each week (removed program profile line)
        for week_num in sorted(weeks.keys(), key=lambda x: int(x) if str(x).isdigit() else 0):
            week_records = weeks[week_num]
            if not week_records:
                continue
            
            # Week header
            elements.append(Paragraph(f"Неделя {week_num}", heading_style))
            elements.append(Spacer(1, 8))
            
            # Group by day
            days_data = {}
            for record in week_records:
                day = record.get("Day", "")
                if day not in days_data:
                    days_data[day] = []
                days_data[day].append(record)
            
            # Process each day
            for day_num in sorted(days_data.keys(), key=lambda x: int(x) if str(x).isdigit() else 0):
                day_records = days_data[day_num]
                
                # Collect all elements for this day to keep together
                day_elements = []
                
                for record in day_records:
                    session = record.get("Session", "")
                    microcycle = record.get("Microcycle", "")
                    deload = record.get("Deload", 0)
                    
                    # Clean session name (remove " A", " B", " C" etc.)
                    session_clean = session
                    if session_clean and len(session_clean) > 0:
                        # Remove trailing space and single letter
                        parts = session_clean.rsplit(' ', 1)
                        if len(parts) == 2 and len(parts[1]) == 1 and parts[1].isalpha():
                            session_clean = parts[0]
                    
                    # Day/Session header with decorative styling
                    day_header = f"День {day_num} - {session_clean}"
                    if microcycle:
                        day_header += f" ({microcycle})"
                    if deload == 1:
                        day_header += " [РАЗГРУЗОЧНАЯ НЕДЕЛЯ -20% объёма]"
                    
                    # Header style with better formatting
                    day_header_style = ParagraphStyle(
                        'DayHeader',
                        parent=heading_style,
                        fontSize=14,
                        textColor=HexColor('#1a1a1a'),
                        spaceAfter=8,
                        spaceBefore=4,
                        fontName=font_name
                    )
                    day_elements.append(Paragraph(escape_html(day_header), day_header_style))
                    day_elements.append(Spacer(1, 4))
                    
                    # Build table data with Weight column
                    # Use Paragraph for header row too
                    table_data = [[
                        Paragraph("№", normal_style),
                        Paragraph("Упражнение", normal_style),
                        Paragraph("Подходы", normal_style),
                        Paragraph("Повторения", normal_style),
                        Paragraph("Вес*", normal_style),
                        Paragraph("Альтернатива", normal_style),
                        Paragraph("Примечание", normal_style)
                    ]]
                    
                    for i in range(1, 6):
                        ex_name = record.get(f'Ex{i}_Name', '')
                        if not ex_name:
                            continue
                        
                        ex_sets = record.get(f'Ex{i}_Sets', '')
                        ex_reps = record.get(f'Ex{i}_Reps', '')
                        ex_alt = record.get(f'Ex{i}_Alt', '')
                        ex_notes = record.get(f'Ex{i}_Notes', '')
                        
                        # Use Paragraph for text wrapping in cells
                        # Weight column is empty (for client to fill)
                        table_data.append([
                            Paragraph(str(i), normal_style),
                            Paragraph(escape_html(ex_name), normal_style),
                            Paragraph(str(ex_sets) if ex_sets else '', normal_style),
                            Paragraph(str(ex_reps) if ex_reps else '', normal_style),
                            Paragraph("", normal_style),  # Weight column - empty for client to fill
                            Paragraph(escape_html(ex_alt) if ex_alt else '', normal_style),
                            Paragraph(escape_html(ex_notes) if ex_notes else '', normal_style)
                        ])
                    
                    # Create table if we have exercises
                    if len(table_data) > 1:
                        # Landscape A4: 11.69 x 8.27 inches, margins 40pt = ~0.56 inch each side
                        # Available width: 11.69 - 0.56*2 = 10.57 inches
                        # Distribute columns: №, Упражнение, Подходы, Повторения, Вес*, Альтернатива, Примечание
                        table = Table(table_data, colWidths=[
                            0.5*inch,   # №
                            2.5*inch,   # Упражнение
                            0.7*inch,   # Подходы
                            0.8*inch,   # Повторения
                            0.8*inch,   # Вес*
                            2.0*inch,   # Альтернатива
                            2.5*inch    # Примечание
                        ])
                        
                        # Weight column index is 4 (0-indexed)
                        weight_col = 4
                        table.setStyle(TableStyle([
                            # Header row
                            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                            ('FONTNAME', (0, 0), (-1, 0), font_name),
                            ('FONTSIZE', (0, 0), (-1, 0), 9),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                            ('TOPPADDING', (0, 0), (-1, 0), 6),
                            # Data rows
                            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                            # Weight column - lighter background
                            ('BACKGROUND', (weight_col, 1), (weight_col, -1), colors.lightgrey),
                            ('FONTNAME', (0, 1), (-1, -1), font_name),
                            ('FONTSIZE', (0, 1), (-1, -1), 8),
                            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                            ('WORDWRAP', (0, 0), (-1, -1), True),  # Enable word wrap
                            ('LEFTPADDING', (0, 0), (-1, -1), 4),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                            ('TOPPADDING', (0, 1), (-1, -1), 4),
                            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
                        ]))
                        day_elements.append(table)
                        
                        # Add note about Weight column
                        note_style = ParagraphStyle(
                            'Note',
                            parent=normal_style,
                            fontSize=8,
                            textColor=HexColor('#666666'),
                            spaceBefore=4,
                            spaceAfter=0,
                            fontName=font_name
                        )
                        day_elements.append(Spacer(1, 4))
                        day_elements.append(Paragraph(escape_html("* Колонка 'Вес' предназначена для записи максимального рабочего веса за сессию"), note_style))
                        day_elements.append(Spacer(1, 8))
                
                # Keep each day together on one page
                if day_elements:
                    elements.append(KeepTogether(day_elements))
                    elements.append(PageBreak())  # New page for next day
        
        return elements
