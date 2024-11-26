#RFP Upload - Allows the user upload an RFP into a project directory and
#split the files in needed into smaller files for AI ingestion

input_data_dir = "c:\\CATarina\\data\\test\\input"
ingest_data_dir = "c:\\CATarina\\data\\test\\ingest"

import streamlit as st
from streamlit_pdf_viewer import pdf_viewer
import fitz  # PyMuPDF
import os
import pandas as pd
import shutil
import streamlit.components.v1 as components
from streamlit_js_eval import streamlit_js_eval

st.set_page_config(page_title="Upload", page_icon = "👩‍🔧", layout="wide")

@st.dialog("RFP File Manager")
def file_win(pdfdoc, mode = 'PDF'):
    st.session_state['dialog_open'] = True
    if mode == 'PDF':
        pdf_viewer(pdfdoc)
        if st.button("Close"):
            st.rerun()
    elif mode == 'File':
        uploaded_files = st.file_uploader(
        "Choose an RFP or RFI to process", accept_multiple_files=True, type =['pdf']
        )
        for uploaded_file in uploaded_files:
            bytes_data = uploaded_file.read()
            file_path = os.path.join(input_data_dir, uploaded_file.name)
            with open(file_path, 'wb') as file:
                file.write(bytes_data)
                file.close()
        if st.button("Close"):
            st.rerun()

#add funtion to dump pdf text only
def copy_pdf_text(pdf_path, output_dir):
    file_name_no_ext = filename_without_extension = os.path.splitext(os.path.basename(pdf_path))[0]
    pdf_document = fitz.open(pdf_path)
    text = ""
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        text = page.get_text()
        pdf_document_dest = fitz.open()
        txt_page = pdf_document_dest.new_page()
        position = fitz.Point(10, 10)  # (x, y) coordinates in points
        txt_page.insert_text(position, text, fontsize=10)
        file_name = file_name_no_ext + str(page_num) + ".pdf"
        pdf_document_dest.save(os.path.join(output_dir, file_name))
        pdf_document_dest.close()


def split_pdf_by_toc(pdf_path, output_dir, toc_depth=1):
    # Open the PDF file
    pdf_document = fitz.open(pdf_path)
    toc = pdf_document.get_toc(simple=True)
       
    # Filter TOC based on the desired depth
    toc = [entry for entry in toc if entry[0] <= toc_depth]

    for i, entry in enumerate(toc):
        title, page_num = entry[1], entry[2] - 1
        next_page_num = toc[i + 1][2] - 1 if i + 1 < len(toc) else pdf_document.page_count
        # Create a new PDF for each section
        new_pdf = fitz.open()
        new_pdf.insert_pdf(pdf_document, page_num,  next_page_num)
        # Save the new PDF
        output_path = f"{output_dir}/{title}.pdf"
        new_pdf.save(output_path)
        new_pdf.close()

    pdf_document.close()
    
def file_selector(folder_path='.'):
    filenames = os.listdir(folder_path)
    selected_filename = st.selectbox('Select a file', filenames)
    return os.path.join(folder_path, selected_filename)

def show_files(path):
    files_df = pd.DataFrame(columns=["file_name"])
    for i, file in enumerate(os.listdir(path)):
        new_row=pd.DataFrame([file], columns=files_df.columns)
        files_df = pd.concat([new_row, files_df], ignore_index=True)
    return files_df

def in_df_on_change(my_key):
    state = st.session_state[my_key]
    for index, updates in state["edited_rows"].items():
        st.session_state["findf"].loc[st.session_state["findf"].index == index, "Reviewed"] = True
        if 'tool' in updates:
            if updates['tool'] == "Table of Contents":
                curr_level = st.session_state["findf"].loc[st.session_state["findf"].index == index, "level"]
                if curr_level[index] == "N/A":
                    st.session_state["findf"].loc[st.session_state["findf"].index == index, "level"] = "1"
            if updates['tool'] == "Direct Copy" or updates['tool'] == "Text Only":
                curr_level = st.session_state["findf"].loc[st.session_state["findf"].index == index, "level"]
                st.session_state["findf"].loc[st.session_state["findf"].index == index, "level"] = "N/A"
        if 'preview' in updates:
            if updates['preview'] == True:
                preview_file_df = st.session_state["findf"].loc[st.session_state["findf"].index == index, "file_name"]
                updates['preview'] = False
                preview_file = preview_file_df.loc[index]
                file_win(os.path.join(input_data_dir, preview_file))
                
        for key, value in updates.items():
            st.session_state["findf"].loc[st.session_state["findf"].index == index, key] = value
    for row in state["added_rows"]:
        st.warning("Use 'Upload' to add files")
                
    for row in state["deleted_rows"]:
        file =  st.session_state["findf"].loc[st.session_state["findf"].index == row, "file_name"]
        st.session_state["findf"] = st.session_state["findf"].drop(row)
        source_file = os.path.join(input_data_dir, file[row])
        os.remove(source_file)
 
def file_input_edit_frame(df, my_key):
    if "findf" not in st.session_state:
        st.session_state["findf"] = df
    df['tool']="Direct Copy"
    df['level']="N/A"
    df['preview']=False

    edf = st.data_editor(st.session_state["findf"], num_rows="dynamic",  on_change=in_df_on_change, args=[my_key],column_config={
            "file_name": st.column_config.TextColumn("File Name", default ='', disabled = True),
            "tool": st.column_config.SelectboxColumn("Tool", options=["Direct Copy", 
                                                                        "Table of Contents", 
                                                                        "Text Only"], default= "Direct Copy"),
             "level": st.column_config.SelectboxColumn("Level", options=["N/A", 
                                                                        "1", 
                                                                        "2",
                                                                        "3"], default= "N/A"),

            "preview": st.column_config.CheckboxColumn("Preview",  default = False)
        },
        key= my_key,
        hide_index=True
        )
    return edf

def ing_df_on_change( my_key):
    state = st.session_state[my_key]
    for index, updates in state["edited_rows"].items():
        st.session_state["fingdf"].loc[st.session_state["fingdf"].index == index, "Reviewed"] = True
        if 'preview' in updates:
            if updates['preview'] == True:
                preview_file_df = st.session_state["fingdf"].loc[st.session_state["fingdf"].index == index, "file_name"]
                updates['preview'] = False
                preview_file = preview_file_df.loc[index]
                file_win(os.path.join(ingest_data_dir, preview_file))
                
        for key, value in updates.items():
            st.session_state["fingdf"].loc[st.session_state["fingdf"].index == index, key] = value
    for row in state["added_rows"]:
        st.warning("Use 'Upload' to add files")
    for row in state["deleted_rows"]:
        file =  st.session_state["fingdf"].loc[st.session_state["fingdf"].index == row, "file_name"]
        st.session_state["fingdf"] = st.session_state["fingdf"].drop(row)
        source_file = os.path.join(ingest_data_dir, file[row])
        os.remove(source_file)
    


def file_ingest_edit_frame(df, my_key):
    if "fingdf" not in st.session_state:
        st.session_state["fingdf"] = df
    df['preview']=False

    edf = st.data_editor(st.session_state["fingdf"], num_rows="dynamic", on_change=ing_df_on_change, args=[my_key], column_config={
            "file_name": st.column_config.TextColumn("File Name", default ='', disabled = True),
            "preview": st.column_config.CheckboxColumn("Preview",  default = False)
        },
        key=my_key,
        hide_index=True
        )
    return edf

def process_files(files,actions, levels):
    for i, file in enumerate(files):
        if file != '': #do nothing if no file name specified
            source_file = os.path.join(input_data_dir, file)
            if actions[i] == 'Direct Copy':
                target_file = os.path.join(ingest_data_dir, file)
                shutil.copyfile(source_file,target_file)
            elif actions[i] == 'Table of Contents':
                TOC_level = 1
                if levels[i] != "N/A":
                    TOC_level = int(levels[i])
                split_pdf_by_toc(source_file, ingest_data_dir,TOC_level)
            elif actions[i] == 'Text Only':
                copy_pdf_text(source_file, ingest_data_dir)
   
    st.success("Processing Complete")

#page layout starts here

col1, col2 = st.columns([6,4])

with col1:
    st.header("RFP/RFI Source Files")
    col1A, col1B, col1C, col1D = st.columns([1,2,2,4])
    with col1A:
        if st.button("Upload"):
            file_win("", "File")
    with col1B:
        if st.button("Refresh Source File List"):
            streamlit_js_eval(js_expressions="parent.window.location.reload()")
    with col1C:       
        if st.button("Process Selected Files"):
            files = st.session_state["findf"]['file_name']
            actions = st.session_state["findf"]['tool']
            levels = st.session_state["findf"]['level']
            process_files(files,actions, levels)
    files_in= file_input_edit_frame(show_files(input_data_dir),"file_in_df")

       
with col2:
    st.header("Files for AI Ingestion")
    col2A, col2B = st.columns([2,2])
    with col2A:
        if st.button("Refresh Ingest File List"):
            streamlit_js_eval(js_expressions="parent.window.location.reload()")
    files_ingest= file_ingest_edit_frame(show_files(ingest_data_dir),"file_ingest_df")





