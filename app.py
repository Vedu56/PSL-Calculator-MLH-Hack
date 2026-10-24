import streamlit as st
import os
import base64
import json
import requests
from dotenv import load_dotenv

# 1. UI Setup (Minimalist Black-and-White Aesthetic)
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

# Using Llama 3.2 Vision which is fully supported on the active HF router endpoint
API_URL = "https://router.huggingface.co/hf-inference/models/meta-llama/Llama-3.2-11B-Vision-Instruct"
headers = {"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"}

st.title("AI Aesthetics Rater (PSL Calculator)")
st.write("Powered by Meta's Llama 3.2 11B Vision Model.")

# 3. App Logic
uploaded_file = st.file_uploader("Upload a selfie...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    st.image(uploaded_file, caption="Target locked.", width=300)
    
    if st.button("Calculate PSL Score"):
        with st.spinner("Analyzing facial features and computing PSL rating..."):
            
            prompt = """
            You are an analytical facial aesthetics rater on a PSL forum. 
            Analyze this image's facial features. 
            Calculate a strict PSL scale score (1 to 10). 
            Provide actionable looksmaxxing advice using community jargon (e.g., Chad, HTN, hunter eyes, mogging, softmaxxing, mewing). 
            CRITICAL GUARDRAIL: You must remain constructive and objective. 
            Output ONLY a valid JSON object with exactly two keys: "psl_score" (a number) and "advice" (a short string). Do not include markdown code blocks if possible, just raw JSON.
            """
            
            try:
                # Convert image to base64 for the API payload
                image_bytes = uploaded_file.read()
                image_data = base64.b64encode(image_bytes).decode("utf-8")
                
                payload = {
                    "inputs": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "image", "image": f"data:image/jpeg;base64,{image_data}"},
                                {"type": "text", "text": prompt}
                            ]
                        }
                    ],
                    "parameters": {"max_new_tokens": 300}
                }
                
                response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
                
                # SHOW THE EXACT STATUS AND TEXT ON SCREEN FOR DEBUGGING
                if response.status_code != 200:
                    st.error(f"HF Error Status {response.status_code}: {response.text}")
                    data = {"psl_score": 0.0, "advice": "Check error above."}
                else:
                    response_data = response.json()
                    
                    if isinstance(response_data, list) and len(response_data) > 0:
                        raw_text = response_data[0].get("generated_text", "")
                        if isinstance(raw_text, list):
                            raw_text = raw_text[-1].get("content", "")
                    elif isinstance(response_data, dict):
                        raw_text = response_data.get("generated_text", str(response_data))
                    else:
                        raw_text = str(response_data)
                        
                    raw_text = raw_text.strip()
                    if raw_text.startswith("```json"): 
                        raw_text = raw_text[7:-3]
                    elif raw_text.startswith("```"): 
                        raw_text = raw_text[3:-3]
                    raw_text = raw_text.strip()
                    
                    data = json.loads(raw_text)
                
            except Exception as e:
                st.error(f"Python Exception: {str(e)}")
                data = {
                    "psl_score": 6.5,
                    "advice": "Fallback triggered."
                }
                
            st.metric(label="Final PSL Score", value=f"{data.get('psl_score')}/10")
            st.success(f"💡 Looksmaxxing Advice: {data.get('advice')}")