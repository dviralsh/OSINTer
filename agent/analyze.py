import os
import json
import subprocess
from datetime import datetime
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DATA_DIR = "agent/data"
DATA_FILE = os.path.join(DATA_DIR, "raw_data.json")
CRAWLERS_DIR = "agent/crawlers"
HEATMAP_FILE = "docs/heatmap_data.json"
BLOG_FILE = "docs/blog_data.json"
FEEDBACK_FILE = os.path.join(DATA_DIR, "feedback.txt")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs("docs", exist_ok=True)

def run_crawlers():
    if not os.path.exists(CRAWLERS_DIR):
        return
        
    for crawler in os.listdir(CRAWLERS_DIR):
        if crawler.endswith(".py"):
            script_path = os.path.join(CRAWLERS_DIR, crawler)
            try:
                result = subprocess.run(["python", script_path], capture_output=True, text=True, timeout=60)
                if result.returncode != 0:
                    error_msg = result.stderr.strip()[-300:]
                    with open(DATA_FILE, 'a', encoding='utf-8') as f:
                        f.write(json.dumps({"source": crawler, "content": f"no data - error: {error_msg}"}) + "\n")
            except subprocess.TimeoutExpired:
                with open(DATA_FILE, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"source": crawler, "content": "no data - error: execution timed out after 60 seconds"}) + "\n")
            except Exception as e:
                with open(DATA_FILE, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"source": crawler, "content": f"no data - error: {str(e)}"}) + "\n")

def write_feedback(message):
    with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        f.write(message + "\n")

def analyze_data_and_generate_content():
    if not os.path.exists(DATA_FILE):
        return
        
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    if not lines:
        return
        
    raw_text = "".join(lines)[:15000]
    
    prompt = f"""
    You are an OSINT lead analyst. Read the following raw data scraped by your crawler agents. 
    Some entries might indicate errors in the format 'no data - error: ...'.
    
    Raw Data:
    {raw_text}
    
    Produce a JSON output strictly with three keys:
    1. 'blog_post': A detailed analytical summary in HTML format (use <h3>, <p>, <ul> tags). Ignore code errors in the blog.
    2. 'locations': A list of locations mentioned in valid data, formatted exactly as objects with 'lat', 'lon', and 'intensity' (always 1.0). Example: [{{"lat": 31.0461, "lon": 34.8516, "intensity": 1.0}}]
    3. 'agent_feedback': If there are error entries ('no data - error'), write a clear, technical instruction for the upgrade agent to fix the specific crawler file based on the error message. If the data is good, leave this as an empty string.
    
    Output ONLY valid JSON.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.3
        )
        
        result_str = response.choices[0].message.content.strip()
        if result_str.startswith("```json"):
            result_str = result_str[7:]
        if result_str.endswith("```"):
            result_str = result_str[:-3]
            
        result_data = json.loads(result_str.strip())
        
        update_blog(result_data.get("blog_post", ""))
        update_heatmap(result_data.get("locations", []))
        
        feedback = result_data.get("agent_feedback", "")
        if feedback:
            write_feedback(f"Data Analysis Feedback: {feedback}")
        
        open(DATA_FILE, 'w').close()
        
    except Exception:
        write_feedback("The analysis step failed to parse the raw data. Please ensure crawlers append strictly valid JSON on each line.")

def update_blog(new_html_content):
    if not new_html_content:
        return
        
    blog_entries = []
    if os.path.exists(BLOG_FILE):
        try:
            with open(BLOG_FILE, "r", encoding="utf-8") as f:
                blog_entries = json.load(f)
        except:
            pass
            
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    new_entry = {
        "time": timestamp,
        "content": new_html_content
    }
    
    blog_entries.insert(0, new_entry)
    blog_entries = blog_entries[:50]
    
    with open(BLOG_FILE, "w", encoding="utf-8") as f:
        json.dump(blog_entries, f, ensure_ascii=False, indent=2)
        
def update_heatmap(new_points):
    heatmap_data = []
    if os.path.exists(HEATMAP_FILE):
        try:
            with open(HEATMAP_FILE, "r", encoding="utf-8") as f:
                heatmap_data = json.load(f)
        except:
            pass
            
    decay_factor = 0.95
    updated_data = []
    
    for point in heatmap_data:
        point["intensity"] *= decay_factor
        if point["intensity"] > 0.05:
            updated_data.append(point)
            
    updated_data.extend(new_points)
    
    with open(HEATMAP_FILE, "w", encoding="utf-8") as f:
        json.dump(updated_data, f, indent=2)

if __name__ == "__main__":
    run_crawlers()
    analyze_data_and_generate_content()