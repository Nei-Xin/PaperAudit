"""Render the completed Markdown report; run with bundled ReportLab Python."""
from pathlib import Path
import html
import re
import argparse
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,default=ROOT/'eval/hy3_final_20260907/submission_report.md')
    parser.add_argument('--output',type=Path,default=ROOT/'output/pdf/PaperAudit_Hy3_experiment_report.pdf')
    parser.add_argument('--model',default='Hy3')
    args=parser.parse_args()
    source=args.source
    output=args.output
    output.parent.mkdir(parents=True,exist_ok=True)
    pdfmetrics.registerFont(TTFont('ReportCJK','C:/Windows/Fonts/simsun.ttc',subfontIndex=0))
    styles={
        'body':ParagraphStyle('body',fontName='ReportCJK',fontSize=10,leading=15,spaceAfter=7,wordWrap='CJK'),
        'title':ParagraphStyle('title',fontName='ReportCJK',fontSize=20,leading=29,spaceAfter=18,textColor=colors.HexColor('#16334b')),
        'h2':ParagraphStyle('h2',fontName='ReportCJK',fontSize=14,leading=21,spaceBefore=15,spaceAfter=9,keepWithNext=True,textColor=colors.HexColor('#16334b')),
        'h3':ParagraphStyle('h3',fontName='ReportCJK',fontSize=11,leading=17,spaceBefore=10,spaceAfter=6,keepWithNext=True),
        'cell':ParagraphStyle('cell',fontName='ReportCJK',fontSize=8,leading=12,wordWrap='CJK'),
    }
    def para(text,style='body'):
        text=re.sub(r'`([^`]+)`',r'\1',text)
        return Paragraph(html.escape(text).replace('\n','<br/>'),styles[style])
    story=[]
    for block in source.read_text(encoding='utf-8').split('\n\n'):
        block=block.strip()
        if not block:
            continue
        if block.startswith('|'):
            rows=[[c.strip() for c in line.strip().strip('|').split('|')] for line in block.splitlines()]
            rows=[r for r in rows if not all(re.fullmatch(r'[-: ]+',c) for c in r)]
            count=len(rows[0]); width=491/count
            table=Table([[para(c,'cell') for c in row] for row in rows],colWidths=[width]*count,repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dce8ef')),
                ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f5f8fa')]),
                ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),
                ('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
                ('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#a9bac6'))]))
            story.extend([table,Spacer(1,10)])
        elif block.startswith('### '):
            story.append(para(block[4:],'h3'))
        elif block.startswith('## '):
            story.append(para(block[3:],'h2'))
        elif block.startswith('# '):
            story.append(para(block[2:],'title'))
        else:
            story.append(para(block))
    def footer(canvas,doc):
        canvas.setFont('ReportCJK',8)
        canvas.setFillColor(colors.HexColor('#617484'))
        canvas.drawString(52,29,'PaperAudit | '+args.model+' 实验数据报告')
        canvas.drawRightString(A4[0]-52,29,str(doc.page))
    SimpleDocTemplate(str(output),pagesize=A4,leftMargin=52,rightMargin=52,topMargin=45,bottomMargin=48,
        title='PaperAudit '+args.model+' 实验数据报告',author='PaperAudit').build(story,onFirstPage=footer,onLaterPages=footer)
    print(output)

if __name__=='__main__':
    main()
