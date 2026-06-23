import os
import csv
import logging
from io import BytesIO, StringIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from app import models

logger = logging.getLogger(__name__)

def generate_project_csv(project: models.Project) -> str:
    """
    Generates a CSV string containing the shot list sheet for the project.
    """
    output = StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        "Scene Number", "Scene Heading", "Shot Number", "Shot Size", 
        "Angle", "Movement", "Lens", "Lighting", "Emotion", "Notes"
    ])
    
    sorted_scenes = sorted(project.scenes, key=lambda s: s.order)
    for scene in sorted_scenes:
        sorted_shots = sorted(scene.shots, key=lambda sh: sh.order)
        for shot in sorted_shots:
            writer.writerow([
                scene.scene_number,
                scene.heading,
                shot.shot_number,
                shot.shot_size or "",
                shot.angle or "",
                shot.movement or "",
                shot.lens or "",
                shot.lighting or "",
                shot.emotion or "",
                shot.notes or ""
            ])
            
    return output.getvalue()

def generate_project_pdf(project: models.Project) -> bytes:
    """
    Generates a professional PDF containing Title Page, Screenplay, and a visual Storyboard/Shot grid.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitlePageTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=32,
        leading=38,
        alignment=1,
        textColor=colors.HexColor("#1A1A24")
    )
    
    subtitle_style = ParagraphStyle(
        'TitlePageSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=14,
        leading=18,
        alignment=1,
        textColor=colors.HexColor("#4A4A5A")
    )
    
    heading_style = ParagraphStyle(
        'ScriptSceneHeading',
        parent=styles['Normal'],
        fontName='Courier-Bold',
        fontSize=12,
        leading=14,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor("#000000")
    )
    
    action_style = ParagraphStyle(
        'ScriptAction',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=11,
        leading=14,
        spaceAfter=8
    )
    
    dialogue_style = ParagraphStyle(
        'ScriptDialogue',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=11,
        leading=14,
        leftIndent=1.0*inch,
        rightIndent=1.0*inch,
        spaceAfter=8
    )
    
    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        spaceBefore=15,
        spaceAfter=10,
        textColor=colors.HexColor("#1A1A24")
    )
    
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=11
    )
    
    story = []
    
    # --- TITLE PAGE ---
    story.append(Spacer(1, 2.0*inch))
    story.append(Paragraph(project.title.upper(), title_style))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(project.logline or "An Original Screenplay", subtitle_style))
    story.append(Spacer(1, 2.5*inch))
    story.append(Paragraph("Created with 70MM AI Workspace", subtitle_style))
    story.append(PageBreak())
    
    # --- SCREENPLAY ---
    story.append(Paragraph("SCREENPLAY", section_title_style))
    story.append(Spacer(1, 0.1*inch))
    
    sorted_scenes = sorted(project.scenes, key=lambda s: s.order)
    for scene in sorted_scenes:
        story.append(Paragraph(f"SCENE {scene.scene_number}: {scene.heading}", heading_style))
        
        elements = []
        for act in scene.action_blocks:
            elements.append((act.order, "action", act.content))
        for dia in scene.dialogues:
            elements.append((dia.order, "dialogue", f"<b>{dia.character_name}</b><br/>{dia.content}"))
            
        elements.sort(key=lambda x: x[0])
        
        for _, elem_type, content in elements:
            if elem_type == "action":
                story.append(Paragraph(content, action_style))
            elif elem_type == "dialogue":
                story.append(Paragraph(content, dialogue_style))
                
    story.append(PageBreak())
    
    # --- SHOT PLANNER & STORYBOARD ---
    story.append(Paragraph("SHOT PLANNER & STORYBOARD", section_title_style))
    story.append(Spacer(1, 0.15*inch))
    
    for scene in sorted_scenes:
        if not scene.shots:
            continue
            
        story.append(Paragraph(f"SCENE {scene.scene_number}: {scene.heading}", heading_style))
        story.append(Spacer(1, 0.05*inch))
        
        sorted_shots = sorted(scene.shots, key=lambda sh: sh.order)
        for shot in sorted_shots:
            img_flowable = None
            
            if shot.storyboard_frames:
                frame = shot.storyboard_frames[0]
                if frame.status == "completed" and frame.image_url:
                    local_filename = os.path.basename(frame.image_url)
                    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "storyboards")
                    local_path = os.path.join(static_dir, local_filename)
                    if os.path.exists(local_path):
                        try:
                            img_flowable = Image(local_path, width=3.0*inch, height=1.5*inch)
                        except Exception as e:
                            logger.error(f"Error loading image in PDF: {str(e)}")
            
            if not img_flowable:
                img_flowable = Paragraph("<b>No Storyboard Frame Generated</b>", table_cell_style)
                
            metadata_text = f"""
            <b>Shot Number:</b> {shot.shot_number}<br/>
            <b>Size:</b> {shot.shot_size or "N/A"} | <b>Angle:</b> {shot.angle or "N/A"}<br/>
            <b>Lens:</b> {shot.lens or "N/A"} | <b>Movement:</b> {shot.movement or "N/A"}<br/>
            <b>Lighting:</b> {shot.lighting or "N/A"}<br/>
            <b>Emotion:</b> {shot.emotion or "N/A"}<br/>
            <b>Notes:</b> {shot.notes or ""}
            """
            metadata_flowable = Paragraph(metadata_text, table_cell_style)
            
            shot_table_data = [[img_flowable, metadata_flowable]]
            shot_table = Table(shot_table_data, colWidths=[3.2*inch, 3.8*inch])
            shot_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8F9FA")),
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#E2E8F0")),
                ('TOPPADDING', (0,0), (-1,-1), 10),
                ('BOTTOMPADDING', (0,0), (-1,-1), 10),
                ('LEFTPADDING', (0,0), (-1,-1), 10),
                ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ]))
            
            story.append(shot_table)
            story.append(Spacer(1, 0.15*inch))
            
    doc.build(story)
    return buffer.getvalue()
