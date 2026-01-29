import os, io, re, zipfile, shutil, tempfile, traceback, json, time, sys
import warnings
warnings.filterwarnings('ignore')
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2
import streamlit as st
import base64
from pathlib import Path
import requests
from typing import Optional

# ------------------- PAGE CONFIG -------------------
st.set_page_config(
    page_title="LFJC Paper Processor",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------- CUSTOM CSS -------------------
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    .stButton > button {
        border-radius: 8px;
        padding: 0.75rem;
        font-weight: 600;
    }
    .drive-success {
        background: #d4edda;
        color: #155724;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .drive-error {
        background: #f8d7da;
        color: #721c24;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    @media (max-width: 768px) {
        .main-header {
            padding: 1rem;
            font-size: 0.9rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# ------------------- HEADER -------------------
st.markdown("""
<div class="main-header">
    <h1>🎓 LFJC PAPER PROCESSING SYSTEM</h1>
    <p>Professional Answer Sheet Processing with Google Drive Integration</p>
    <small>Deployed via GitHub | Streamlit Cloud</small>
</div>
""", unsafe_allow_html=True)

# ------------------- EXACT FUNCTIONS FROM YOUR COLAB CODE -------------------
def enhance_image_opencv(pil_img):
    """EXACT SAME as your Colab"""
    img_cv = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    thresh = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 29, 17)
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(thresh, -1, kernel)
    return Image.fromarray(cv2.cvtColor(sharpened, cv2.COLOR_GRAY2RGB))

def parse_qnos(qnos_str):
    """EXACT SAME as your Colab"""
    q_list = []
    for part in qnos_str.split(','):
        part = part.strip()
        if '-' in part:
            start, end = map(int, part.split('-'))
            q_list.extend(range(start, end + 1))
        elif part:
            q_list.append(int(part))
    return q_list

def parse_multi_numbering(input_str):
    """EXACT SAME as your Colab"""
    numbering_map = {}
    for part in input_str.split(','):
        part = part.strip()
        if ':' in part:
            img_range, start_num = part.split(':')
            try:
                start_num = int(start_num)
            except ValueError:
                continue
            if '-' in img_range:
                start_idx, end_idx = map(int, img_range.split('-'))
                for i, idx in enumerate(range(start_idx, end_idx + 1)):
                    numbering_map[idx] = start_num + i
            else:
                idx = int(img_range)
                numbering_map[idx] = start_num
    return numbering_map

def parse_skip_images(skip_str):
    """EXACT SAME as your Colab"""
    skip_list = []
    for part in skip_str.split(','):
        part = part.strip()
        if '-' in part:
            start, end = map(int, part.split('-'))
            skip_list.extend(range(start, end + 1))
        elif part:
            skip_list.append(int(part))
    return skip_list

def sanitize_filename(name):
    """EXACT SAME as your Colab"""
    cleaned_name = re.sub(r'[^À-῿Ⰰ-퟿豈-﷏\uFDF0-\uFFFD\w\s.-]', '_', name)
    cleaned_name = re.sub(r'\s+', '_', cleaned_name)
    cleaned_name = cleaned_name.strip('_')
    if not cleaned_name:
        return "untitled"
    return cleaned_name

# ------------------- GOOGLE DRIVE FUNCTIONS -------------------
def get_folder_id_from_url(url: str) -> str:
    """Extract folder ID from Google Drive URL"""
    patterns = [
        r'drive\.google\.com/drive/folders/([a-zA-Z0-9_-]+)',
        r'/folders/([a-zA-Z0-9_-]+)',
        r'id=([a-zA-Z0-9_-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return url

def upload_to_drive_simple(pdf_data: bytes, filename: str, folder_id: str, api_method: str = "instructions") -> dict:
    """Multiple methods to handle Google Drive upload"""
    clean_folder_id = get_folder_id_from_url(folder_id)
    
    if api_method == "instructions":
        drive_url = f"https://drive.google.com/drive/folders/{clean_folder_id}"
        
        return {
            'success': True,
            'method': 'instructions',
            'message': f'📁 **Manual Upload Required**\n\n1. **Open your Drive folder:** [Click here]({drive_url})\n2. **Download the PDF** from below\n3. **Upload** it to your Drive folder\n\n✅ Folder ID: `{clean_folder_id}`',
            'drive_url': drive_url
        }
    
    return {
        'success': False,
        'error': 'Invalid upload method'
    }

# ------------------- SIDEBAR -------------------
with st.sidebar:
    st.markdown("### 📋 EXAM DETAILS")
    exam_type = st.text_input("Exam Type", "")
    exam_date = st.text_input("Exam Date (DD-MM-YYYY)", "")
    
    st.markdown("---")
    st.markdown("### ✂️ STRIP SETTINGS")
    
    col1, col2 = st.columns(2)
    with col1:
        strip_q1 = st.text_input("Q nos 1", "")
    with col2:
        ratio_option1 = st.selectbox("Ratio 1", options=[f"1/{i}" for i in range(5, 21)] + ["Custom"], key="ratio1")
        if ratio_option1 == "Custom":
            ratio_val1 = st.number_input("Custom 1", value=0.1, min_value=0.0, max_value=1.0, step=0.01, key="custom1")
        else:
            ratio_val1 = 1/float(ratio_option1.split("/")[1])
    
    col1, col2 = st.columns(2)
    with col1:
        strip_q2 = st.text_input("Q nos 2", "")
    with col2:
        ratio_option2 = st.selectbox("Ratio 2", options=[f"1/{i}" for i in range(5, 21)] + ["Custom"], key="ratio2")
        if ratio_option2 == "Custom":
            ratio_val2 = st.number_input("Custom 2", value=0.1, min_value=0.0, max_value=1.0, step=0.01, key="custom2")
        else:
            ratio_val2 = 1/float(ratio_option2.split("/")[1])
    
    col1, col2 = st.columns(2)
    with col1:
        strip_q3 = st.text_input("Q nos 3", "")
    with col2:
        ratio_option3 = st.selectbox("Ratio 3", options=[f"1/{i}" for i in range(5, 21)] + ["Custom"], key="ratio3")
        if ratio_option3 == "Custom":
            ratio_val3 = st.number_input("Custom 3", value=0.1, min_value=0.0, max_value=1.0, step=0.01, key="custom3")
        else:
            ratio_val3 = 1/float(ratio_option3.split("/")[1])
    
    st.markdown("---")
    st.markdown("### 🔢 NUMBERING")
    multi_numbering_input = st.text_input("Numbering Ranges", "")
    skip_numbering_input = st.text_input("Skip Images", "")
    
    st.markdown("---")
    st.markdown("### ☁️ GOOGLE DRIVE UPLOAD")
    
    # Get Drive Folder ID from environment variable or use default
    DEFAULT_DRIVE_FOLDER = os.environ.get("DRIVE_FOLDER_ID", "YOUR_FOLDER_ID_HERE")
    
    drive_folder_input = st.text_input(
        "Google Drive Folder ID or URL",
        value=DEFAULT_DRIVE_FOLDER,
        help="Enter folder ID or full Google Drive URL"
    )
    
    enable_drive_upload = st.checkbox("Upload to Google Drive", value=True)

# ------------------- SESSION STATE -------------------
if 'all_images' not in st.session_state:
    st.session_state.all_images = []

# ------------------- MAIN AREA -------------------
st.markdown("### 📁 UPLOAD IMAGES")

uploaded_files = st.file_uploader(
    "Select answer sheet images",
    type=['png', 'jpg', 'jpeg'],
    accept_multiple_files=True
)

if uploaded_files:
    if st.button("📥 Upload Images", use_container_width=True):
        st.session_state.all_images = []
        for uploaded_file in uploaded_files:
            st.session_state.all_images.append({
                'name': uploaded_file.name,
                'bytes': uploaded_file.read()
            })
        st.success(f"✅ Uploaded {len(uploaded_files)} images")
        st.rerun()

# ------------------- PDF GENERATION -------------------
def create_pdf(images):
    try:
        A4_WIDTH, A4_HEIGHT = int(8.27 * 300), int(11.69 * 300)
        TOP_MARGIN_FIRST_PAGE, TOP_MARGIN_SUBSEQUENT_PAGES = 125, 110
        BOTTOM_MARGIN = 105
        LEFT_MARGIN, RIGHT_MARGIN = 0, 0
        GAP_BETWEEN_IMAGES = 20
        OVERLAP_PIXELS = 25
        WATERMARK_TEXT = "LFJC"
        
        pdf_pages = []
        current_page = Image.new('RGB', (A4_WIDTH, A4_HEIGHT), (255, 255, 255))
        y_offset = TOP_MARGIN_FIRST_PAGE

        draw_header = ImageDraw.Draw(current_page)
        college_name = "LITTLE FLOWER JUNIOR COLLEGE, UPPAL, HYD-39"
        
        # Load default font
        try:
            font = ImageFont.load_default()
            header_font = font
            subheader_font = font
            question_font = font
            page_number_font = font
        except:
            header_font = ImageFont.load_default()
            subheader_font = ImageFont.load_default()
            question_font = ImageFont.load_default()
            page_number_font = ImageFont.load_default()

        # Draw header
        draw_header.text((100, y_offset), college_name, fill="black", font=header_font)
        y_offset += 80
        
        combined_header = f"{exam_type}   {exam_date}"
        draw_header.text((100, y_offset), combined_header, fill="black", font=subheader_font)
        y_offset += 100

        image_index = 1
        question_number_counter = 0
        
        # Get strip mapping
        strip_mapping = {}
        if strip_q1:
            for q in parse_qnos(strip_q1):
                strip_mapping[q] = ratio_val1
        if strip_q2:
            for q in parse_qnos(strip_q2):
                strip_mapping[q] = ratio_val2
        if strip_q3:
            for q in parse_qnos(strip_q3):
                strip_mapping[q] = ratio_val3
        
        numbering_map = parse_multi_numbering(multi_numbering_input)
        skip_list = parse_skip_images(skip_numbering_input)

        for img_info in images:
            question_number_to_display = None
            if image_index in numbering_map:
                question_number_to_display = numbering_map[image_index]
            elif image_index not in skip_list:
                question_number_counter += 1
                question_number_to_display = question_number_counter
            else:
                image_index += 1
                continue
            
            try:
                img = Image.open(io.BytesIO(img_info['bytes'])).convert('RGB')
                img = enhance_image_opencv(img)
                
                # Scale image
                scale = ((A4_WIDTH - LEFT_MARGIN - RIGHT_MARGIN - 20) * 0.7) / img.width
                img_scaled = img.resize((int(img.width * scale), int(img.height * scale)), Image.Resampling.LANCZOS)
                img_to_process = img_scaled
                is_first_part = True

                while img_to_process:
                    remaining_space = A4_HEIGHT - y_offset - BOTTOM_MARGIN
                    if img_to_process.height <= remaining_space:
                        img_part = img_to_process
                        img_to_process = None
                    else:
                        split_height = remaining_space + OVERLAP_PIXELS
                        img_part = img_to_process.crop((0, 0, img_to_process.width, split_height))
                        img_to_process = img_to_process.crop((0, split_height - OVERLAP_PIXELS, 
                                                             img_to_process.width, img_to_process.height))

                    draw_img = ImageDraw.Draw(img_part)

                    fraction = strip_mapping.get(question_number_to_display, None)
                    if fraction is not None:
                        strip_width = int(img_part.width * fraction)
                        draw_img.rectangle([(0, 0), (strip_width, img_part.height)], 
                                         fill=(255, 255, 255))

                    if is_first_part and question_number_to_display is not None:
                        draw_img.text((10, 10), f"{question_number_to_display}.", 
                                    font=question_font, fill="black")
                        is_first_part = False

                    current_page.paste(img_part, (LEFT_MARGIN, y_offset))
                    y_offset += img_part.height + GAP_BETWEEN_IMAGES

                    if img_to_process:
                        pdf_pages.append(current_page)
                        current_page = Image.new('RGB', (A4_WIDTH, A4_HEIGHT), (255, 255, 255))
                        y_offset = TOP_MARGIN_SUBSEQUENT_PAGES

                image_index += 1

            except Exception as e:
                continue

        pdf_pages.append(current_page)

        pdf_buffer = io.BytesIO()
        pdf_pages[0].save(pdf_buffer, format='PDF', save_all=True, 
                         append_images=pdf_pages[1:])
        pdf_buffer.seek(0)
        
        return pdf_buffer.getvalue()

    except Exception as e:
        st.error(f"PDF Creation Error: {str(e)}")
        return None

# ------------------- GENERATE BUTTON -------------------
st.markdown("---")
st.markdown("### 🚀 GENERATE OUTPUT")

if st.button("📄 GENERATE PDF", type="primary", use_container_width=True):
    if not st.session_state.all_images:
        st.error("❌ Please upload images first!")
    elif not exam_type or not exam_date:
        st.error("❌ Please enter exam details!")
    else:
        with st.spinner("Creating PDF..."):
            pdf_data = create_pdf(st.session_state.all_images)
            
            if pdf_data:
                filename = f"{exam_type.replace(' ', '_')}_{exam_date.replace(' ', '_')}.pdf"
                st.success("✅ PDF created successfully!")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.download_button(
                        label="📥 DOWNLOAD PDF",
                        data=pdf_data,
                        file_name=filename,
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )
                
                with col2:
                    if st.button("💾 Save Locally", use_container_width=True):
                        os.makedirs("output_pdfs", exist_ok=True)
                        with open(f"output_pdfs/{filename}", "wb") as f:
                            f.write(pdf_data)
                        st.success(f"✅ Saved locally as `output_pdfs/{filename}`")
                
                # Google Drive Upload
                if enable_drive_upload and drive_folder_input:
                    st.markdown("---")
                    st.markdown("### ☁️ GOOGLE DRIVE UPLOAD")
                    
                    result = upload_to_drive_simple(pdf_data, filename, drive_folder_input, "instructions")
                    
                    if result.get('success'):
                        st.markdown(f'<div class="drive-success">{result["message"]}</div>', 
                                  unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="drive-error">❌ {result.get("error")}</div>', 
                                  unsafe_allow_html=True)
            else:
                st.error("❌ Failed to create PDF")

# ------------------- FOOTER -------------------
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: gray; font-size: 0.8rem;">
    <p>LFJC Paper Processor | Deployed via GitHub + Streamlit Cloud</p>
    <p>📧 Report issues on GitHub Repository</p>
</div>
""", unsafe_allow_html=True)
