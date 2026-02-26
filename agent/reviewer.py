import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

CRAWLERS_DIR = "agent/crawlers"
DATA_DIR = "agent/data"
FEEDBACK_FILE = os.path.join(DATA_DIR, "feedback.txt")

os.makedirs(CRAWLERS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

def write_feedback(message):
    with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        f.write(message + "\n")

def review_and_optimize_crawlers():
    crawler_files = [f for f in os.listdir(CRAWLERS_DIR) if f.endswith(".py")]
    
    for crawler in crawler_files:
        filepath = os.path.join(CRAWLERS_DIR, crawler)
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()

        prompt = f"""
        You are a senior Python software engineer reviewing OSINT data crawlers.
        Review the following code for '{crawler}'.
        Fix any potential bugs (like missing imports, bad XML parsing, or logic errors), optimize the logic, and ensure it appends valid JSON to 'agent/data/raw_data.json'.
        Return ONLY the optimized Python code. Do not include markdown wrappers like ```python. 
        Do not write any comments or prints in Hebrew.
        
        Code to review:
        {code}
        """
        
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.2
            )
            
            optimized_code = response.choices[0].message.content.strip()
            if optimized_code.startswith("```python"):
                optimized_code = optimized_code[9:]
            if optimized_code.endswith("```"):
                optimized_code = optimized_code[:-3]
                
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(optimized_code.strip())
        except Exception:
            pass

def suggest_new_directions():
    crawler_files = [f for f in os.listdir(CRAWLERS_DIR) if f.endswith(".py")]
    prompt = f"""
    You are a lead OSINT architect. Your system currently has these crawlers: {', '.join(crawler_files)}.
    Suggest exactly ONE new, highly valuable open intelligence source (e.g., a specific public RSS feed, an open API, public government data) that is NOT in this list.
    Write a brief, technical instruction for the upgrade agent to build it.
    Return ONLY the instruction string.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7
        )
        suggestion = response.choices[0].message.content.strip()
        write_feedback(f"Architect Suggestion: {suggestion}")
    except Exception:
        pass

if __name__ == "__main__":
    review_and_optimize_crawlers()
    suggest_new_directions()