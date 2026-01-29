import os, io, re, zipfile, shutil, tempfile, traceback
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2
import streamlit as st

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
    /* Hide ALL Streamlit branding elements completely */
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    .stDeployButton {display: none !important;}
    header {visibility: hidden !important;}
    
    /* Hide the "Manage Apps" button and hamburger menu */
    .stApp > header > div > div:nth-child(2) > button,
    .stApp > header > div > div:nth-child(1) > button {
        display: none !important;
    }
    
    /* Hide Streamlit's main menu completely */
    div[data-testid="stSidebarNav"] {
        display: none !important;
    }
    
    /* Hide any remaining Streamlit elements */
    .stApp > div:nth-child(1) > div:nth-child(1) > div > div:nth-child(2) > div {
        display: none !important;
    }
    
    /* Remove Streamlit's default spacing */
    .stApp > div > div > div > div > section {
        padding-top: 0rem;
    }
    
    /* Professional styling */
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 2.5rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
        box-shadow: 0 8px 32px rgba(30, 60, 114, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.1);
        position: relative;
        overflow: hidden;
    }
    
    .main-header::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle at center, rgba(255, 255, 255, 0.1) 0%, transparent 70%);
        z-index: 0;
    }
    
    .main-header h1 {
        position: relative;
        z-index: 1;
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }
    
    .main-header p {
        position: relative;
        z-index: 1;
        font-size: 1.1rem;
        opacity: 0.9;
        margin: 0;
    }
    
    .stButton > button {
        width: 100%;
        border-radius: 10px;
        padding: 0.9rem;
        font-weight: 600;
        transition: all 0.3s ease;
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: white;
        border: none;
        font-size: 1rem;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(30, 60, 114, 0.3);
        background: linear-gradient(135deg, #2a5298 0%, #4a90e2 100%);
    }
    
    .ratio-box {
        background: linear-gradient(135deg, rgba(248, 250, 252, 0.9) 0%, rgba(233, 236, 239, 0.9) 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 4px solid #4a90e2;
        margin: 1rem 0;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    .selected-file {
        background: rgba(240, 248, 255, 0.8);
        padding: 14px;
        border-radius: 10px;
        margin: 8px 0;
        border-left: 4px solid #4a90e2;
        font-size: 0.95rem;
        font-weight: 500;
        border: 1px solid rgba(74, 144, 226, 0.1);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
    }
    
    .stSidebar .sidebar-content {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
    
    /* Professional styling */
    .section-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1e3c72;
        margin-top: 1.5rem;
        margin-bottom: 0.8rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #4a90e2;
        letter-spacing: 0.5px;
    }
    
    /* Sidebar show/hide button */
    .sidebar-toggle {
        position: fixed;
        top: 25px;
        left: 25px;
        z-index: 1000;
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: white;
        border: none;
        border-radius: 50%;
        width: 48px;
        height: 48px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 15px rgba(30, 60, 114, 0.3);
        font-size: 1.2rem;
        transition: all 0.3s ease;
    }
    
    .sidebar-toggle:hover {
        transform: scale(1.1) rotate(90deg);
        box-shadow: 0 6px 20px rgba(30, 60, 114, 0.4);
        background: linear-gradient(135deg, #2a5298 0%, #4a90e2 100%);
    }
</style>
""", unsafe_allow_html=True)

# ------------------- SESSION STATE FOR SIDEBAR -------------------
if 'sidebar_visible' not in st.session_state:
    st.session_state.sidebar_visible = True

# ------------------- SIDEBAR TOGGLE BUTTON -------------------
if not st.session_state.sidebar_visible:
    st.markdown("""
    <div class="sidebar-toggle" onclick="document.getElementById('sidebar-toggle-script').click()">
        ⚙️
    </div>
    <script>
        // Create hidden button for toggling sidebar
        const toggleBtn = document.createElement('button');
        toggleBtn.id = 'sidebar-toggle-script';
        toggleBtn.style.display = 'none';
        document.body.appendChild(toggleBtn);
        
        toggleBtn.onclick = function() {
            this.dispatchEvent(new CustomEvent('toggle-sidebar'));
        };
    </script>
    """, unsafe_allow_html=True)
    
    # Add JavaScript to handle sidebar toggle
    st.components.v1.html("""
    <script>
        const toggleBtn = document.getElementById('sidebar-toggle-script');
        toggleBtn.addEventListener('toggle-sidebar', function() {
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: 'toggle-sidebar'
            }, '*');
        });
    </script>
    """)

# ------------------- HEADER -------------------
st.markdown("""
<div class="main-header">
    <h1>🎓 LFJC PAPER PROCESSING SYSTEM</h1>
    <p>Professional Document Processing Solution | Secure • Efficient • Reliable</p>
</div>
""", unsafe_allow_html=True)

# ------------------- SESSION STATE -------------------
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = []

# ------------------- SIDEBAR -------------------
if st.session_state.sidebar_visible:
    with st.sidebar:
        # Add close button at top of sidebar
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown("### ⚙️ PROCESSING SETTINGS")
        with col2:
            if st.button("✕", help="Close settings panel", key="close_sidebar"):
                st.session_state.sidebar_visible = False
                st.rerun()
        
        st.markdown("---")
        
        st.markdown('<div class="section-header">📋 EXAM DETAILS</div>', unsafe_allow_html=True)
        exam_type = st.text_input("Exam Type", "", placeholder="e.g., Semester I - Physics")
        exam_date = st.text_input("Exam Date (DD-MM-YYYY)", "", placeholder="15-01-2024")
        
        st.markdown('<div class="section-header">📐 PAGE ALIGNMENT</div>', unsafe_allow_html=True)
        alignment = st.radio(
            "Image Alignment",
            ["Center", "Left", "Right"],
            horizontal=True,
            index=0,
            help="Position images on the page"
        )
        
        st.markdown('<div class="section-header">✂️ STRIP CROPPING SETTINGS</div>', unsafe_allow_html=True)
        
        # Strip 1
        st.markdown('<div class="ratio-box">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            strip_q1 = st.text_input("Question Range 1", "", placeholder="e.g., 1-5")
        with col2:
            ratio_option1 = st.selectbox("Ratio 1", options=[f"1/{i}" for i in range(5, 21)] + ["Custom"], key="r1")
            if ratio_option1 == "Custom":
                ratio_val1 = st.number_input("Custom Ratio 1", value=0.1, min_value=0.0, max_value=1.0, step=0.01, key="c1")
            else:
                ratio_val1 = 1/float(ratio_option1.split("/")[1])
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Strip 2
        st.markdown('<div class="ratio-box">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            strip_q2 = st.text_input("Question Range 2", "", placeholder="e.g., 6-10")
        with col2:
            ratio_option2 = st.selectbox("Ratio 2", options=[f"1/{i}" for i in range(5, 21)] + ["Custom"], key="r2")
            if ratio_option2 == "Custom":
                ratio_val2 = st.number_input("Custom Ratio 2", value=0.1, min_value=0.0, max_value=1.0, step=0.01, key="c2")
            else:
                ratio_val2 = 1/float(ratio_option2.split("/")[1])
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Strip 3
        st.markdown('<div class="ratio-box">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            strip_q3 = st.text_input("Question Range 3", "", placeholder="e.g., 11-15")
        with col2:
            ratio_option3 = st.selectbox("Ratio 3", options=[f"1/{i}" for i in range(5, 21)] + ["Custom"], key="r3")
            if ratio_option3 == "Custom":
                ratio_val3 = st.number_input("Custom Ratio 3", value=0.1, min_value=0.0, max_value=1.0, step=0.01, key="c3")
            else:
                ratio_val3 = 1/float(ratio_option3.split("/")[1])
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="section-header">🔢 NUMBERING OPTIONS</div>', unsafe_allow_html=True)
        multi_numbering_input = st.text_input("Custom Numbering Ranges", 
                                            placeholder="Format: 1-5:1, 6-10:41, 11-15:51",
                                            help="Map image ranges to custom starting numbers")
        skip_numbering_input = st.text_input("Skip Images", 
                                           placeholder="e.g., 2,4-5,7",
                                           help="Images to skip from numbering sequence")
        
        st.markdown("---")
        
        # Quick Help
        with st.expander("📖 QUICK HELP & FORMATS"):
            st.markdown("""
            **Format Examples:**
            
            **Question Ranges:**  
            `1-5, 10, 15-20`
            
            **Custom Numbering:**  
            `1-5:1, 6-10:41`  
            *(Images 1-5 start at 1, Images 6-10 start at 41)*
            
            **Skip Images:**  
            `2,4-5,7`  
            *(Skip images 2, 4, 5, and 7)*
            
            **Note:** All settings apply to the entire processing queue.
            """)
        
        st.markdown("---")
        
        # System Status
        with st.expander("📊 SYSTEM STATUS"):
            st.metric("Files in Queue", len(st.session_state.uploaded_files))
            st.metric("Batches", max([f['batch'] for f in st.session_state.uploaded_files], default=0))
        
        st.markdown("---")
        
        # Add show sidebar button at bottom
        st.markdown("*Settings panel can be reopened from the ⚙️ button*")

# Show reopen sidebar button if sidebar is hidden
else:
    st.markdown("""
    <div style='text-align: center; padding: 2.5rem; background: linear-gradient(135deg, #f8fafc 0%, #eef2f7 100%); border-radius: 12px; margin: 2rem 0; border: 1px solid rgba(74, 144, 226, 0.1);'>
        <h3 style='color: #1e3c72; margin-bottom: 1rem;'>⚙️ Settings Panel Hidden</h3>
        <p style='color: #5a6a8a; font-size: 1.05rem;'>Click the ⚙️ button in the top-left corner to reopen processing settings.</p>
        <div style='margin-top: 1.5rem; font-size: 0.9rem; color: #7b8ab8;'>
            <i>Current Queue: <strong>{}</strong> files ready for processing</i>
        </div>
    </div>
    """.format(len(st.session_state.uploaded_files)), unsafe_allow_html=True)

# ------------------- MAIN AREA -------------------
st.markdown("### 📁 DOCUMENT UPLOAD & PROCESSING")

# File uploader with batch support
uploaded_files = st.file_uploader(
    "Select answer sheet images (PNG, JPG, JPEG format)",
    type=['png', 'jpg', 'jpeg'],
    accept_multiple_files=True,
    help="Select multiple images. Each batch processes up to 10 images automatically."
)

# Batch management
if uploaded_files:
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 **ADD TO PROCESSING QUEUE**", use_container_width=True, type="primary"):
            new_files_count = 0
            for uploaded_file in uploaded_files:
                # Check if file already exists
                if not any(f['name'] == uploaded_file.name for f in st.session_state.uploaded_files):
                    st.session_state.uploaded_files.append({
                        'name': uploaded_file.name,
                        'bytes': uploaded_file.read(),
                        'batch': len(st.session_state.uploaded_files) // 10 + 1
                    })
                    new_files_count += 1
            
            if new_files_count > 0:
                st.success(f"✅ Successfully added {new_files_count} new images to processing queue")
            else:
                st.info("⚠️ All selected images are already in the processing queue")
            st.rerun()
    
    with col2:
        if st.button("🗑️ **CLEAR PROCESSING QUEUE**", use_container_width=True, type="secondary"):
            st.session_state.uploaded_files = []
            st.session_state.processed_files = []
            st.success("✅ Processing queue cleared successfully")
            st.rerun()

# Display uploaded files with batch numbers
if st.session_state.uploaded_files:
    st.markdown(f"### 📋 PROCESSING QUEUE ({len(st.session_state.uploaded_files)} images)")
    
    # Show by batches
    batches = {}
    for file_info in st.session_state.uploaded_files:
        batch_num = file_info['batch']
        if batch_num not in batches:
            batches[batch_num] = []
        batches[batch_num].append(file_info['name'])
    
    for batch_num, files in sorted(batches.items()):
        with st.expander(f"📦 **Batch {batch_num}** ({len(files)} images)", expanded=True):
            for file_name in files:
                st.markdown(f'<div class="selected-file">📄 {file_name}</div>', unsafe_allow_html=True)
            
            # Remove batch button
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button(f"Remove Batch {batch_num}", key=f"remove_batch_{batch_num}"):
                    st.session_state.uploaded_files = [f for f in st.session_state.uploaded_files if f['batch'] != batch_num]
                    st.success(f"✅ Batch {batch_num} removed from processing queue")
                    st.rerun()

# ------------------- HELPER FUNCTIONS -------------------
def enhance_image_opencv(pil_img):
    img_cv = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    thresh = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 29, 17)
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(thresh, -1, kernel)
    return Image.fromarray(cv2.cvtColor(sharpened, cv2.COLOR_GRAY2RGB))

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

def parse_qnos(qnos_str):
    q_list = []
    if not qnos_str:
        return q_list
    for part in qnos_str.split(','):
        part = part.strip()
        if '-' in part:
            start, end = map(int, part.split('-'))
            q_list.extend(range(start, end + 1))
        elif part:
            q_list.append(int(part))
    return q_list

def parse_multi_numbering(input_str):
    numbering_map = {}
    if not input_str:
        return numbering_map
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
    skip_list = []
    if not skip_str:
        return skip_list
    for part in skip_str.split(','):
        part = part.strip()
        if '-' in part:
            start, end = map(int, part.split('-'))
            skip_list.extend(range(start, end + 1))
        elif part:
            skip_list.append(int(part))
    return skip_list

def sanitize_filename(name):
    cleaned_name = re.sub(r'[^À-῿Ⰰ-퟿豈-﷏\uFDF0-\uFFFD\w\s.-]', '_', name)
    cleaned_name = re.sub(r'\s+', '_', cleaned_name)
    cleaned_name = cleaned_name.strip('_')
    if not cleaned_name:
        return "untitled"
    return cleaned_name

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

# ------------------- PDF GENERATION -------------------
def create_pdf(files):
    try:
        A4_WIDTH, A4_HEIGHT = int(8.27 * 300), int(11.69 * 300)
        TOP_MARGIN_FIRST_PAGE, TOP_MARGIN_SUBSEQUENT_PAGES = 125, 110
        BOTTOM_MARGIN = 105
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

        # Sort files naturally
        files.sort(key=lambda x: natural_sort_key(x['name']))

        for file_info in files:
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
                img = Image.open(io.BytesIO(file_info['bytes'])).convert('RGB')
                img = enhance_image_opencv(img)
                
                # Scale image based on alignment choice
                if alignment == "Center":
                    # Scale to 90% of page width for centered images
                    scale = (A4_WIDTH * 0.9) / img.width
                else:  # Left or Right alignment
                    # Use smaller scale to leave space on sides
                    SIDE_MARGIN = 50
                    scale = ((A4_WIDTH - SIDE_MARGIN) * 0.9) / img.width
                
                img_scaled = img.resize(
                    (int(img.width * scale), int(img.height * scale)), 
                    Image.Resampling.LANCZOS
                )
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
                        img_to_process = img_to_process.crop(
                            (0, split_height - OVERLAP_PIXELS, 
                             img_to_process.width, img_to_process.height)
                        )

                    draw_img = ImageDraw.Draw(img_part)

                    fraction = strip_mapping.get(question_number_to_display, None)
                    if fraction is not None:
                        strip_width = int(img_part.width * fraction)
                        draw_img.rectangle(
                            [(0, 0), (strip_width, img_part.height)], 
                            fill=(255, 255, 255)
                        )

                    if is_first_part and question_number_to_display is not None:
                        try:
                            bbox = draw_img.textbbox(
                                (0, 0), f"{question_number_to_display}.", 
                                font=question_font
                            )
                            text_width_q = bbox[2] - bbox[0]
                            text_height_q = bbox[3] - bbox[1]
                            text_x = (strip_width - text_width_q - 10) if fraction is not None else 10
                            draw_img.text(
                                (text_x, 10), f"{question_number_to_display}.", 
                                font=question_font, fill="black"
                            )
                        except:
                            draw_img.text(
                                (10, 10), f"{question_number_to_display}.", 
                                font=question_font, fill="black"
                            )
                        is_first_part = False

                    # Place image based on alignment choice
                    if alignment == "Center":
                        x_position = (A4_WIDTH - img_part.width) // 2
                    elif alignment == "Left":
                        x_position = 50  # 50px left margin
                    else:  # Right alignment
                        x_position = A4_WIDTH - img_part.width - 50  # 50px right margin
                    
                    current_page.paste(img_part, (x_position, y_offset))
                    
                    y_offset += img_part.height + GAP_BETWEEN_IMAGES

                    if img_to_process:
                        pdf_pages.append(current_page)
                        current_page = Image.new('RGB', (A4_WIDTH, A4_HEIGHT), (255, 255, 255))
                        y_offset = TOP_MARGIN_SUBSEQUENT_PAGES

                image_index += 1

            except Exception as e:
                st.error(f"Error processing {file_info['name']}: {e}")
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

# ------------------- GENERATE BUTTONS -------------------
st.markdown("---")
st.markdown("### 🚀 PROCESSING ACTIONS")

if st.session_state.uploaded_files:
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📄 **GENERATE PDF DOCUMENT**", use_container_width=True, type="primary"):
            if not exam_type or not exam_date:
                st.error("❌ Please enter exam details in the settings panel!")
                if not st.session_state.sidebar_visible:
                    st.info("📝 Click the ⚙️ button in the top-left corner to open settings panel")
            else:
                with st.spinner(f"🔨 Processing {len(st.session_state.uploaded_files)} images into PDF..."):
                    pdf_data = create_pdf(st.session_state.uploaded_files)
                    
                    if pdf_data:
                        filename = f"{sanitize_filename(exam_type)}_{sanitize_filename(exam_date)}_processed.pdf"
                        st.success(f"✅ PDF document created successfully!")
                        
                        col_d1, col_d2 = st.columns([3, 1])
                        with col_d1:
                            st.download_button(
                                label="📥 **DOWNLOAD PDF DOCUMENT**",
                                data=pdf_data,
                                file_name=filename,
                                mime="application/pdf",
                                type="primary",
                                use_container_width=True
                            )
                        with col_d2:
                            st.metric("Estimated Pages", max(1, len(pdf_data) // 50000))
                    else:
                        st.error("❌ Failed to create PDF document")
    
    with col2:
        # Create ZIP of processed images
        if st.button("🗃️ **EXPORT PROCESSED IMAGES**", use_container_width=True, type="secondary"):
            with st.spinner("🔨 Creating archive of processed images..."):
                try:
                    # Create processed images
                    temp_dir = tempfile.mkdtemp()
                    processed_files = []
                    
                    strip_mapping = get_strip_mapping()
                    numbering_map = parse_multi_numbering(multi_numbering_input)
                    skip_list = parse_skip_images(skip_numbering_input)
                    
                    image_index = 1
                    question_number_counter = 0
                    
                    for file_info in st.session_state.uploaded_files:
                        question_number_to_display = None
                        if image_index in numbering_map:
                            question_number_to_display = numbering_map[image_index]
                        elif image_index not in skip_list:
                            question_number_counter += 1
                            question_number_to_display = question_number_counter
                        
                        if question_number_to_display:
                            try:
                                img = Image.open(io.BytesIO(file_info['bytes'])).convert('RGB')
                                img = enhance_image_opencv(img)
                                
                                # Apply strip cropping
                                strip_fraction = strip_mapping.get(question_number_to_display)
                                if strip_fraction is not None and strip_fraction > 0:
                                    original_width = img.width
                                    crop_width = int(original_width * (1 - strip_fraction))
                                    img = img.crop((original_width - crop_width, 0, original_width, img.height))
                                
                                # Save processed image
                                filename = f"Q{question_number_to_display:03d}.png"
                                filepath = os.path.join(temp_dir, filename)
                                img.save(filepath, "PNG", quality=95)
                                processed_files.append(filepath)
                                
                            except Exception as e:
                                st.error(f"Error processing {file_info['name']}: {e}")
                        
                        image_index += 1
                    
                    # Create ZIP
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        for filepath in processed_files:
                            zipf.write(filepath, os.path.basename(filepath))
                    
                    zip_buffer.seek(0)
                    zip_filename = f"{sanitize_filename(exam_type)}_{sanitize_filename(exam_date)}_processed_images.zip"
                    
                    st.success(f"✅ Archive created with {len(processed_files)} processed images!")
                    
                    col_z1, col_z2 = st.columns([3, 1])
                    with col_z1:
                        st.download_button(
                            label="📥 **DOWNLOAD IMAGE ARCHIVE**",
                            data=zip_buffer,
                            file_name=zip_filename,
                            mime="application/zip",
                            type="secondary",
                            use_container_width=True
                        )
                    with col_z2:
                        st.metric("Processed Images", len(processed_files))
                    
                    # Cleanup
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    
                except Exception as e:
                    st.error(f"Archive Creation Error: {str(e)}")
    
    with col3:
        if st.button("⚙️ **OPEN SETTINGS**", use_container_width=True, type="secondary"):
            if not st.session_state.sidebar_visible:
                st.session_state.sidebar_visible = True
                st.rerun()
            else:
                st.info("📝 Settings panel is already open on the left side")
else:
    st.info("📤 Upload answer sheet images and add them to the processing queue to begin")

# ------------------- MODERN GLASS-MORPHISM FOOTER -------------------
st.markdown("""
<style>
    .footer-container-glass {
        position: relative;
        margin-top: 4rem;
        padding: 2rem;
        background: linear-gradient(135deg, 
            rgba(255, 255, 255, 0.95) 0%,
            rgba(255, 255, 255, 0.9) 100%);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        box-shadow: 
            0 8px 32px rgba(30, 60, 114, 0.1),
            inset 0 1px 0 rgba(255, 255, 255, 0.6);
        overflow: hidden;
    }
    
    .footer-bg-overlay {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(45deg, 
            transparent 0%,
            rgba(74, 144, 226, 0.03) 25%,
            rgba(42, 82, 152, 0.05) 50%,
            rgba(30, 60, 114, 0.03) 75%,
            transparent 100%);
        z-index: 0;
    }
    
    .footer-content-glass {
        position: relative;
        z-index: 1;
        text-align: center;
    }
    
    .copyright-gradient {
        font-size: 1.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, 
            #1e3c72 0%,
            #2a5298 25%,
            #4a90e2 50%,
            #2a5298 75%,
            #1e3c72 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
        letter-spacing: 1.5px;
    }
    
    .copyright-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: linear-gradient(135deg, #1e3c72, #2a5298);
        color: white;
        padding: 6px 20px;
        border-radius: 30px;
        font-weight: 600;
        font-size: 0.9rem;
        margin: 0 10px 1rem 10px;
        box-shadow: 0 4px 15px rgba(30, 60, 114, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .footer-divider-glass {
        height: 1px;
        width: 60%;
        margin: 1.5rem auto;
        background: linear-gradient(90deg, 
            transparent 0%,
            rgba(74, 144, 226, 0.3) 50%,
            transparent 100%);
    }
    
    .institution-badge {
        display: inline-flex;
        align-items: center;
        gap: 10px;
        padding: 8px 24px;
        background: rgba(255, 255, 255, 0.7);
        border-radius: 12px;
        border: 1px solid rgba(74, 144, 226, 0.2);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }
    
    .badge-icon {
        color: #4a90e2;
        font-size: 1.2rem;
    }
    
    .badge-text {
        font-size: 0.95rem;
        font-weight: 700;
        color: #1e3c72;
        letter-spacing: 0.5px;
    }
    
    .version-tag {
        display: inline-block;
        background: linear-gradient(135deg, rgba(74, 144, 226, 0.1), rgba(42, 82, 152, 0.1));
        color: #5a6a8a;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 500;
        margin-top: 1rem;
        border: 1px solid rgba(74, 144, 226, 0.1);
    }
    
    .footer-corner-accent {
        position: absolute;
        width: 120px;
        height: 120px;
        border-radius: 50%;
        background: radial-gradient(circle at center, rgba(74, 144, 226, 0.08), transparent 70%);
    }
    
    .corner-1 {
        top: -40px;
        right: -40px;
    }
    
    .corner-2 {
        bottom: -40px;
        left: -40px;
        background: radial-gradient(circle at center, rgba(30, 60, 114, 0.06), transparent 70%);
    }
</style>

<div class="footer-container-glass">
    <div class="footer-bg-overlay"></div>
    <div class="footer-corner-accent corner-1"></div>
    <div class="footer-corner-accent corner-2"></div>
    
    <div class="footer-content-glass">
        <div class="copyright-gradient">INTELLECTUAL PROPERTY PROTECTED</div>
        
        <div class="copyright-badge">
            <span>© 2024</span>
            <span>•</span>
            <span>COPYRIGHT LFJC</span>
        </div>
        
        <div class="footer-divider-glass"></div>
        
        <div class="institution-badge">
            <div class="badge-icon">⚡</div>
            <div class="badge-text">LFJC PAPER PROCESSING SYSTEM</div>
            <div class="badge-icon">📊</div>
        </div>
        
        <div class="version-tag">
            Professional Edition • v2.1.0 • Secure Processing
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# JavaScript for sidebar toggle
st.components.v1.html("""
<script>
    // Listen for messages to toggle sidebar
    window.addEventListener('message', function(event) {
        if (event.data.type === 'streamlit:setComponentValue' && event.data.value === 'toggle-sidebar') {
            // This will trigger a rerun when sidebar needs to be shown
            window.location.reload();
        }
    });
</script>
""", height=0)
