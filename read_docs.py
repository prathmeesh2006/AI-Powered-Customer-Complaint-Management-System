import zipfile
import xml.etree.ElementTree as ET
import os

def read_docx(filepath):
    with zipfile.ZipFile(filepath, 'r') as z:
        with z.open('word/document.xml') as f:
            tree = ET.parse(f)
            root = tree.getroot()
            paragraphs = []
            for para in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
                texts = []
                for t in para.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
                    if t.text:
                        texts.append(t.text)
                if texts:
                    paragraphs.append(''.join(texts))
            return '\n'.join(paragraphs)

docs = [
    'AIVOA_PRD.docx',
    'AIVOA_Tech_Stack_and_Architecture.docx', 
    'AIVOA_UI_UX_Specification.docx'
]

for doc in docs:
    filepath = os.path.join('c:/AIVOA_Project', doc)
    content = read_docx(filepath)
    outname = doc.replace('.docx', '_extracted.txt')
    outpath = os.path.join('c:/AIVOA_Project', outname)
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Written: {outpath} ({len(content)} chars)')
