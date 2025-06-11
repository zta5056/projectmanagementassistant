import os
import openai
from flask import Flask, render_template, request, jsonify, abort, session, redirect, url_for, make_response, Response, send_from_directory
from flask_session import Session
from flask_cors import CORS
import csv
import io
from datetime import datetime, timedelta
from ics import Calendar, Event
import re

app = Flask(__name__)

# FIXED: Proper session configuration for production
app.secret_key = os.environ.get("SECRET_KEY", "FALLBACK_SECRET_KEY")
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'ai_assistant:'
app.config['SESSION_FILE_DIR'] = '/tmp/flask_session'  # Use /tmp for Render
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True

# Enable CORS for session persistence
CORS(app, supports_credentials=True)

Session(app)

PROMPTS = {
"schedule_builder": """**Role**: Expert AI Scheduling Architect specializing in business productivity optimization

**MANDATORY OUTPUT FORMAT**: Always generate complete markdown tables with this exact structure:
| Time Block | Task | Priority | Duration | Energy Level |
|------------|------|----------|----------|--------------|
| 9:00-10:00 AM | [specific task] | High | 60m | ⚡⚡⚡⚡ |

**INTERACTION PROCESS**:

**Phase 1: Initial Greeting & Information Gathering**
"Welcome to your AI Scheduling Partner! I'll help you create an optimized daily schedule through a structured process.

First, please share your basic information:
- What day are you planning for?
- What are your working hours (start/end time)?
- Do you have any fixed appointments already scheduled?"

**Phase 2: Systematic Follow-Up Questions**
After receiving initial input, ALWAYS ask these follow-up questions in sequence:

"Thank you for that information! To create your optimal schedule, I need to understand more details:

**QUESTION SET A - Tasks & Priorities:**
1. What are ALL your tasks for this day? (Please list everything, even small items)
2. Which 3 tasks are absolutely critical to complete today?
3. Are there any tasks with hard deadlines or specific time requirements?

**QUESTION SET B - Work Style & Energy:**
4. When do you feel most focused and energetic? (Morning/Afternoon/Evening)
5. Do you prefer longer focused blocks or shorter, varied tasks?
6. How much buffer time do you typically need between meetings/tasks?

**QUESTION SET C - Constraints & Preferences:**
7. Are there any tasks you want to avoid during certain times?
8. Do you have any recurring commitments (lunch, breaks, etc.)?
9. What time do you want to finish work today?"

**Phase 3: Schedule Generation**
"Based on your responses, here's your optimized schedule using time-blocking methodology:

[GENERATE COMPLETE MARKDOWN TABLE HERE]

**Phase 4: Refinement Questions**
After presenting the schedule, ALWAYS ask:
"How does this schedule look? I can adjust:
- Task timing and duration
- Priority levels and sequencing  
- Buffer time between activities
- Energy level matching

What would you like me to modify?"

**CRITICAL RULES:**
- NEVER generate a schedule without asking follow-up questions first
- ALWAYS use the exact table format specified above
- Include at least 5 rows of scheduled activities
- Energy Level must use 1-5 lightning bolts (⚡ to ⚡⚡⚡⚡⚡)
- Priority must be exactly: High, Medium, or Low""",

"risk_register_builder": """**Role**: AI Risk Management Strategist | ISO 31000 Certified Expert

**MANDATORY OUTPUT FORMAT**: Always generate complete markdown tables with this exact structure:
| Risk ID | Risk Description | Likelihood | Impact | Risk Score | Category | Mitigation Strategy |
|---------|------------------|------------|--------|------------|----------|-------------------|
| RR-001 | [specific risk] | 3 | 4 | 12 | Operational | [specific action] |

**INTERACTION PROCESS**:

**Phase 1: Initial Project Understanding**
"Hello! I'll help you create a comprehensive risk register through a systematic analysis process.

Let's start with your project basics:
- What is the name and main objective of your project/initiative?
- What industry or sector does this involve?
- What's your estimated timeline and budget range?"

**Phase 2: Systematic Follow-Up Questions**
After receiving initial input, ALWAYS ask these follow-up questions in sequence:

**QUESTION SET A - Project Scope & Context:**
1. Who are the key stakeholders and what are their expectations?
2. What similar projects have you or your organization done before?
3. What went wrong in previous similar projects (lessons learned)?

**QUESTION SET B - Operational Environment:**
4. What external vendors, suppliers, or partners are involved?
5. What technology systems or infrastructure does this project depend on?
6. What regulatory requirements or compliance standards apply?

**QUESTION SET C - Resource & Timeline Risks:**
7. What are your biggest concerns about meeting the timeline?
8. Where might you face resource constraints (people, budget, equipment)?
9. What could cause scope creep or requirement changes?

**QUESTION SET D - Strategic & Market Risks:**
10. How might market conditions or competitor actions affect this project?
11. What internal organizational changes could impact the project?
12. What would happen if key team members became unavailable?"

**Phase 3: Risk Register Generation**
"Based on your responses, here's your comprehensive risk register:

[GENERATE COMPLETE MARKDOWN TABLE HERE]

**Risk Scoring Guide:**
- Likelihood: 1=Very Low, 2=Low, 3=Medium, 4=High, 5=Very High
- Impact: 1=Minimal, 2=Minor, 3=Moderate, 4=Major, 5=Critical
- Risk Score = Likelihood × Impact (1-25 scale)

**Phase 4: Refinement Questions**
After presenting the risk register, ALWAYS ask:
"How does this risk assessment look? I can help you:
- Add or modify specific risks you're concerned about
- Adjust likelihood or impact scores
- Develop more detailed mitigation strategies
- Prioritize which risks need immediate attention

What risks should we focus on or adjust?"

**CRITICAL RULES:**
- NEVER generate a risk register without asking follow-up questions first
- ALWAYS use the exact table format specified above
- Include at least 5 distinct risks across different categories
- Categories must be: Operational, Financial, Technical, Strategic, or Compliance
- Risk IDs must follow format: RR-001, RR-002, etc.""",

"meeting_summarizer": """**Role**: Professional AI Meeting Secretary & Action Item Specialist

**MANDATORY OUTPUT FORMAT**: Always generate complete markdown tables with this exact structure:
| Action Item | Owner | Deadline | Priority | Status | Notes |
|-------------|-------|----------|----------|--------|-------|
| [specific task] | [name] | 2025-06-20 | High | Open | [details] |

**INTERACTION PROCESS**:

**Phase 1: Initial Meeting Context**
"Hello! I'll help you create a comprehensive meeting summary with clear action items through a structured process.

Please start by sharing:
- What type of meeting was this? (team meeting, client call, planning session, etc.)
- When did it take place and how long was it?
- Who were the main participants?"

**Phase 2: Systematic Follow-Up Questions**
After receiving initial input, ALWAYS ask these follow-up questions in sequence:

**QUESTION SET A - Meeting Structure & Content:**
1. What was the main purpose or agenda of this meeting?
2. What were the key topics or agenda items discussed?
3. Can you share any notes, transcripts, or recordings you have?

**QUESTION SET B - Decisions & Outcomes:**
4. What specific decisions were made during the meeting?
5. Were there any disagreements or unresolved issues?
6. What problems or challenges were identified?

**QUESTION SET C - Action Items & Next Steps:**
7. What specific tasks or action items were assigned?
8. Who is responsible for each action item?
9. What are the deadlines or target completion dates?

**QUESTION SET D - Follow-Up & Context:**
10. Are there any dependencies between action items?
11. What resources or support might be needed to complete these actions?
12. When is the next meeting or check-in scheduled?"

**Phase 3: Meeting Summary Generation**
"Based on your responses, here's your comprehensive meeting summary:

**Meeting Overview:**
- **Date & Time:** [date and time]
- **Duration:** [duration]
- **Attendees:** [participant list with roles]
- **Purpose:** [meeting objective]

**Key Discussion Points:**
[Organized summary of main topics]

**Decisions Made:**
[List of specific decisions with context]

**Action Items:**
[GENERATE COMPLETE MARKDOWN TABLE HERE]

**Unresolved Issues:**
[Items requiring follow-up]

**Phase 4: Refinement Questions**
After presenting the summary, ALWAYS ask:
"How does this meeting summary look? I can help you:
- Add or clarify any missing action items
- Adjust deadlines or ownership assignments
- Include additional context or decisions
- Reorganize the summary structure

What would you like me to modify or add?"

**CRITICAL RULES:**
- NEVER generate a summary without asking follow-up questions first
- ALWAYS use the exact table format specified above
- Include at least 3 action items (create generic ones if none provided)
- Priority must be exactly: High, Medium, or Low
- Status must be exactly: Open, In Progress, or Completed
- Deadline format must be: YYYY-MM-DD"""
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
    if not markdown:
        print("DEBUG: No markdown provided to parse")
        return []
    
    print(f"DEBUG: Full markdown to parse: {markdown}")
    
    # Split into lines and clean up
    lines = [line.strip() for line in markdown.strip().split('\n')]
    
    # Find all lines that contain table data (have multiple |)
    table_lines = []
    for line in lines:
        if line.count('|') >= 3:  # At least 3 pipes for a proper table row
            table_lines.append(line)
    
    print(f"DEBUG: Found {len(table_lines)} potential table lines")
    
    if len(table_lines) < 2:
        print("DEBUG: Not enough table lines found")
        return []
    
    # Parse headers from first line
    header_line = table_lines[0]
    headers = []
    header_parts = header_line.split('|')
    for part in header_parts:
        cleaned = part.strip()
        if cleaned and cleaned not in ['', '-', ':']:
            headers.append(cleaned)
    
    print(f"DEBUG: Parsed headers: {headers}")
    
    if len(headers) < 2:
        print("DEBUG: Not enough valid headers found")
        return []
    
    # Skip separator line (usually contains dashes)
    data_start_index = 1
    if len(table_lines) > 1 and '-' in table_lines[1]:
        data_start_index = 2
    
    # Parse data rows
    rows = []
    for i in range(data_start_index, len(table_lines)):
        line = table_lines[i]
        cells = []
        cell_parts = line.split('|')
        
        for part in cell_parts:
            cleaned = part.strip()
            if cleaned:  # Only add non-empty cells
                cells.append(cleaned)
        
        print(f"DEBUG: Row {i-data_start_index+1} cells: {cells}")
        
        # Match cells to headers
        if len(cells) >= len(headers):
            row_data = {}
            for j, header in enumerate(headers):
                if j < len(cells):
                    row_data[header] = cells[j]
                else:
                    row_data[header] = ''
            rows.append(row_data)
    
    print(f"DEBUG: Successfully parsed {len(rows)} complete rows")
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
        # UPGRADED: Using GPT-4o (latest and most capable model)
        response = openai.ChatCompletion.create(
            model="gpt-4o",  # Changed from gpt-3.5-turbo
            messages=chat_history,
            max_tokens=800,  # Increased for more complete responses
            temperature=0.3,  # Lowered for more consistent outputs
            top_p=0.9,  # Added for better consistency
            frequency_penalty=0.1,  # Reduces repetition
            presence_penalty=0.1   # Encourages diverse content
        )
        reply = response['choices'][0]['message']['content']
        chat_history.append({"role": "assistant", "content": reply})
        session[history_key] = chat_history

        # Enhanced table detection with stricter patterns
        table_patterns = [
            # Strict pattern for complete tables with proper headers
            r'(\|[^|\n]+\|[^|\n]*\n\|[-:\s|]+\|\n(?:\|[^|\n]*\|[^|\n]*\n)+)',
            # Backup pattern for tables with at least 3 rows
            r'(\|.*\|(?:\n\|.*\|){2,})',
            # Final fallback for any table structure
            r'(\|[^|]*\|(?:\s*\n\s*\|[^|]*\|)*)'
        ]
        
        markdown_table = None
        for i, pattern in enumerate(table_patterns):
            matches = re.findall(pattern, reply, re.MULTILINE | re.DOTALL)
            if matches:
                # Find the longest, most complete match
                markdown_table = max(matches, key=len)
                print(f"DEBUG: Table found with pattern {i+1} for {prompt_name}")
                break
        
        # Store the complete table
        table_key = f'{prompt_name}_last_table'
        session[table_key] = markdown_table
        session.permanent = True
        session.modified = True
        
        return jsonify({'reply': reply})
    except Exception as e:
        print(f"ERROR in chat_api: {str(e)}")
        return jsonify({'error': str(e)}), 500
        
@app.route('/reset/<prompt_name>', methods=['POST'])
def reset_chat(prompt_name):
    history_key = f'chat_history_{prompt_name}'
    session.pop(history_key, None)  # Remove chat history for this prompt
    return jsonify({'success': True})

@app.route('/export/<prompt_name>/csv')
def export_csv(prompt_name):
    table_key = f'{prompt_name}_last_table'
    table_md = session.get(table_key)
    
    print(f"DEBUG CSV Export: Raw table: {table_md}")
    
    if not table_md:
        return f"No table found to export. Session keys: {list(session.keys())}", 400
    
    rows = parse_markdown_table(table_md)
    if not rows:
        # Try to create a minimal export from the raw data
        if '|' in table_md:
            cells = [c.strip() for c in table_md.split('|') if c.strip()]
            if len(cells) >= 2:
                # Create a simple two-column export
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(['Data', 'Value'])  # Generic headers
                for i in range(0, len(cells), 2):
                    if i + 1 < len(cells):
                        writer.writerow([cells[i], cells[i+1]])
                    else:
                        writer.writerow([cells[i], ''])
                
                response = make_response(output.getvalue())
                response.headers["Content-Disposition"] = f"attachment; filename={prompt_name}_export.csv"
                response.headers["Content-type"] = "text/csv"
                return response
        
        return f"Table parsing failed. Raw data: {table_md}", 400

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename={prompt_name}_export.csv"
    response.headers["Content-type"] = "text/csv"
    return response

@app.route('/export/<prompt_name>/pdf')
def export_html_as_pdf(prompt_name):
    table_md = session.get(f'{prompt_name}_last_table')
    if not table_md:
        return "No table found to export.", 400
    
    rows = parse_markdown_table(table_md)
    if not rows:
        return "Table parsing failed.", 400
    
    # Generate complete HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{prompt_name.replace('_', ' ').title()} Export</title>
        <style>
            body {{ 
                font-family: 'Segoe UI', Arial, sans-serif; 
                margin: 20px; 
                background: white;
            }}
            h1 {{ 
                color: #2155CD; 
                border-bottom: 2px solid #2155CD;
                padding-bottom: 10px;
            }}
            table {{ 
                border-collapse: collapse; 
                width: 100%; 
                margin-top: 20px;
            }}
            th, td {{ 
                border: 1px solid #ddd; 
                padding: 12px 8px; 
                text-align: left; 
            }}
            th {{ 
                background-color: #2155CD; 
                color: white;
                font-weight: 600;
            }}
            tr:nth-child(even) {{ background-color: #f8f9fa; }}
        </style>
    </head>
    <body>
        <h1>{prompt_name.replace('_', ' ').title()} Export</h1>
        <table>
            <thead>
                <tr>
    """
    
    # Add headers
    for header in rows[0].keys():
        html_content += f"<th>{header}</th>"
    html_content += "</tr></thead><tbody>"
    
    # Add data rows
    for row in rows:
        html_content += "<tr>"
        for cell in row.values():
            html_content += f"<td>{cell}</td>"
        html_content += "</tr>"
    
    html_content += f"""
            </tbody>
        </table>
        <div style="margin-top: 20px; font-size: 0.9em; color: #666;">
            <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </body>
    </html>
    """
    
    response = make_response(html_content)
    response.headers["Content-Disposition"] = f"attachment; filename={prompt_name}_export.html"
    response.headers["Content-type"] = "text/html"
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
    today = datetime.today().date()
    
    for row in rows:
        # Try different column name variations
        time_block = (row.get('Time Block') or row.get('Time') or 
                     row.get('Timeblock') or row.get('Time Slot'))
        task = (row.get('Task') or row.get('Task Name') or 
               row.get('Activity') or row.get('Description'))
        
        if not time_block or not task:
            continue
        
        # Improved time parsing
        time_patterns = [
            r'(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\s*([APMapm]+)',
            r'(\d{1,2}):(\d{2})\s*([APMapm]+)\s*-\s*(\d{1,2}):(\d{2})\s*([APMapm]+)',
            r'(\d{1,2})\s*-\s*(\d{1,2})\s*([APMapm]+)'
        ]
        
        start_dt = None
        end_dt = None
        
        for pattern in time_patterns:
            match = re.search(pattern, time_block, re.IGNORECASE)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 5:  # Full time format
                        start_hour, start_min, end_hour, end_min, period = groups
                        period = period.upper()
                        
                        # Convert to 24-hour format
                        start_hour = int(start_hour)
                        end_hour = int(end_hour)
                        
                        if 'PM' in period and start_hour != 12:
                            start_hour += 12
                        elif 'AM' in period and start_hour == 12:
                            start_hour = 0
                            
                        if 'PM' in period and end_hour != 12:
                            end_hour += 12
                        elif 'AM' in period and end_hour == 12:
                            end_hour = 0
                        
                        start_dt = datetime.combine(today, datetime.min.time().replace(
                            hour=start_hour, minute=int(start_min)))
                        end_dt = datetime.combine(today, datetime.min.time().replace(
                            hour=end_hour, minute=int(end_min)))
                        break
                except (ValueError, IndexError):
                    continue
        
        if start_dt and end_dt:
            e = Event()
            e.name = task
            e.begin = start_dt
            e.end = end_dt
            e.description = row.get('Notes', '') or row.get('Priority', '')
            cal.events.add(e)
    
    ics_content = str(cal)
    return Response(ics_content, mimetype="text/calendar",
                    headers={"Content-Disposition": "attachment; filename=schedule.ics"})

@app.route('/user-guide')
def user_guide():
    """Serve the user guide PDF"""
    return send_from_directory('static', 'user_guide.pdf', as_attachment=False)

@app.errorhandler(404)
def not_found(e):
    return "Page not found or not allowed.", 404



if __name__ == '__main__':
    # For local development
    app.run(debug=True)
else:
    # For production deployment on Render
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
