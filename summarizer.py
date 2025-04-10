import arxiv
import smtplib
from email.mime.text import MIMEText
import lmstudio
from datetime import date

# Define your email details
sender_email = "dnibs.ai@gmail.com"
receiver_email = "david.k.niblick@gmail.com"
today = date.today()
subject = "Arxiv LLM Research " + str(today)

client = arxiv.Client()

search = arxiv.Search(
  query = "LLM",
  max_results = 5,
  sort_by = arxiv.SortCriterion.SubmittedDate
)
# Fetch top 5 papers from last week related to 'LLM research'
papers = client.results(search)

model = lmstudio.llm()
all_summaries = ""
metadata = ""

for paper in papers:
    # Download and summarize the paper
    paper.download_pdf()
    with open(f"{paper.title}.pdf", "rb") as file:
        text = file.read().decode('utf-8')
        prompt = f"Summarize this paper in one paragraph:\n\n{text}"
        summary = model.respond(prompt)

    # Update all_summaries and metadata
    all_summaries += f"Summary of {paper['title']}:\n{summary}\n\n"
    metadata += f"Title: {paper['title']}\nAuthors: {', '.join(paper.authors)}\nPublished: {paper.published}\nLink: {paper['pdf_url']}\n\n"

# Save all_summaries and metadata to a file
with open("all_summaries.txt", "w") as f:
    f.write(metadata + "\n\n" + all_summaries)

body = f"Metadata:\n{metadata}\n\nAll Summaries:\n{all_summaries}"

# Send the combined summary and metadata via email
msg = MIMEText(body)
msg['Subject'] = subject
msg['From'] = sender_email
msg['To'] = receiver_email

try:
    # Connect to the SMTP server (e.g., Gmail's SMTP server)
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()  # Secure the connection
        server.login(sender_email, "your_app_password")  # Log in to your email account
        server.sendmail(sender_email, receiver_email, msg.as_string())  # Send the email
    print("Email sent successfully!")
except Exception as e:
    print(f"Failed to send email: {e}")
