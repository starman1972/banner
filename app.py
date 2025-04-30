import streamlit as st
from PIL import Image
from io import BytesIO
import os
import pandas as pd
import requests
from dotenv import load_dotenv

# set_page_config gleich nach den Imports!
st.set_page_config(
    page_title="Wine Banner Generator",
    layout="wide",
    page_icon="🍷"
)

from logic.prompt_engine import build_autonomous_prompt
from logic.generation import generate_banner_prompt_gpt4, generate_dalle_image

try:
    from streamlit_cropper import st_cropper
    cropper_available = True
except ImportError:
    cropper_available = False

# Robust CSV loader: handles UTF-8 BOM and whitespace, keeps SKU as string
@st.cache_data
def load_sku_csv(path):
    df = pd.read_csv(
        path, sep=";", encoding="utf-8-sig", dtype={"sku": str}
    )
    df.columns = [col.strip() for col in df.columns]
    df["sku"] = df["sku"].astype(str).str.strip()
    return df

CSV_FILENAME = "banner_bilder_v1.csv"
if os.path.exists(CSV_FILENAME):
    df_skus = load_sku_csv(CSV_FILENAME)
else:
    df_skus = pd.DataFrame(columns=["sku","bild","hintergrundbild"])

load_dotenv()
import openai
openai.api_key = os.getenv("OPENAI_API_KEY")

st.markdown("""
    <style>
    .stImage img { max-height: 550px !important; object-fit: contain !important; }
    </style>
""", unsafe_allow_html=True)

def reset_generation():
    st.session_state['gpt_prompt'] = None
    st.session_state['ai_banner_img'] = None
    st.session_state['img_loading'] = False

# ----------- HERO-Bereich -----------
st.markdown("""
<div style="
    background: linear-gradient(90deg, #fffbe6 10%, #ffe2e2 100%);
    border-radius: 1.5em;
    padding: 3.5em 2em 2em 2em;
    box-shadow: 0 4px 24px #22001208;
    text-align: center;
    margin-bottom: 2em;
">
  <div style="margin-bottom:2em;">
    <span style="font-size:60px; line-height: 1">🍷</span>
  </div>
  <h1 style="font-family:'Montserrat',sans-serif;font-weight:800;font-size:2.7em;letter-spacing:-1px;color:#661a33;">
    Wine Banner Generator
  </h1>
  <div style="margin: 0.7em auto 1.8em auto; max-width:600px; font-size:1.22em; color:#4a0033; font-weight: 500;">
    Generate professional, custom banners that truly match your wine’s identity —<br>
    simply upload your bottle or enter a SKU and let AI do the magic.<br>
    <span style="color:#a04142;font-weight:700;">No design skills needed!</span>
  </div>
  <div style="
      display: inline-block;
      background: #fff;
      border-radius: 2em;
      padding: 0.5em 2em;
      box-shadow: 0 1px 5px #a0414213;
      font-size: 1.09em;
      color: #932238;
      font-weight: 700;
      margin-bottom: 2.2em;
      ">
    Start by uploading your bottle image <b>or</b> enter a product SKU below ⬇
  </div>
</div>
""", unsafe_allow_html=True)

# ------------- STEP 1: "Upload or SKU" Section -------------

st.markdown("""
<div style="
    background: #fff;
    border-radius: 1em;
    box-shadow: 0 2px 14px #661a3312;
    padding: 2em 0 2.5em 0;
    max-width: 900px;
    margin: 0 auto 3em auto;
">
  <h2 style="text-align:center; color:#661a33; font-size:2em; margin-bottom:0.2em;">
    1️⃣ Step 1: Upload your bottle <b>or</b> enter product SKU
  </h2>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 2])

# ----------- File upload -----------
with col1:
    uploaded_file = st.file_uploader(
        "Upload your wine bottle image",
        type=["png", "jpg", "jpeg", "webp"],
        key="uploader"
    )

    if uploaded_file:
        image_input = Image.open(uploaded_file).convert("RGB")
        img_from = "upload"
        st.session_state["image_input"] = image_input
        st.session_state["img_from"] = "upload"
        st.image(image_input, caption="Preview: Your bottle image", use_container_width=True)
    else:
        st.caption("1. You can upload an image, or use the SKU field.")

# ----------- SKU lookup + product image loading -----------
with col2:
    st.markdown("#### 1.1 Or select by SKU")
    sku_input = st.text_input("Enter product SKU for auto-image lookup", value="", key="sku_entered")
    load_btn = st.button("🔎 Load product image by SKU")

    sku_img_url = None
    sku_bkg_url = None

    if load_btn:
        sku_to_load = sku_input.strip()
        if not sku_to_load:
            st.error("Please enter a SKU before clicking Load.")
        else:
            match = df_skus[df_skus["sku"] == sku_to_load]
            if match.empty:
                st.error("No image found for this SKU.")
            else:
                url_img = str(match["bild"].values[0]).strip()
                url_bg = str(match["hintergrundbild"].values[0]).strip()
                sku_img_url = url_img if url_img else None
                sku_bkg_url = url_bg if url_bg else None
                try:
                    response = requests.get(url_img, timeout=10)
                    image_input = Image.open(BytesIO(response.content)).convert("RGB")
                    img_from = "sku"
                    st.session_state["image_input"] = image_input
                    st.session_state["img_from"] = "sku"
                    st.image(image_input, caption=f"Preview from SKU {sku_input}", use_container_width=True)
                    if sku_bkg_url and sku_bkg_url.startswith("http"):
                        st.info(f"Background image already exists for this SKU: [link]({sku_bkg_url})")
                    else:
                        st.success("No background image exists for this SKU yet.")
                except Exception as e:
                    st.error(f"Image could not be loaded: {e}")
    else:
        st.caption("2. Or just enter a SKU (then click “Load product image by SKU”).")

# ========== Banner-Format ==========
st.markdown("#### 1.2 Choose desired banner format")
ratio_option = st.radio(
    "Aspect ratio:",
    [
        "Wide Banner (4.54:1)",
        "3:2",
        "1:1 (Square)",
        "16:9 (Classic)",
        "Custom"
    ],
    key="ratio_choice",
    horizontal=False
)

ratio_map = {
    "Wide Banner (4.54:1)": (3000, 660),
    "3:2": (1500, 1000),
    "1:1 (Square)": (1024, 1024),
    "16:9 (Classic)": (1920, 1080)
}

if ratio_option == "Custom":
    width = st.number_input("Width (px)", min_value=300, max_value=5000, value=3000, key="num_width")
    height = st.number_input("Height (px)", min_value=100, max_value=3000, value=660, key="num_height")
    target_size = (int(width), int(height))
else:
    target_size = ratio_map.get(ratio_option, (3000, 660))

st.caption(f"🔲 Target banner size: {target_size[0]} x {target_size[1]} px")
st.caption("You can crop the generated image to this exact size later on.")

#====================#
#  SESSION STATE-Logik
#====================#
# Immer State-Bild verwenden, falls vorhanden!
image_input = st.session_state.get("image_input", None)
img_from = st.session_state.get("img_from", None)

ready_for_AI = image_input is not None
input_fingerprint = (None, None)
if ready_for_AI:
    if img_from == "sku":
        input_fingerprint = ("sku_" + sku_input.strip(), str(target_size))
    else:
        # FileUploader: name + format
        if uploaded_file:
            input_fingerprint = ("upload_" + getattr(uploaded_file, "name", "no_file"), str(target_size))
        else:
            input_fingerprint = ("upload_no_file", str(target_size))

if "last_fingerprint" not in st.session_state:
    st.session_state["last_fingerprint"] = None
if ready_for_AI and input_fingerprint != st.session_state.get("last_fingerprint"):
    reset_generation()
    st.session_state["last_fingerprint"] = input_fingerprint

#==========================#
# STEP 2: KI Prompt & Image
#==========================#
if ready_for_AI and target_size:
    st.markdown("---")
    st.markdown("""
    <div style="margin-top:2em; margin-bottom:1em; text-align:center;">
      <h2 style="color:#661a33;">2️⃣ Step 2: Generate your Prompt & Banner</h2>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🍷 Generate AI Prompt & Banner", type="primary", key="generate_ai"):
        with st.spinner("GPT-4o is analyzing your bottle and crafting the AI prompt..."):
            prompt_text = build_autonomous_prompt()
            gpt_prompt = generate_banner_prompt_gpt4(image_input, prompt_text)
            st.session_state['gpt_prompt'] = gpt_prompt
            st.session_state['ai_banner_img'] = None
            st.session_state['img_loading'] = True

        st.success("Prompt for DALL·E has been generated!")
        st.markdown("""
        <div style="
            background:#faf0f5;
            padding:1.1em;
            border-radius:6px;
            margin-top:2em;
            margin-bottom:2em;
            font-size:1.05em;">
          <b style="color:#700;">DALL·E Prompt (for full transparency)</b><br>
          <pre style="font-size: 1em; margin-bottom:0;">""" + st.session_state['gpt_prompt'] + """</pre>
        </div>
        """, unsafe_allow_html=True)

        with st.spinner("DALL·E is generating your banner... this may take a moment."):
            img_url = generate_dalle_image(st.session_state['gpt_prompt'], target_size)
            response = requests.get(img_url)
            ai_banner_img = Image.open(BytesIO(response.content)).convert("RGB")
            st.session_state['ai_banner_img'] = ai_banner_img
            st.session_state['img_loading'] = False

    if st.session_state.get("gpt_prompt"):
        st.markdown("""
        <div style="
            background:#faf0f5;
            padding:1.1em;
            border-radius:6px;
            margin-top:2em;
            margin-bottom:2em;
            font-size:1.05em;">
            <b style="color:#700;">DALL·E Prompt (for full transparency)</b><br>
            <pre style="font-size: 1em; margin-bottom:0;">""" + st.session_state['gpt_prompt'] + """</pre>
        </div>
        """, unsafe_allow_html=True)

    if st.session_state.get("img_loading", False):
        st.info("🧑‍🎨 Your banner is being created by DALL·E. This may take up to 30 seconds...")

    # ========= STEP 3: Cropper mit kleiner Startbox =========
    if st.session_state.get("ai_banner_img") is not None:
        st.markdown("---")
        st.markdown("""
        <div style="margin-top:2em; margin-bottom:1em; text-align:center;">
          <h2 style="color:#661a33;">3️⃣ Step 3: Crop your banner & download</h2>
        </div>
        """, unsafe_allow_html=True)

        ai_banner_img = st.session_state["ai_banner_img"]
        target_width, target_height = target_size
        aspect_ratio = target_width / target_height
        orig_width, orig_height = ai_banner_img.size

        desired_width = int(orig_width * 0.3)
        desired_height = int(desired_width / aspect_ratio)
        scaled_aspect_ratio_tuple = (desired_width, desired_height)

        if cropper_available:
            cropped_img = st_cropper(
                ai_banner_img,
                realtime_update=True,
                box_color="#932238",
                aspect_ratio=scaled_aspect_ratio_tuple
            )

            final_img = cropped_img.resize((target_width, target_height))
            st.image(final_img, caption=f"Cropped & scaled banner ({target_width} x {target_height})")

            buffer = BytesIO()
            final_img.save(buffer, format="JPEG", quality=95)
            st.download_button(
                label="📥 Download final JPG",
                data=buffer.getvalue(),
                file_name="wine_banner_cropped.jpg",
                mime="image/jpeg"
            )
            st.success("Done! Your customized banner is ready to use.")

        else:
            st.warning("streamlit-cropper not installed. Please install with: pip install streamlit-cropper")

    elif st.session_state.get("gpt_prompt"):
        st.info("Generating DALL·E 3 image...")

else:
    st.info("✅ You can start after uploading/selecting an image and choosing a target format!")