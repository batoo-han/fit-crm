"""Service for generating PDF files from training programs."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
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
        client_name: str = "Клиент"
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
            # Create PDF document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
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
            
            # Parse and add content
            lines = program_text.split('\n')
            current_section = []
            
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
            
            # Build PDF
            doc.build(story)
            
            logger.info(f"PDF generated successfully: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating PDF: {e}")
            return False
    
    @staticmethod
    def generate_program_pdf(
        program_text: str,
        client_id: int,
        client_name: str = "Клиент"
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
        # Create output directory
        os.makedirs("data/programs", exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"program_{client_id}_{timestamp}.pdf"
        output_path = os.path.join("data/programs", filename)
        
        # Generate PDF
        success = PDFGenerator.generate_pdf(program_text, output_path, client_name)
        
        if success:
            return output_path
        
        return None
