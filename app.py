import os, io, re, zipfile, shutil, tempfile, traceback, json, time
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
        width: 100%;
        border-radius: 8px;
        padding: 0.75rem;
        font-weight: 600;
    }
    .ratio-box {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #4a90e2;
        margin: 1rem 0;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
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
</style>
""", unsafe_allow_html=True)

# ------------------- HEADER -------------------
st.markdown("""
<div class="main-header">
    <h1>🎓 LFJC PAPER PROCESSING SYSTEM</h1>
    <p>Professional Answer Sheet Processing with Google Drive Integration</p>
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

def natural_sort_key(s):
    """EXACT SAME as your Colab"""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

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
    
    # If no pattern matches, assume it's already an ID
    return url

def upload_to_drive_via_api(pdf_data: bytes, filename: str, access_token: str, folder_id: str) -> dict:
    """
    Upload PDF to Google Drive using REST API
    Requires OAuth2 access token
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    
    # First, create metadata
    metadata = {
        'name': filename,
        'parents': [folder_id]
    }
    
    # Prepare multipart upload
    files = {
        'metadata': ('metadata', json.dumps(metadata), 'application/json'),
        'file': (filename, pdf_data, 'application/pdf')
    }
    
    try:
        response = requests.post(
            'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart',
            headers=headers,
            files=files
        )
        
        if response.status_code == 200:
            return {
                'success': True,
                'file_id': response.json().get('id'),
                'webViewLink': response.json().get('webViewLink')
            }
        else:
            return {
                'success': False,
                'error': f"API Error {response.status_code}: {response.text}"
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def upload_to_drive_simple(pdf_data: bytes, filename: str, folder_id: str, api_method: str = "instructions") -> dict:
    """
    Multiple methods to handle Google Drive upload
    """
    # Clean folder ID (extract from URL if needed)
    clean_folder_id = get_folder_id_from_url(folder_id)
    
    if api_method == "instructions":
        # Method 1: Provide instructions for manual upload
        drive_url = f"https://drive.google.com/drive/folders/{clean_folder_id}"
        
        return {
            'success': True,
            'method': 'instructions',
            'message': f'📁 **Manual Upload Required**\n\n1. **Open your Drive folder:** [Click here]({drive_url})\n2. **Download the PDF** from below\n3. **Upload** it to your Drive folder\n\n✅ Folder ID: `{clean_folder_id}`',
            'drive_url': drive_url
        }
    
    elif api_method == "web_upload":
        # Method 2: Try using Google Drive web interface (experimental)
        drive_url = f"https://drive.google.com/drive/folders/{clean_folder_id}"
        
        # Create a download link that user can then upload
        b64_pdf = base64.b64encode(pdf_data).decode()
        download_link = f'<a href="data:application/pdf;base64,{b64_pdf}" download="{filename}">Download PDF</a>'
        
        return {
            'success': True,
            'method': 'web_upload',
            'message': f'📤 **Two-Step Upload**\n\n1. {download_link} (right-click → Save As)\n2. Go to [your Drive folder]({drive_url}) and upload the file',
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
        ratio_option1 = st.selectbox("Ratio 1", options=[f"1/{i}" for i in range(5, 21)] + ["Custom"])
        if ratio_option1 == "Custom":
            ratio_val1 = st.number_input("Custom 1", value=0.1, min_value=0.0, max_value=1.0, step=0.01)
        else:
            ratio_val1 = 1/float(ratio_option1.split("/")[1])
    
    col1, col2 = st.columns(2)
    with col1:
        strip_q2 = st.text_input("Q nos 2", "")
    with col2:
        ratio_option2 = st.selectbox("Ratio 2", options=[f"1/{i}" for i in range(5, 21)] + ["Custom"])
        if ratio_option2 == "Custom":
            ratio_val2 = st.number_input("Custom 2", value=0.1, min_value=0.0, max_value=1.0, step=0.01)
        else:
            ratio_val2 = 1/float(ratio_option2.split("/")[1])
    
    col1, col2 = st.columns(2)
    with col1:
        strip_q3 = st.text_input("Q nos 3", "")
    with col2:
        ratio_option3 = st.selectbox("Ratio 3", options=[f"1/{i}" for i in range(5, 21)] + ["Custom"])
        if ratio_option3 == "Custom":
            ratio_val3 = st.number_input("Custom 3", value=0.1, min_value=0.0, max_value=1.0, step=0.01)
        else:
            ratio_val3 = 1/float(ratio_option3.split("/")[1])
    
    st.markdown("---")
    st.markdown("### 🔢 NUMBERING")
    multi_numbering_input = st.text_input("Numbering Ranges", "")
    skip_numbering_input = st.text_input("Skip Images", "")
    
    st.markdown("---")
    st.markdown("### ☁️ GOOGLE DRIVE UPLOAD")
    
    # Your default Google Drive folder (HARDCODE YOUR FOLDER ID HERE)
    DEFAULT_DRIVE_FOLDER = "1bTHTX8OAE4XIDZOHCyFKw-YCbQ-R_JGD"  # ⬅️ REPLACE WITH YOUR FOLDER ID
    
    drive_folder_input = st.text_input(
        "Google Drive Folder ID or URL",
        value=DEFAULT_DRIVE_FOLDER,
        help="Enter folder ID or full Google Drive URL"
    )
    
    enable_drive_upload = st.checkbox("Upload to Google Drive", value=True)
    
    upload_method = st.radio(
        "Upload Method",
        options=["instructions", "web_upload"],
        format_func=lambda x: {
            "instructions": "📋 Manual Upload Instructions",
            "web_upload": "🌐 Two-Step Web Upload"
        }[x],
        help="Choose how to handle Google Drive upload"
    )
    
    # Advanced options (collapsed by default)
    with st.expander("⚙️ Advanced Drive Options"):
        use_api_token = st.checkbox("Use API Token (Advanced)", value=False)
        if use_api_token:
            api_token = st.text_input("Access Token", type="password", 
                                     help="OAuth2 access token for direct upload")
            if api_token:
                st.info("⚠️ Token will be used for direct API upload")

# ------------------- MAIN AREA -------------------
st.markdown("### 📁 UPLOAD IMAGES")

uploaded_files = st.file_uploader(
    "Select answer sheet images",
    type=['png', 'jpg', 'jpeg'],
    accept_multiple_files=True
)

if 'all_images' not in st.session_state:
    st.session_state.all_images = []

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

# Show uploaded images count
if st.session_state.all_images:
    st.info(f"📊 **{len(st.session_state.all_images)}** images ready for processing")

# ------------------- HELPER FUNCTIONS -------------------
def get_strip_mapping():
    mapping = {}
    if strip_q1:
        for q in parse_qnos(strip_q1):
            mapping[q] = ratio_val1
    if strip_q2:
        for q in parse_qnos(strip_q2):
            mapping[q] = ratio_val2
    if strip_q3:
        for q in parse_qnos(strip_q3):
            mapping[q] = ratio_val3
    return mapping

def load_font_with_size(size):
    try:
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "arial.ttf",
        ]
        for font_path in font_paths:
            try:
                return ImageFont.truetype(font_path, size)
            except:
                continue
        return ImageFont.load_default()
    except:
        return ImageFont.load_default()

# ------------------- PDF GENERATION (KEEP EXACT SAME) -------------------
def create_pdf(images):
    try:
        A4_WIDTH, A4_HEIGHT = int(8.27 * 300), int(11.69 * 300)
        TOP_MARGIN_FIRST_PAGE, TOP_MARGIN_SUBSEQUENT_PAGES = 125, 110
        BOTTOM_MARGIN = 105
        LEFT_MARGIN, RIGHT_MARGIN = 0, 0
        GAP_BETWEEN_IMAGES = 20
        OVERLAP_PIXELS = 25
        WATERMARK_TEXT = "LFJC"
        WATERMARK_OPACITY = int(255 * 0.20)
        WATERMARK_ANGLE = 45

        pdf_pages = []
        
        header_font = load_font_with_size(60)
        subheader_font = load_font_with_size(45)
        question_font = load_font_with_size(40)
        page_number_font = load_font_with_size(30)
        watermark_font = load_font_with_size(800)

        strip_mapping = get_strip_mapping()
        numbering_map = parse_multi_numbering(multi_numbering_input)
        skip_list = parse_skip_images(skip_numbering_input)

        current_page = Image.new('RGB', (A4_WIDTH, A4_HEIGHT), (255, 255, 255))
        y_offset = TOP_MARGIN_FIRST_PAGE

        draw_header = ImageDraw.Draw(current_page)
        college_name = "LITTLE FLOWER JUNIOR COLLEGE, UPPAL, HYD-39"
        
        try:
            bbox = draw_header.textbbox((0, 0), college_name, font=header_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            draw_header.text(((A4_WIDTH - text_width) // 2, y_offset), 
                           college_name, fill="black", font=header_font)
            y_offset += text_height + 10
        except:
            draw_header.text((A4_WIDTH // 4, y_offset), college_name, 
                           fill="black", font=header_font)
            y_offset += 80

        combined_header = f"{exam_type}   {exam_date}"
        try:
            bbox = draw_header.textbbox((0, 0), combined_header, font=subheader_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            draw_header.text(((A4_WIDTH - text_width) // 2, y_offset), 
                           combined_header, fill="black", font=subheader_font)
            y_offset += text_height + 40
        except:
            draw_header.text((A4_WIDTH // 3, y_offset), combined_header, 
                           fill="black", font=subheader_font)
            y_offset += 60

        image_index = 1
        question_number_counter = 0

        for img_info in images:
            image_index += 0
            
            question_number_to_display = None
            if image_index in numbering_map:
                question_number_to_display = numbering_map[image_index]
            elif image_index not in skip_list:
                question_number_counter += 1
                question_number_to_display = question_number_counter
            else:
                continue
            
            try:
                img = Image.open(io.BytesIO(img_info['bytes'])).convert('RGB')
                img = enhance_image_opencv(img)
                
                # SCALE WITH 70% FACTOR - FIXED LINE
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
                        try:
                            bbox = draw_img.textbbox((0, 0), f"{question_number_to_display}.", 
                                                    font=question_font)
                            text_width_q = bbox[2] - bbox[0]
                            text_height_q = bbox[3] - bbox[1]
                            text_x = (strip_width - text_width_q - 10) if fraction is not None else 10
                            draw_img.text((text_x, 10), f"{question_number_to_display}.", 
                                        font=question_font, fill="black")
                        except:
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

        for i, page in enumerate(pdf_pages):
            watermark_img = Image.new('RGBA', (A4_WIDTH, A4_HEIGHT), (0, 0, 0, 0))
            draw_wm = ImageDraw.Draw(watermark_img)
            
            try:
                bbox = draw_wm.textbbox((0, 0), WATERMARK_TEXT, font=watermark_font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                text_temp = Image.new('RGBA', (text_width, text_height), (0, 0, 0, 0))
                draw_temp = ImageDraw.Draw(text_temp)
                draw_temp.text((-bbox[0], -bbox[1]), WATERMARK_TEXT, 
                             font=watermark_font, fill=(0, 0, 0, WATERMARK_OPACITY))
                
                rotated_text = text_temp.rotate(WATERMARK_ANGLE, expand=1)
                rotated_width, rotated_height = rotated_text.size
                
                paste_x = (A4_WIDTH - rotated_width) // 2
                paste_y = (A4_HEIGHT - rotated_height) // 2
                
                page.paste(rotated_text, (paste_x, paste_y), rotated_text)
            except:
                draw_page = ImageDraw.Draw(page)
                draw_page.text((A4_WIDTH//3, A4_HEIGHT//2), WATERMARK_TEXT, 
                             fill=(200, 200, 200, 100), font=watermark_font)

            if i > 0:
                try:
                    draw_page_num = ImageDraw.Draw(page)
                    page_number_text = str(i + 1)
                    bbox_pn = draw_page_num.textbbox((0, 0), page_number_text, font=page_number_font)
                    text_width_pn = bbox_pn[2] - bbox_pn[0]
                    text_height_pn = bbox_pn[3] - bbox_pn[1]
                    page_num_x = (A4_WIDTH - text_width_pn) // 2
                    page_num_y = A4_HEIGHT - BOTTOM_MARGIN + (BOTTOM_MARGIN - text_height_pn) // 2 - 20
                    draw_page_num.text((page_num_x, page_num_y), page_number_text, 
                                     font=page_number_font, fill="black")
                except:
                    draw_page_num = ImageDraw.Draw(page)
                    draw_page_num.text((A4_WIDTH//2, A4_HEIGHT - 50), str(i + 1), 
                                     fill="black", font=page_number_font)

        pdf_buffer = io.BytesIO()
        pdf_pages[0].save(pdf_buffer, format='PDF', save_all=True, 
                         append_images=pdf_pages[1:], resolution=300.0)
        pdf_buffer.seek(0)
        
        return pdf_buffer.getvalue()

    except Exception as e:
        st.error(f"PDF Creation Error: {str(e)}")
        traceback.print_exc()
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
                # Generate filename
                filename = f"{exam_type.replace(' ', '_')}_{exam_date.replace(' ', '_')}.pdf"
                
                # Display success message
                st.success("✅ PDF created successfully!")
                
                # Create two columns for download and Drive options
                col1, col2 = st.columns(2)
                
                with col1:
                    # Download button
                    st.download_button(
                        label="📥 DOWNLOAD PDF",
                        data=pdf_data,
                        file_name=filename,
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )
                
                with col2:
                    # Save locally button
                    if st.button("💾 Save Locally", use_container_width=True):
                        os.makedirs("output_pdfs", exist_ok=True)
                        with open(f"output_pdfs/{filename}", "wb") as f:
                            f.write(pdf_data)
                        st.success(f"✅ Saved locally as `output_pdfs/{filename}`")
                
                # Google Drive Upload Section
                st.markdown("---")
                st.markdown("### ☁️ GOOGLE DRIVE UPLOAD")
                
                if enable_drive_upload and drive_folder_input:
                    with st.spinner("Preparing Google Drive upload..."):
                        # Get folder ID
                        folder_id = get_folder_id_from_url(drive_folder_input)
                        
                        # Handle API token if provided
                        if use_api_token and 'api_token' in locals():
                            # Direct API upload
                            result = upload_to_drive_via_api(
                                pdf_data, filename, api_token, folder_id
                            )
                        else:
                            # Simple upload methods
                            result = upload_to_drive_simple(
                                pdf_data, filename, folder_id, upload_method
                            )
                        
                        # Display results
                        if result.get('success'):
                            st.markdown(f'<div class="drive-success">{result["message"]}</div>', 
                                      unsafe_allow_html=True)
                            
                            # If we have a direct link, show it
                            if 'webViewLink' in result:
                                st.markdown(f"**Direct Link:** [Open PDF]({result['webViewLink']})")
                            elif 'drive_url' in result:
                                st.markdown(f"**Drive Folder:** [Open Folder]({result['drive_url']})")
                            
                            # QR code for mobile access (optional)
                            if st.checkbox("Show QR code for mobile access"):
                                import qrcode
                                qr = qrcode.make(result.get('drive_url', ''))
                                qr_bytes = io.BytesIO()
                                qr.save(qr_bytes, format='PNG')
                                st.image(qr_bytes, caption="Scan to open Drive folder", width=200)
                        else:
                            st.markdown(f'<div class="drive-error">❌ Upload failed: {result.get("error", "Unknown error")}</div>', 
                                      unsafe_allow_html=True)
                
                # PDF Preview
                with st.expander("🔍 PDF Preview (First Page)"):
                    # Convert first page to image for preview
                    try:
                        # Save first page as image
                        pdf_pages = Image.open(io.BytesIO(pdf_data))
                        pdf_pages.seek(0)  # First page
                        preview_img = pdf_pages.copy()
                        preview_img.thumbnail((800, 800))
                        st.image(preview_img, caption="First Page Preview", use_column_width=True)
                    except:
                        st.info("Preview not available")
                
            else:
                st.error("❌ Failed to create PDF")
