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
    .selected-file {
        background: #f0f8ff;
        padding: 8px;
        border-radius: 5px;
        margin: 5px 0;
        border-left: 3px solid #4a90e2;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ------------------- HEADER -------------------
st.markdown("""
<div class="main-header">
    <h1>🎓 LFJC PAPER PROCESSING SYSTEM</h1>
    <p>Professional Answer Sheet Processing | FREE Version</p>
</div>
""", unsafe_allow_html=True)

# ------------------- SESSION STATE -------------------
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = []

# ------------------- SIDEBAR -------------------
with st.sidebar:
    st.markdown("### 📋 EXAM DETAILS")
    exam_type = st.text_input("Exam Type", "")
    exam_date = st.text_input("Exam Date (DD-MM-YYYY)", "")
    
    st.markdown("### ✂️ STRIP SETTINGS")
    
    # Strip 1
    st.markdown('<div class="ratio-box">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        strip_q1 = st.text_input("Q nos 1", "")
    with col2:
        ratio_option1 = st.selectbox("Ratio 1", options=[f"1/{i}" for i in range(5, 21)] + ["Custom"], key="r1")
        if ratio_option1 == "Custom":
            ratio_val1 = st.number_input("Custom 1", value=0.1, min_value=0.0, max_value=1.0, step=0.01, key="c1")
        else:
            ratio_val1 = 1/float(ratio_option1.split("/")[1])
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Strip 2
    st.markdown('<div class="ratio-box">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        strip_q2 = st.text_input("Q nos 2", "")
    with col2:
        ratio_option2 = st.selectbox("Ratio 2", options=[f"1/{i}" for i in range(5, 21)] + ["Custom"], key="r2")
        if ratio_option2 == "Custom":
            ratio_val2 = st.number_input("Custom 2", value=0.1, min_value=0.0, max_value=1.0, step=0.01, key="c2")
        else:
            ratio_val2 = 1/float(ratio_option2.split("/")[1])
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Strip 3
    st.markdown('<div class="ratio-box">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        strip_q3 = st.text_input("Q nos 3", "")
    with col2:
        ratio_option3 = st.selectbox("Ratio 3", options=[f"1/{i}" for i in range(5, 21)] + ["Custom"], key="r3")
        if ratio_option3 == "Custom":
            ratio_val3 = st.number_input("Custom 3", value=0.1, min_value=0.0, max_value=1.0, step=0.01, key="c3")
        else:
            ratio_val3 = 1/float(ratio_option3.split("/")[1])
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("### 🔢 NUMBERING OPTIONS")
    multi_numbering_input = st.text_input("Numbering Ranges", placeholder="1-5:1, 6-10:41, 11-15:51")
    skip_numbering_input = st.text_input("Skip Images", placeholder="2,4-5,7")

# ------------------- MAIN AREA -------------------
st.markdown("### 📁 UPLOAD ANSWER SHEETS")

# File uploader with batch support
uploaded_files = st.file_uploader(
    "Choose answer sheet images",
    type=['png', 'jpg', 'jpeg'],
    accept_multiple_files=True,
    help="Select multiple images (max 200MB total)"
)

# Batch management
if uploaded_files:
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 **ADD TO BATCH**", use_container_width=True):
            for uploaded_file in uploaded_files:
                # Check if file already exists
                if not any(f['name'] == uploaded_file.name for f in st.session_state.uploaded_files):
                    st.session_state.uploaded_files.append({
                        'name': uploaded_file.name,
                        'bytes': uploaded_file.read(),
                        'batch': len(st.session_state.uploaded_files) // 10 + 1
                    })
            st.success(f"✅ Added {len(uploaded_files)} images to batch")
            st.rerun()
    
    with col2:
        if st.button("🗑️ **CLEAR ALL**", use_container_width=True):
            st.session_state.uploaded_files = []
            st.session_state.processed_files = []
            st.rerun()

# Display uploaded files with batch numbers
if st.session_state.uploaded_files:
    st.markdown(f"### 📋 SELECTED FILES ({len(st.session_state.uploaded_files)} images)")
    
    # Show by batches
    batches = {}
    for file_info in st.session_state.uploaded_files:
        batch_num = file_info['batch']
        if batch_num not in batches:
            batches[batch_num] = []
        batches[batch_num].append(file_info['name'])
    
    for batch_num, files in sorted(batches.items()):
        with st.expander(f"📦 **Batch {batch_num}** ({len(files)} images)"):
            for file_name in files:
                st.markdown(f'<div class="selected-file">📄 {file_name}</div>', unsafe_allow_html=True)
            
            # Remove batch button
            if st.button(f"❌ Remove Batch {batch_num}", key=f"remove_batch_{batch_num}"):
                st.session_state.uploaded_files = [f for f in st.session_state.uploaded_files if f['batch'] != batch_num]
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
                
                # Scale with 70% factor
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
st.markdown("### 🚀 GENERATE OUTPUT")

if st.session_state.uploaded_files:
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📄 **GENERATE PDF**", type="primary", use_container_width=True):
            if not exam_type or not exam_date:
                st.error("❌ Please enter exam details!")
            else:
                with st.spinner(f"Processing {len(st.session_state.uploaded_files)} images..."):
                    pdf_data = create_pdf(st.session_state.uploaded_files)
                    
                    if pdf_data:
                        filename = f"{sanitize_filename(exam_type)}_{sanitize_filename(exam_date)}.pdf"
                        st.success(f"✅ PDF created with {len(st.session_state.uploaded_files)} images!")
                        st.download_button(
                            label="📥 DOWNLOAD PDF",
                            data=pdf_data,
                            file_name=filename,
                            mime="application/pdf",
                            type="primary"
                        )
                    else:
                        st.error("❌ Failed to create PDF")
    
    with col2:
        # Create ZIP of processed images
        if st.button("🗃️ **DOWNLOAD ZIP**", type="secondary", use_container_width=True):
            with st.spinner("Creating ZIP file..."):
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
                                filename = f"{question_number_to_display}.png"
                                filepath = os.path.join(temp_dir, filename)
                                img.save(filepath)
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
                    zip_filename = f"{sanitize_filename(exam_type)}_{sanitize_filename(exam_date)}.zip"
                    
                    st.success(f"✅ ZIP created with {len(processed_files)} images!")
                    st.download_button(
                        label="📥 DOWNLOAD ZIP",
                        data=zip_buffer,
                        file_name=zip_filename,
                        mime="application/zip"
                    )
                    
                    # Cleanup
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    
                except Exception as e:
                    st.error(f"ZIP Creation Error: {str(e)}")
    
    with col3:
        if st.button("📦 **GENERATE BOTH**", type="primary", use_container_width=True):
            st.info("Please use PDF or ZIP button individually for now")

# ------------------- FOOTER -------------------
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p style='margin: 0;'>📚 <strong>Little Flower Junior College</strong> | Paper Processing System</p>
    <p style='margin: 0; font-size: 0.9rem;'>Uppal, Hyderabad - 39 | FREE Version</p>
</div>
""", unsafe_allow_html=True)
