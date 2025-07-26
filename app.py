import streamlit as st
from videodb import connect, IndexType
import time
import os
import google.generativeai as genai
import re

# --- Page Configuration ---
st.set_page_config(
    page_title="Echo Chamber",
    page_icon="🚀",
    layout="wide"
)

# --- App Title ---
st.title("🚀 Echo Chamber: AI Video Insight Engine")
st.info("Upload a video to get a scene-by-scene breakdown, detect key visuals, and ask questions about its content.")

# --- Sidebar for Controls ---
with st.sidebar:
    st.header("⚙️ Controls")
    
    videodb_api_key = st.text_input("Enter your VideoDB API Key", type="password")
    gemini_api_key = st.text_input("Enter your Gemini API Key", type="password")
    
    uploaded_file = st.file_uploader("Upload a video...", type=["mp4", "mov", "avi"])
    
    analyze_button = st.button("Analyze Video", type="primary")

# --- Initialize Session State ---
if "scenes" not in st.session_state:
    st.session_state.scenes = []
if "transcript" not in st.session_state:
    st.session_state.transcript = ""
if "video_id" not in st.session_state:
    st.session_state.video_id = None
if "video_object" not in st.session_state:
    st.session_state.video_object = None


# --- Main Logic on Button Click ---
if analyze_button:
    if uploaded_file and videodb_api_key and gemini_api_key:
        # Clear previous results
        st.session_state.scenes = []
        st.session_state.transcript = ""
        st.session_state.video_id = None
        st.session_state.video_object = None

        with st.spinner("Analyzing... This may take a few minutes."):
            try:
                # Save uploaded file temporarily
                temp_video_path = os.path.join(".", uploaded_file.name)
                with open(temp_video_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # Connect and upload to VideoDB
                conn = connect(api_key=videodb_api_key)
                collection = conn.get_collection()
                
                st.write("Uploading video...")
                video = collection.upload(file_path=temp_video_path)
                st.session_state.video_id = video.id
                st.session_state.video_object = video # Save the video object
                
                # --- Generate Both Visuals and Audio using Correct Functions ---
                st.write("Indexing video scenes (visuals)...")
                index_id = video.index_scenes()
                
                st.write("Indexing spoken words (audio)...")
                video.index_spoken_words()
                
                st.info("AI is processing the video. Please wait (approx. 90 seconds)...")
                time.sleep(90)
                
                # --- Fetch Both Visuals and Audio ---
                st.write("Fetching results...")
                st.session_state.scenes = video.get_scene_index(index_id)
                st.session_state.transcript = video.get_transcript()
                
                st.success("Analysis Complete!")

            except Exception as e:
                st.error(f"An error occurred during analysis: {e}")
            finally:
                # Clean up temp file
                if os.path.exists(temp_video_path):
                    os.remove(temp_video_path)
    else:
        st.warning("Please provide all API keys and upload a video.")

# --- Display Results Area ---
if st.session_state.scenes:
    st.header("🎬 Visual Scene Breakdown")
    st.write("Here is what the AI *saw* in your video. Click on any scene to expand it.")
    for i, scene in enumerate(st.session_state.scenes):
        with st.expander(f"Scene {i+1} ({scene['start']:.2f}s - {scene['end']:.2f}s): {scene['description'][:60]}..."):
            st.write(f"**AI Description:** {scene['description']}")
    
    try:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
    except Exception as e:
        model = None
        st.error(f"Error configuring Gemini: Please check your API key. Details: {e}")

    if model:
        # --- Create tabs for a cleaner layout ---
        tab1, tab2, tab3, tab4 = st.tabs(["🔍 Key Visuals", "💬 Q&A with Clip", "🎙️ Key Quotes", " campaigns"])

        with tab1:
            st.header("Key Object & Brand Detector")
            if st.button("Detect Key Visuals"):
                with st.spinner("Scanning for key brands and objects..."):
                    all_descriptions = "\n".join([s['description'] for s in st.session_state.scenes])
                    prompt = f"Analyze the following scene descriptions. Identify all recurring brands, logos, named products, and important physical objects. Consolidate similar items. Return a simple, comma-separated list.\n\nDESCRIPTIONS:\n{all_descriptions}"
                    try:
                        response = model.generate_content(prompt)
                        st.success("Detected Visuals:")
                        st.info(response.text)
                    except Exception as e:
                        st.error(f"Could not detect objects: {e}")

        with tab2:
            st.header("Ask a Question, Get a Video Clip")
            question = st.text_input("E.g., 'When is the new phone revealed?'")
            if st.button("Get Answer and a Clip"):
                if question and st.session_state.video_object:
                    with st.spinner("Thinking and finding the perfect moment..."):
                        scenes_with_timestamps = "\n".join([f"Scene from {s['start']}s to {s['end']}s: {s['description']}" for s in st.session_state.scenes])
                        transcript_text = st.session_state.transcript
                        prompt = f"""
                        You are an AI assistant analyzing a video. Based on the provided visual and audio contexts, answer the user's question. 
                        Your response MUST be in two parts:
                        1.  **Answer:** A clear, text-based answer.
                        2.  **Timestamp:** The single most relevant timestamp (in seconds) from the video that best represents the answer. Return ONLY the number.

                        ---VISUAL CONTEXT---\n{scenes_with_timestamps}
                        ---AUDIO CONTEXT---\n{transcript_text}
                        
                        QUESTION: "{question}"
                        """
                        try:
                            response = model.generate_content(prompt)
                            response_text = response.text
                            
                            answer_match = re.search(r"Answer:(.*?)Timestamp:", response_text, re.DOTALL)
                            timestamp_match = re.search(r"Timestamp:.*?(\d+\.?\d*)", response_text, re.DOTALL)

                            if answer_match and timestamp_match:
                                answer = answer_match.group(1).strip()
                                timestamp = float(timestamp_match.group(1).strip())
                                
                                st.markdown(f"**Answer:** {answer}")
                                
                                # --- STABLE SOLUTION: Generate a fresh clip of the relevant moment ---
                                st.info("Displaying the most relevant moment below:")
                                # Create a 10-second timeline around the key moment
                                clip_start = max(0, timestamp - 2)
                                clip_end = timestamp + 8
                                clip_timeline = [[clip_start, clip_end]]
                                
                                # Generate and display the clip
                                clip_url = st.session_state.video_object.generate_stream(timeline=clip_timeline)
                                st.video(clip_url)
                                st.caption(f"Generated clip from {clip_start:.2f}s to {clip_end:.2f}s")
                                
                            else:
                                st.markdown("The AI provided an answer, but I couldn't extract a specific timestamp. Here is the full response:")
                                st.markdown(response_text)
                        except Exception as e:
                            st.error(f"Could not get answer: {e}")
                else:
                    st.warning("Please analyze a video and ask a question.")

        with tab3:
            st.header("Key Quote Extractor")
            if st.button("Extract Top 5 Quotes"):
                with st.spinner("Reading the transcript to find the best soundbites..."):
                    transcript_text = st.session_state.transcript
                    if transcript_text:
                        prompt = f"You are a PR expert. Read the following transcript and extract the 5 most memorable, impactful, and quotable sentences. Return them as a simple bulleted list.\n\nTRANSCRIPT:\n{transcript_text}"
                        try:
                            response = model.generate_content(prompt)
                            st.success("Found Key Quotes:")
                            st.markdown(response.text)
                        except Exception as e:
                            st.error(f"Could not extract quotes: {e}")
                    else:
                        st.warning("No transcript available to analyze.")
        
        with tab4:
            st.header("Auto-Generated Social Media Campaign")
            if st.button("Create Social Posts"):
                with st.spinner("Writing social media posts..."):
                    all_descriptions = "\n".join([s['description'] for s in st.session_state.scenes])
                    transcript_text = st.session_state.transcript
                    if transcript_text or all_descriptions:
                        prompt = f"""
                        You are a social media marketing expert. Based on the following video transcript and visual descriptions, create three distinct social media posts to promote it: 
                        1. A professional post for LinkedIn.
                        2. A short, punchy post for Twitter/X.
                        3. An engaging caption for Instagram.
                        
                        Include relevant hashtags for each. Format the output clearly with headings for each platform.

                        ---VISUAL CONTEXT---\n{all_descriptions}
                        ---AUDIO CONTEXT---\n{transcript_text}
                        """
                        try:
                            response = model.generate_content(prompt)
                            st.success("Your Social Media Campaign is Ready:")
                            st.markdown(response.text)
                        except Exception as e:
                            st.error(f"Could not generate posts: {e}")
                    else:
                        st.warning("No content available to generate posts.")
