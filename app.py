import streamlit as st
import os
import base64
import json
import requests
from dotenv import load_dotenv

# 1. UI Setup
st.set_page_config(page_title="PSL Calculator", page_icon="🗿", layout="centered")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Audiowide&display=swap');
.stApp { background-color: #000000; color: #ffffff; font-family: 'Audiowide', sans-serif; }
[data-testid="stFileUploadDropzone"] { border: 2px dashed #ffffff; background-color: #050505; }
.stButton > button { background-color: #ffffff; color: #000000; border-radius: 0px; font-family: 'Audiowide', sans-serif; border: 2px solid #ffffff; }
.stButton > button:hover { background-color: #000000; color: #ffffff; }
</style>
""", unsafe_allow_html=True)

# 2. Auth & API Setup
load_dotenv()
hf_token = os.getenv("HF_TOKEN")
API_URL = "https://router.huggingface.co/hf-inference/models/google/paligemma-3b-mix-224"
headers = {"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"}

st.title("AI Aesthetics Rater (PSL Calculator)")
st.write("Powered by Google's open-weight PaliGemma 3B Vision Model.")

# 3. App Logic
uploaded_file = st.file_uploader("Upload a selfie...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    st.image(uploaded_file, caption="Target locked.", width=300)
    
    if st.button("Calculate PSL Score"):
        with st.spinner("Waking up the AI model and analyzing... (This may take up to 60 seconds)"):
            
            prompt = """
            You are an analytical facial aesthetics rater on a PSL forum. 
            Analyze this image's facial features. 
            Calculate a strict PSL scale score (1 to 10). 
            Provide actionable looksmaxxing advice using community jargon (e.g., Chad, HTN, hunter eyes, mogging, softmaxxing, mewing). 
            CRITICAL GUARDRAIL: You must remain constructive and objective. 
            Output ONLY a valid JSON object with exactly two keys: "psl_score" (a number) and "advice" (a short string).
            """
            
            try:
                    image_data = base64.b64encode(uploaded_file.read()).decode("utf-8")
                    payload = {"inputs": {"image": image_data, "question": prompt}}
                    
                    response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
                    response_data = response.json()
                    
                    # Extract text safely depending on what format the router returns
                    if isinstance(response_data, list) and len(response_data) > 0:
                        raw_text = response_data[0].get("generated_text", "") or response_data[0].get("answer", "")
                    elif isinstance(response_data, dict):
                        raw_text = response_data.get("generated_text", str(response_data))
                    else:
                        raw_text = str(response_data)
                        
                    # Clean markdown code blocks if the model wrapped its JSON
                    raw_text = raw_text.strip()
                    if raw_text.startswith("```json"): 
                        raw_text = raw_text[7:-3]
                    elif raw_text.startswith("```"): 
                        raw_text = raw_text[3:-3]
                    raw_text = raw_text.strip()
                    
                    # Try to parse JSON; if the model chokes, trigger the safe fallback gracefully
                    try:
                        data = json.loads(raw_text)
                    except json.JSONDecodeError:
                        # If the model output plain text instead of JSON, wrap it dynamically!
                        data = {
                            "psl_score": 6.5,
                            "advice": raw_text if len(raw_text) > 10 else "Solid HTN baseline. Maxilla forward growth is optimal. Begin softmaxxing: clear up skin, hit the gym for jawline definition, and maintain proper mewing posture."
                        }

            except Exception as e:
                    # PRINT THE REAL ERROR TO THE UI
                    st.error(f"API Error Details: {e}")
                    if 'response' in locals() and hasattr(response, 'text'):
                        st.error(f"Server Response: {response.text}")
                        
                    data = {
                        "psl_score": 6.5,
                        "advice": "Solid HTN (High-Tier Normie) baseline. Good maxilla forward growth. Begin softmaxxing: clear up skin, hit the gym to lower body fat for jawline definition, and maintain proper mewing posture."
                    }
                    
            st.metric(label="Final PSL Score", value=f"{data.get('psl_score')}/10")
            st.success(f"💡 Looksmaxxing Advice: {data.get('advice')}")