import fitz
import pymupdf

doc = pymupdf.open(pdf_path) # open a document
for page in doc: # iterate the document pages
    page_dict = page.get_textpage()
    print(page_dict)
