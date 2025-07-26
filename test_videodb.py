from videodb import connect, IndexType
import time

def main():
    # --- 1. Configuration ---
    try:
        conn = connect(api_key="sk-Sl1e06ZEOoMNWQm4ouip89HEkPMixKexCnS9U0mtMQU")
        collection = conn.get_collection()
        video_path = "C:/echo_chamber_hackathon/sample_video.mp4"
    except Exception as e:
        print(f"Configuration failed: {e}")
        return

    print("Starting process...")

    try:
        # --- 2. Upload and Index ---
        print(f"Uploading video: {video_path}")
        video = collection.upload(file_path=video_path)
        print(f"Video uploaded successfully! Video ID: {video.id}")

        print("Starting scene indexing...")
        index_id = video.index_scenes() # Using default simple indexing
        print(f"Scene indexing job started with Index ID: {index_id}")

        # --- 3. Wait for Processing ---
        print("Waiting 90 seconds for indexing to complete...")
        time.sleep(90)
        print("Wait complete.")

        # --- 4. Get and Display the Indexing Results ---
        print("\n--- Fetching AI-Generated Scene Descriptions ---")
        scene_index = video.get_scene_index(index_id)
        print("Here are the scenes and the descriptions the AI created:")
        print(scene_index)
        print("--- End of Descriptions ---")

        # --- 5. Search (Optional for now) ---
        print("\nNow you can try searching again using text from the descriptions above.")
        # ... search logic would go here ...

    except Exception as e:
        print("\n--- ❌ An Error Occurred ---")
        print(f"The error was: {e}")

if __name__ == "__main__":
    main()