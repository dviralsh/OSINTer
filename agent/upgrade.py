import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

CRAWLERS_DIR = "agent/crawlers"
DATA_DIR = "agent/data"
FEEDBACK_FILE = os.path.join(DATA_DIR, "feedback.txt")

os.makedirs(CRAWLERS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

def get_system_state():
    existing_files = []
    for f in os.listdir(CRAWLERS_DIR):
        if f.endswith(".py"):
            existing_files.append(f)
    
    feedback = ""
    if os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            feedback = f.read().strip()
            
    return existing_files, feedback

def run_upgrade():
    existing_files, feedback = get_system_state()
    
    state_info = f"Current crawlers in system: {', '.join(existing_files) if existing_files else 'None'}."
    feedback_info = f"Feedback from Analysis Agent: {feedback}" if feedback else "No current feedback."
    
    prompt = f"""
    You are an autonomous OSINT agent developer.
    {state_info}
    {feedback_info}
    
    Your task:
    If there is feedback about a broken crawler or bad data format, fix the specific crawler mentioned. 
    Otherwise, write a NEW crawler for a REAL, public news source, open API, or specialized OSINT projects (specifically target sources like pizzint.watch or similar intelligence aggregation platforms). Do not use mock data.
    
    Requirements for the Python script:
    1. Fetch real recent news, OSINT or intelligence data.
    2. Append the extracted text as a JSON string to 'agent/data/raw_data.json'. The format MUST be a dictionary with 'source' and 'content' keys.
    3. Use libraries like 'requests' or 'beautifulsoup4'.
    4. Wrap the main logic in a try-except block.
    5. The script MUST run once and exit. Never use infinite loops (like `while True`).
    
    Output strictly a JSON object with two keys:
    - 'filename': A smart, descriptive filename for the crawler (e.g., 'crawler_pizzint.py'). If fixing an existing crawler, use its exact existing filename.
    - 'code': The complete, runnable Python code as a string. Do not include markdown formatting like python in the string itself.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "You are an elite OSINT software engineer. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=3000
        )
        
        result_str = response.choices[0].message.content.strip()
        
        if result_str.startswith("```json"):
            result_str = result_str[7:]
        if result_str.endswith("```"):
            result_str = result_str[:-3]
            
        result_data = json.loads(result_str.strip())
        
        filename = result_data["filename"]
        code_content = result_data["code"]
        
        filepath = os.path.join(CRAWLERS_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code_content)
            
        print(f"Upgrade complete. Wrote file: {filepath}")
        
        if os.path.exists(FEEDBACK_FILE):
            os.remove(FEEDBACK_FILE)
            
    except Exception as e:
        print(f"Failed to generate or parse upgrade: {e}")

if __name__ == "__main__":
    run_upgrade()