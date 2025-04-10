import os
import datetime
import requests
import arxiv
from arxiv import Client
from pdfminer.high_level import extract_text
import lmstudio  
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv, find_dotenv


# === Config ===
SEARCH_QUERY = "LLM OR large language model"
MAX_RESULTS = 2
OUTPUT_FOLDER = "arxiv_summaries"
DAYS_BACK = 360
TODAY = datetime.date.today()
SUBJECT = "Arxiv LLM Research " + str(TODAY)

# === Load env variables ===
dotenv_path = find_dotenv()
if not dotenv_path:
    raise FileNotFoundError(".env file not found")
load_dotenv()
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
RECEIVER_EMAILS = os.getenv('RECEIVER_EMAIL').split(',')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
if not SENDER_EMAIL or not RECEIVER_EMAILS or not EMAIL_PASSWORD:
    raise ValueError("Missing required environment variables: SENDER_EMAIL, RECEIVER_EMAIL, or EMAIL_PASSWORD")

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# === Summarizer using LM Studio ===
def summarize_text_with_lmstudio(text, model=None):
    global lmstudio_model  # Use the global variable to store the model instance

    if model is None:
        if lmstudio_model is None:  # Check if the model is already loaded
            print("🤖 Loading LM Studio model...")
            lmstudio_model = lmstudio.llm(model='gemma-3-27b-it')  # Load the model
        model = lmstudio_model  # Use the loaded model

    prompt = (
        "Summarize the following academic paper. Assume the reader is knowledgable about artificial intelligence, but has not read the paper."
        "Start with a one-sentence summary of what the paper contributes. Then give a summary with more detail." 
        "Include core concepts and any significant breakthroughs. End with proposed further research." 
        "If possible, include links for more reading. Paper begins here:\n\n"
        f"{text[:10000]}\n\nSummary:"
    )

    result = model.respond(prompt)
    return result  



# === Helpers ===
def is_recent(published_date, days_back=DAYS_BACK):
    published = datetime.datetime.fromisoformat(published_date.replace("Z", "+00:00"))
    return (datetime.datetime.now(datetime.timezone.utc) - published).days <= days_back


def download_pdf(url, filename):
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to download PDF from {url}. HTTP Status: {response.status_code}")
    with open(filename, 'wb') as f:
        f.write(response.content)

# === Main ===

def main():
    print(f"🔍 Searching arXiv for recent '{SEARCH_QUERY}' papers...")

    # Create a client instance
    client = arxiv.Client()
    search = arxiv.Search(
        query=SEARCH_QUERY,
        max_results=MAX_RESULTS,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending
    )

    results = client.results(search)

    model = lmstudio.llm()

    email_body = 'Summary of recent publications regarding AI and LLMs for ' + str(TODAY)
    count = 0
    for result in results:
        if not is_recent(result.published.isoformat()):
            continue

        arxiv_id = result.entry_id.split('/')[-1]
        title = result.title.strip().replace("\n", " ")
        pdf_url = result.pdf_url

        print(f"\n📄 [{arxiv_id}] {title}")

        # === Download PDF ===
        pdf_path = os.path.join(OUTPUT_FOLDER, f"{arxiv_id}.pdf")
        download_pdf(pdf_url, pdf_path)

        # === Extract and Summarize ===
        try:
            text = extract_text(pdf_path)
            summary = summarize_text_with_lmstudio(text, model=model)
        except Exception as e:
            summary = f"[Error extracting text or summarizing: {e}]"

        # === Save summary ===
        summary_file = os.path.join(OUTPUT_FOLDER, f"{arxiv_id}.txt")
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"Title: {title}\n\nSummary:\n{summary}")

        print(f"✅ Summary saved to {summary_file}")

        email_body += f"Summary of {title}, {arxiv_id}:\n{pdf_url}\n{summary}\n\n\n\n\n"
        email_body += f"------------------------------------------------\n\n"
        count += 1

    if count == 0:
        print("⚠️ No recent papers found in the last 30 days.")
    else:
        print(f"\n🎉 Done! Summaries saved in '{OUTPUT_FOLDER}' folder.")

    
    # Create the email message
    msg = MIMEText(email_body)
    msg['Subject'] = SUBJECT
    msg['From'] = SENDER_EMAIL
    msg['To'] = ', '.join(RECEIVER_EMAILS)  # This works for both single and multiple emails

    try:
        # Connect to the SMTP server (e.g., Gmail's SMTP server)
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()  # Secure the connection
            server.login(SENDER_EMAIL, EMAIL_PASSWORD)  # Log in to your email account
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAILS, msg.as_string())  # Send the email
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    main()