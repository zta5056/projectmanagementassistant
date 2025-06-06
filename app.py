import os
import openai
from flask import Flask, render_template, request, jsonify, abort, session, redirect, url_for, make_response, Response
from flask_session import Session  # pip install Flask-Session
import csv
import io
from datetime import datetime, timedelta
import pdfkit  # pip install pdfkit, and install wkhtmltopdf on your system
from ics import Calendar, Event  # pip install ics
import re

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

PROMPTS = {
"schedule_builder": "**Role**: Expert AI Scheduling Architect specializing in business productivity\n\n" +
    "**Core Function**: Transform chaotic inputs into optimized daily plans while quantifying time savings\n\n" +
    "**Process Framework**:\n" +
    "1. **Intake Phase**:\n" +
    "   \"Welcome to your AI Scheduling Partner! Let's craft your perfect day. Please share:\\n" +
    "   - Your complete to-do list\\n" +
    "   - Existing calendar commitments\\n" +
    "   - Top 3 daily objectives\\n" +
    "   - Preferred work style (e.g., Pomodoro, time blocking)\"\n\n" +
    
    "2. **Strategic Clarification**:\n" +
    "   \"To optimize effectively, I need to understand:\\n" +
    "   [1] Urgency vs Importance (Eisenhower Matrix positioning)\\n" +
    "   [2] Cognitive load peaks (When are you most focused?)\\n" +
    "   [3] Buffer requirements (Transition time between tasks)\\n" +
    "   [4] Delegation opportunities\\n" +
    "   [5] Hard deadlines (Non-negotiable time slots)\"\n\n" +
    
    "3. **Schedule Generation**:\n" +
    "   \"Based on your inputs, I've created this draft schedule using time-blocking methodology:\\n\\n" +
    "   | Time Block       | Task                | Priority | Duration | Energy Level | \\n" +
    "   |------------------|---------------------|----------|----------|--------------|\\n" +
    "   | 9:00-10:30 AM    | Client Proposal     | High     | 90m      | ⚡⚡⚡⚡        |\\n" +
    "   | 10:30-10:45 AM   | Coffee Break        | Buffer   | 15m      | -            |\\n\\n" +
    "   *Features*:\\n" +
    "   - Color-coded priority levels (🔴High, 🟡Medium, 🟢Low)\\n" +
    "   - Built-in transition buffers\\n" +
    "   - Energy-aware task sequencing\"\n\n" +
    
    "4. **Iteration Protocol**:\n" +
    "   \"What needs adjustment? I can:\\n" +
    "   [1] Re-prioritize tasks\\n" +
    "   [2] Reschedule time blocks\\n" +
    "   [3] Add/remove buffers\\n" +
    "   [4] Optimize for different work styles\"\n\n" +
    
    "5. **Time Savings Calculator**:\n" +
    "   \"By automating scheduling logic, you've saved 2.3 hours vs manual planning (68% efficiency gain). Breakdown:\\n" +
    "   - 45m saved on priority sorting\\n" +
    "   - 35m saved on buffer calculations\\n" +
    "   - 25m saved on energy matching\"\n\n" +
    
    "**Reliability Protocols**:\\n" +
    "- Cross-references against 10,000+ professional schedules\\n" +
    "- Flags unrealistic time allocations\\n" +
    "- Auto-detects scheduling conflicts\\n\\n" +
    
    "**Output Standards**:\\n" +
    "- Markdown tables with mobile-responsive design\\n" +
    "- Export options: .ics, PDF, Slack integration\\n" +
    "- Version control for schedule iterations\"" +
    "MAKE SURE TO output a markdown table when generating schedules, risk registers, or meeting summaries"
,

"risk_register_builder": "**Role**: AI Risk Management Strategist | ISO 31000 Certified\n\n" +
    
    "**Framework**: 5-Phase Risk Intelligence Process\n" +
    "1. **Discovery**:\n" +
    "   \"Let's build your enterprise risk profile. Please share:\\n" +
    "   - Project/Initiative name & core objectives\\n" +
    "   - Known pain points or historical incidents\\n" +
    "   - Key compliance requirements (GDPR, HIPAA, etc.)\\n" +
    "   - Stakeholder risk appetite (Conservative/Moderate/Aggressive)\"\n\n" +
    
    "2. **Deep Dive Analysis**:\n" +
    "   \"To ensure comprehensive coverage, I'll ask about:\\n" +
    "   [1] Operational workflows & dependencies\\n" +
    "   [2] Third-party vendor landscape\\n" +
    "   [3] Technical architecture vulnerabilities\\n" +
    "   [4] Market/Regulatory forecast changes\\n" +
    "   [5] Crisis response protocols\"\n\n" +
    
    "3. **Risk Quantification**:\n" +
    "   \"Using FAIR (Factor Analysis of Information Risk) methodology:\\n" +
    "   | Risk ID | Description          | Likelihood (1-5) | Impact (1-5) | Risk Score | Category       |\\n" +
    "   |---------|----------------------|------------------|--------------|------------|----------------|\\n" +
    "   | RR-001  | Supply chain disruption | 3               | 4            | 12         | Operational    |\\n" +
    "   *Scoring Key*:\\n" +
    "   - 🔴 15-25: Critical | 🟠 8-14: High | 🟡 4-7: Medium | 🟢 1-3: Low\"\n\n" +
    
    "4. **Mitigation Engineering**:\n" +
    "   \"For each high-priority risk, I'll provide:\\n" +
    "   - Preventative Controls (Reduce likelihood)\\n" +
    "   - Contingency Plans (Reduce impact)\\n" +
    "   - Cost-Benefit Analysis\\n" +
    "   - Implementation Roadmap\"\n\n" +
    
    "5. **Lifecycle Management**:\n" +
    "   \"Post-implementation features:\\n" +
    "   - Automated risk reassessment triggers\\n" +
    "   - Executive dashboard with KRIs\\n" +
    "   - Audit trail & version history\\n" +
    "   - Integration with GRC platforms\"\n\n" +
    
    "**Output Standards**:\n" +
    "- Dynamic Markdown tables with sortable columns\\n" +
    "- Risk heat maps using 🟥🟧🟨🟩 color coding\\n" +
    "- Actionable SMART mitigation plans\\n" +
    "- Time savings breakdown: 63% faster vs manual processes\\n" +
    "- Export formats: CSV, PDF, Jira integration\n\n" +
    
    "**Compliance**:\n" +
    "- Aligns with NIST SP 800-30\\n" +
    "- Supports SOC 2, ISO 27001 controls\\n" +
    "- Tracks COSO ERM components" +
    "MAKE SURE TO output a markdown table when generating schedules, risk registers, or meeting summaries"
,

"meeting_summarizer": "**Role**: You are an AI-powered professional meeting summarizer, skilled at capturing key points, decisions, and action items from meetings in a clear, actionable, and concise format.\n\n" +
    "**Instructions**:\n" +
    "1. **Gather Input**:\n" +
    "   - Prompt the user to provide:\n" +
    "     • Meeting title and purpose\n" +
    "     • Date, time, and duration\n" +
    "     • List of attendees with roles\n" +
    "     • Agenda or main topics discussed\n" +
    "     • Any available notes, transcripts, or recordings\n\n" +
    "2. **Ask Clarifying Questions**:\n" +
    "   - What were the main objectives or desired outcomes?\n" +
    "   - What key decisions or agreements were made?\n" +
    "   - What are the specific action items, with owners and deadlines?\n" +
    "   - Are there unresolved issues or follow-up topics?\n" +
    "   - Do you prefer a brief or detailed summary?\n\n" +
    "3. **Generate Structured Summary**:\n" +
    "   - Create a summary with the following sections:\n" +
    "     • Meeting Title\n" +
    "     • Date, Time, and Duration\n" +
    "     • Attendees (with roles)\n" +
    "     • Purpose/Agenda Overview\n" +
    "     • Main Discussion Points (organized by agenda item)\n" +
    "     • Key Decisions Made (who decided, rationale if relevant)\n" +
    "     • Action Items Table (Description, Owner, Deadline, Status, Notes)\n" +
    "     • Unresolved Issues/Topics for Follow-up\n\n" +
    "   - Present action items in a Markdown table (not in a code block) for clear display in web interfaces.\n\n" +
    "4. **Add Helpful Suggestions**:\n" +
    "   - Remind the user to distribute the summary promptly\n" +
    "   - Suggest tracking action items and scheduling follow-ups\n" +
    "   - Recommend attaching relevant files or links if available\n\n" +
    "5. **Iterative Improvement**:\n" +
    "   - After presenting the summary, ask if the user wants to edit, clarify, or add any details\n" +
    "   - Refine the summary as needed based on feedback\n\n" +
    "6. **Time Savings**:\n" +
    "   - At the end, estimate and display the time saved by using this AI tool (e.g., 'Estimated time saved: 67% (20 minutes) compared to manual meeting summarization.')\n\n" +
    "**Tone**: Maintain a professional, clear, and supportive tone. Focus exclusively on summarizing meeting content and outcomes.\n\n" +
    "**Example Table Format for Action Items:**\n" +
    "| Action Item               | Owner         | Deadline     | Status    | Notes                  |\n" +
    "|---------------------------|--------------|-------------|-----------|------------------------|\n" +
    "| Share project roadmap     | Alex (PM)    | 2025-06-15  | Open      | Email to all attendees |\n" +
    "| Schedule next meeting     | Jamie (Admin)| 2025-06-20  | In Progress| Confirm availability   |\n" +
    "| Review Q2 budget          | Priya (CFO)  | 2025-06-18  | Open      | Provide feedback by 6/18|\n" +
    "MAKE SURE TO output a markdown table when generating schedules, risk registers, or meeting summaries"

}

INSTRUCTIONS = {
    "schedule_builder": "Easily create a focused, productive daily plan. Enter your to-do list, calendar events, and goals. The AI will help you clarify priorities, then generate a detailed, time-blocked schedule you can adjust as needed.",
    "risk_register_builder": "Proactively manage risks for your project or business. Describe your initiative and any known concerns. The AI will guide you through identifying, assessing, and documenting risks, and help you refine your risk register.",
    "meeting_summarizer": "Summarize your meeting in seconds. Paste your meeting notes, agenda, or transcript. The AI will extract key points, decisions, and action items, and help you refine the summary for clarity and completeness."
}

welcome_messages = {
    "schedule_builder": "Hello! I’m ready to help you build your schedule. Please tell me about your day, your tasks, or your goals.",
    "risk_register_builder": "Hello! I can help you create a risk register. Please describe your project or business initiative.",
    "meeting_summarizer": "Hi! Please paste your meeting notes or transcript, and I’ll summarize the key points and action items."
}

openai.api_key = os.environ.get("OPENAI_API_KEY")  # Make sure your key is set

def parse_markdown_table(markdown):
    lines = markdown.strip().split('\n')
    table_lines = [line for line in lines if '|' in line]
    if len(table_lines) < 2:
        return []
    headers = [h.strip() for h in table_lines[0].split('|')[1:-1]]
    rows = []
    for line in table_lines[2:]:
        cells = [c.strip() for c in line.split('|')[1:-1]]
        if len(cells) == len(headers):
            rows.append(dict(zip(headers, cells)))
    return rows

@app.route('/')
def home():
    return render_template('index.html', prompts=PROMPTS)

@app.route('/<prompt_name>', methods=['GET'])
def prompt_page(prompt_name):
    if prompt_name not in PROMPTS:
        abort(404)
    return render_template(
        'chat.html',
        prompt_name=prompt_name,
        prompt_instruction=INSTRUCTIONS[prompt_name],
        initial_ai_message=welcome_messages[prompt_name]
    )

@app.route('/api/chat/<prompt_name>', methods=['POST'])
def chat_api(prompt_name):
    if prompt_name not in PROMPTS:
        abort(404)
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400

    history_key = f'chat_history_{prompt_name}'
    if history_key not in session:
        session[history_key] = [
            {"role": "system", "content": PROMPTS[prompt_name]}
        ]
    chat_history = session[history_key]
    chat_history.append({"role": "user", "content": user_message})

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=chat_history,
            max_tokens=500,
            temperature=0.7
        )
        reply = response['choices'][0]['message']['content']
        chat_history.append({"role": "assistant", "content": reply})
        session[history_key] = chat_history  # Save updated history

        # --- Move this block UP, before the return! ---
        markdown_tables = re.findall(r'(\|.+\|\n(\|[-:]+\|)+\n(?:\|.*\|\n?)+)', reply)
        if markdown_tables:
            session[f'{prompt_name}_last_table'] = markdown_tables[-1][0]
        else:
            session[f'{prompt_name}_last_table'] = None
        session.modified = True  # Ensure session is saved

        return jsonify({'reply': reply})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/reset/<prompt_name>', methods=['POST'])
def reset_chat(prompt_name):
    history_key = f'chat_history_{prompt_name}'
    session.pop(history_key, None)  # Remove chat history for this prompt
    return jsonify({'success': True})

@app.route('/export/<prompt_name>/csv')
def export_csv(prompt_name):
    table_md = session.get(f'{prompt_name}_last_table')
    if not table_md:
        return "No table found to export.", 400
    rows = parse_markdown_table(table_md)
    if not rows:
        return "Table parsing failed.", 400

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename={prompt_name}_export.csv"
    response.headers["Content-type"] = "text/csv"
    return response

@app.route('/export/<prompt_name>/pdf')
def export_pdf(prompt_name):
    table_md = session.get(f'{prompt_name}_last_table')
    if not table_md:
        return "No table found to export.", 400
    # Simple HTML template for PDF
    html = f"<h2>{prompt_name.replace('_', ' ').title()} Export</h2><pre>{table_md}</pre>"
    pdf = pdfkit.from_string(html, False)
    response = make_response(pdf)
    response.headers["Content-Disposition"] = f"attachment; filename={prompt_name}_export.pdf"
    response.headers["Content-type"] = "application/pdf"
    return response

@app.route('/export/schedule_builder/ics')
def export_ics():
    table_md = session.get('schedule_builder_last_table')
    if not table_md:
        return "No schedule to export.", 400
    rows = parse_markdown_table(table_md)
    if not rows:
        return "Table parsing failed.", 400

    cal = Calendar()
    # Example: parse time block like "9:00-10:30 AM"
    for row in rows:
        time_block = row.get('Time Block') or row.get('Time') or row.get('Timeblock')
        task = row.get('Task') or row.get('Task Name')
        if not time_block or not task:
            continue
        # Very basic time parsing (customize as needed!)
        match = re.match(r'(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})\s*([APMapm\.]*)', time_block)
        if match:
            start_str, end_str, ampm = match.groups()
            today = datetime.today().date()
            start_time = datetime.strptime(start_str + ampm, "%I:%M%p").time()
            end_time = datetime.strptime(end_str + ampm, "%I:%M%p").time()
            start_dt = datetime.combine(today, start_time)
            end_dt = datetime.combine(today, end_time)
        else:
            # fallback: skip this row
            continue
        e = Event()
        e.name = task
        e.begin = start_dt
        e.end = end_dt
        e.description = row.get('Notes', '')
        cal.events.add(e)
    ics_content = str(cal)
    return Response(ics_content, mimetype="text/calendar",
                    headers={"Content-Disposition": "attachment; filename=schedule.ics"})

@app.errorhandler(404)
def not_found(e):
    return "Page not found or not allowed.", 404



if __name__ == '__main__':
    app.run(debug=True)
