import os
import json
import csv
from datetime import datetime
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage
from langchain.tools import tool
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate
from langchain import hub

# Set your Google API key
os.environ["GOOGLE_API_KEY"] = "AIzaSyDjh1LP2YSKKDAx9vh3sCF5wBkbCHUqWU0" 

# Initialize FastAPI app
app = FastAPI(title="Lead Generation Chatbot API", version="1.0.0")

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="templates")
# Note: static directory not needed for current implementation

# Dummy in-memory calendar: dict of date to dict of time: client_name (None if free)
# Day-wise organization
calendar: Dict[str, Dict[str, Optional[str]]] = {
    "2025-08-20": {"10:00 AM": None, "11:00 AM": None},
    "2025-08-21": {"2:00 PM": None, "3:00 PM": None},
    "2025-08-22": {"9:30 AM": None, "10:30 AM": None},
}

# Pydantic models for API requests/responses
class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    available_slots: Optional[List[str]] = None

class BookingRequest(BaseModel):
    slot: str
    client_name: str

class BookingResponse(BaseModel):
    message: str
    success: bool

class FormData(BaseModel):
    name: str
    email: str
    phone: str
    company: str
    selected_slot: str
    message: str = ""

# Tools
@tool
def get_available_slots() -> str:
    """Get list of available time slots as JSON list of 'date time' strings."""
    available = []
    for date, times in calendar.items():
        for time, booked in times.items():
            if booked is None:
                available.append(f"{date} {time}")
    return json.dumps(available)

@tool
def book_meeting(slot: str, client_name: str) -> str:
    """Book a meeting for the given slot (format 'date time') and client name. Returns confirmation or error."""
    try:
        date, time = slot.split(" ", 1)
        if date in calendar and time in calendar[date] and calendar[date][time] is None:
            calendar[date][time] = client_name
            return f"Booked {slot} for {client_name}. Confirmation sent! Calendar updated."
        else:
            return f"Slot {slot} not available or invalid."
    except:
        return "Error booking slot."

@tool
def process_meeting_booking(booking_data: str) -> str:
    """Process a complete meeting booking with all client details. This tool handles the entire booking process independently."""
    try:
        # Parse the booking data (JSON string)
        data = json.loads(booking_data)
        
        # Extract booking information
        slot = data.get('selected_slot', '')
        name = data.get('name', '')
        email = data.get('email', '')
        phone = data.get('phone', '')
        company = data.get('company', '')
        message = data.get('message', '')
        
        # Validate required fields
        if not all([slot, name, email, phone, company]):
            return "Error: Missing required booking information"
        
        # Save to CSV
        csv_file = "meeting_bookings.csv"
        file_exists = os.path.exists(csv_file)
        
        with open(csv_file, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            
            # Write header if file doesn't exist
            if not file_exists:
                writer.writerow(['Timestamp', 'Name', 'Email', 'Phone', 'Company', 'Selected Slot', 'Message'])
            
            # Write data
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                name, email, phone, company, slot, message
            ])
        
        # Update calendar
        try:
            date, time = slot.split(" ", 1)
            if date in calendar and time in calendar[date]:
                calendar[date][time] = name
        except:
            pass
        
        return f"SUCCESS: Meeting booked for {name} at {slot}. Confirmation sent to {email}!"
        
    except Exception as e:
        return f"Error processing booking: {str(e)}"

tools = [get_available_slots, book_meeting, process_meeting_booking]

# LLM Setup
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0.7,
    max_tokens=500,
)

# System Prompt for AorySoft lead generation chatbot
system_message = SystemMessage(content="""You are a professional and friendly lead generation chatbot for AorySoft, a leading software house. Your mission is to help potential clients and naturally guide them toward scheduling meetings.

COMPANY: AorySoft - We develop custom software solutions, web applications, mobile apps, and enterprise software for businesses of all sizes.

AVAILABLE TOOLS:
1. get_available_slots() - Get available meeting time slots
2. book_meeting(slot, client_name) - Book a meeting for a specific time and client

CONVERSATION STRATEGY:
- Start conversations naturally and professionally
- Ask 2-3 targeted questions to understand their business challenges
- Show genuine interest and empathy
- When they express clear pain points or interest, suggest a meeting
- Be helpful and informative, not pushy or passive

RESPONSE PRIORITY:
1. IMMEDIATE: If they directly ask to meet/schedule - show slots right away
2. GUIDED: If they're exploring - ask questions to understand needs first
3. NATURAL: Build rapport and guide toward meetings when appropriate

MEETING TRIGGERS - Use get_available_slots() when:
- User explicitly asks: "can we meet?", "schedule a meeting", "book a call", "I want to meet", "let's meet"
- User shows clear interest: "I'd be open to hearing a plan", "tell me more about solutions"
- After understanding their needs (2-3 exchanges), they seem ready for next steps

IMMEDIATE MEETING REQUESTS:
- If someone directly asks to meet, schedule, or book - IMMEDIATELY show available slots
- Don't ask more questions if they're already ready to meet
- Be responsive and efficient for direct requests

AVOID:
- Don't push meetings immediately (first understand their needs)
- Don't be too passive (guide them toward solutions)
- Don't be aggressive (build rapport first)

Use the ReAct format to think through what the user needs and decide whether to use tools.

Be professional, helpful, and guide conversations naturally toward meetings when appropriate.
""")

# Custom function to handle calendar widget generation after tool call
def handle_calendar_response(tool_result):
    """Convert tool result to calendar widget HTML"""
    try:
        slots_list = json.loads(tool_result)
        calendar_html = generate_calendar_widget(slots_list)
        
        return f"""Perfect! I'd love to schedule a meeting to discuss how AorySoft can help solve your business challenges. 

Please select your preferred date and time from the interactive calendar below:

{calendar_html}

Simply click on any available time slot to book your meeting instantly! 🚀"""
    except Exception as e:
        print(f"Error generating calendar: {e}")
        return tool_result

# Generate beautiful calendar widget HTML
def generate_calendar_widget(slots_list):
    """Generate a beautiful interactive calendar widget HTML"""
    
    # Parse slots and organize by date
    slots_by_date = {}
    for slot in slots_list:
        date_part = slot.split(' ')[0]  # "2025-08-20"
        time_part = ' '.join(slot.split(' ')[1:])  # "10:00 AM"
        
        if date_part not in slots_by_date:
            slots_by_date[date_part] = []
        slots_by_date[date_part].append(time_part)
    
    # Generate calendar HTML
    calendar_html = """
<div style="max-width: 800px; margin: 20px auto; font-family: 'Segoe UI', Arial, sans-serif;">
    <style>
        .aorysoft-calendar {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            border: 2px solid #3498db;
        }
        .calendar-header {
            text-align: center;
            margin-bottom: 25px;
            color: #2c3e50;
        }
        .calendar-title {
            font-size: 1.8rem;
            font-weight: bold;
            margin-bottom: 10px;
            color: #3498db;
        }
        .calendar-subtitle {
            font-size: 1.1rem;
            color: #6c757d;
        }
        .calendar-dates {
            display: grid;
            gap: 20px;
            margin-bottom: 20px;
        }
        .date-section {
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.08);
            border: 1px solid #e9ecef;
            transition: all 0.3s ease;
        }
        .date-section:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(52, 152, 219, 0.15);
            border-color: #3498db;
        }
        .date-header {
            font-size: 1.3rem;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 15px;
            text-align: center;
            padding-bottom: 10px;
            border-bottom: 2px solid #3498db;
        }
        .time-slots {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
            gap: 12px;
        }
        .time-slot {
            background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
            color: white;
            padding: 15px 20px;
            border-radius: 10px;
            text-align: center;
            font-weight: 600;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s ease;
            border: none;
            box-shadow: 0 4px 12px rgba(52, 152, 219, 0.3);
        }
        .time-slot:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(52, 152, 219, 0.4);
            background: linear-gradient(135deg, #2980b9 0%, #1f5f99 100%);
        }
        .time-slot:active {
            transform: translateY(0);
            box-shadow: 0 2px 8px rgba(52, 152, 219, 0.3);
        }
        .calendar-footer {
            text-align: center;
            margin-top: 25px;
            padding-top: 20px;
            border-top: 2px solid #e9ecef;
            color: #6c757d;
            font-size: 1rem;
        }
        .booking-form {
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin-top: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.08);
            display: none;
        }
        .booking-form.show {
            display: block;
            animation: slideDown 0.3s ease;
        }
        @keyframes slideDown {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #2c3e50;
        }
        .form-group input, .form-group textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s ease;
        }
        .form-group input:focus, .form-group textarea:focus {
            outline: none;
            border-color: #3498db;
        }
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        .submit-btn {
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
            padding: 15px 30px;
            border: none;
            border-radius: 10px;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
            transition: all 0.3s ease;
        }
        .submit-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(40, 167, 69, 0.4);
        }
        .selected-slot {
            background: #28a745;
            color: white;
            padding: 10px 15px;
            border-radius: 8px;
            text-align: center;
            margin-bottom: 20px;
            font-weight: bold;
        }
        @media (max-width: 768px) {
            .time-slots {
                grid-template-columns: repeat(2, 1fr);
            }
            .form-row {
                grid-template-columns: 1fr;
            }
            .aorysoft-calendar {
                padding: 20px;
            }
        }
    </style>
    
    <div class="aorysoft-calendar">
        <div class="calendar-header">
            <div class="calendar-title">🚀 Schedule Your AorySoft Meeting</div>
            <div class="calendar-subtitle">Select your preferred date and time below</div>
        </div>
        
        <div class="calendar-dates">
"""
    
    # Add date sections
    for date_str, times in sorted(slots_by_date.items()):
        # Format date for display
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        formatted_date = date_obj.strftime('%A, %B %d, %Y')
        
        calendar_html += f"""
            <div class="date-section">
                <div class="date-header">{formatted_date}</div>
                <div class="time-slots">
"""
        
        # Add time slots
        for time_slot in times:
            full_slot = f"{date_str} {time_slot}"
            calendar_html += f"""
                    <button class="time-slot" onclick="selectTimeSlot('{full_slot}', this)">
                        {time_slot}
                    </button>
"""
        
        calendar_html += """
                </div>
            </div>
"""
    
    # Complete the calendar HTML
    calendar_html += """
        </div>
        
        <div class="calendar-footer">
            💡 Click any time slot above to book your meeting instantly!
        </div>
        
        <div id="bookingForm" class="booking-form">
            <div class="selected-slot" id="selectedSlotDisplay"></div>
            <form onsubmit="submitBooking(event)">
                <div class="form-row">
                    <div class="form-group">
                        <label for="clientName">Full Name *</label>
                        <input type="text" id="clientName" name="name" required>
                    </div>
                    <div class="form-group">
                        <label for="clientEmail">Email *</label>
                        <input type="email" id="clientEmail" name="email" required>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label for="clientPhone">Phone *</label>
                        <input type="tel" id="clientPhone" name="phone" required>
                    </div>
                    <div class="form-group">
                        <label for="clientCompany">Company *</label>
                        <input type="text" id="clientCompany" name="company" required>
                    </div>
                </div>
                <div class="form-group">
                    <label for="clientMessage">Project Details (Optional)</label>
                    <textarea id="clientMessage" name="message" rows="3" placeholder="Tell us about your project and challenges..."></textarea>
                </div>
                <button type="submit" class="submit-btn">🚀 Confirm Meeting</button>
            </form>
        </div>
    </div>
    
            <script>
        // Debug: Log when calendar loads
        console.log('Calendar widget loaded with slots:', {slots_list});
        console.log('Global functions available:', typeof window.selectTimeSlot, typeof window.submitBooking);
    </script>
</div>
"""
    
    return calendar_html

# Pure ReAct implementation that actually works (no forced tool usage)
class PureReActAgent:
    def __init__(self, llm, tools, system_prompt):
        self.llm = llm
        self.tools = {tool.name: tool for tool in tools}
        self.system_prompt = system_prompt
        self.tool_names = list(self.tools.keys())
    
    def invoke(self, input_data):
        user_input = input_data["input"]
        
        # ReAct reasoning prompt
        tools_desc = "\n".join([f"- {name}: {tool.description}" for name, tool in self.tools.items()])
        
        prompt = f"""You are AorySoft's lead generation assistant. Use ReAct reasoning to help users.

SYSTEM CONTEXT:
{self.system_prompt}

AVAILABLE TOOLS:
{tools_desc}

INSTRUCTIONS:
1. Think step by step using the format below
2. Only use tools when actually needed
3. For greetings, general questions - respond directly without tools
4. For meeting requests - use get_available_slots tool

FORMAT:
Thought: [your reasoning about what to do]
Action: [tool name if needed, or "no tool needed"]
Action Input: [input for tool if using one]
Observation: [result from tool]
Final Answer: [your response to the user]

User: {user_input}

Thought:"""

        try:
            # Get LLM response
            response = self.llm.invoke(prompt)
            response_text = response.content
            
            print(f"ReAct Response: {response_text}")
            
            # Parse and execute any tool calls
            if "Action:" in response_text and "no tool needed" not in response_text.lower():
                lines = response_text.split('\n')
                action_line = None
                action_input_line = None
                
                for i, line in enumerate(lines):
                    if line.strip().startswith('Action:'):
                        action_line = line.strip()
                        # Look for Action Input on next line
                        if i + 1 < len(lines) and lines[i + 1].strip().startswith('Action Input:'):
                            action_input_line = lines[i + 1].strip()
                        break
                
                if action_line:
                    # Extract tool name
                    tool_name = action_line.replace('Action:', '').strip()
                    
                    if tool_name in self.tools:
                        print(f"Executing tool: {tool_name}")
                        
                        # Execute tool
                        if tool_name == "get_available_slots":
                            tool_result = self.tools[tool_name].invoke("")
                            
                            # Convert to calendar widget
                            try:
                                slots_list = json.loads(tool_result)
                                calendar_html = generate_calendar_widget(slots_list)
                                
                                final_response = f"""Perfect! I'd love to schedule a meeting to discuss how AorySoft can help solve your business challenges. 

Please select your preferred date and time from the interactive calendar below:

{calendar_html}

Simply click on any available time slot to book your meeting instantly! 🚀"""
                                
                                return {"output": final_response}
                            except:
                                return {"output": f"I can help you schedule a meeting. Available slots: {tool_result}"}
                        else:
                            # For other tools
                            action_input = action_input_line.replace('Action Input:', '').strip() if action_input_line else ""
                            tool_result = self.tools[tool_name].invoke(action_input)
                            return {"output": f"Tool result: {tool_result}"}
            
            # Extract final answer if no tool was used
            if "Final Answer:" in response_text:
                final_answer = response_text.split("Final Answer:")[-1].strip()
                return {"output": final_answer}
            else:
                # Fallback - return the thinking part
                return {"output": "Hi there! I'm AorySoft's lead generation assistant. I'm here to help you understand how our custom software solutions can solve your business challenges. What specific problems are you facing in your business today?"}
                
        except Exception as e:
            print(f"Error in ReAct processing: {e}")
            return {"output": "Hi there! I'm AorySoft's lead generation assistant. I'm here to help you understand how our custom software solutions can solve your business challenges. What would you like to discuss?"}

# Create the pure ReAct agent
agent_executor = PureReActAgent(llm, tools, system_message.content)

# API Endpoints
@app.get("/", response_class=HTMLResponse)
async def get_html_ui():
    """Serve the HTML UI for testing the API"""
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Error: index.html not found</h1>", status_code=404)

@app.get("/form", response_class=HTMLResponse)
async def get_booking_form():
    """Serve the separate booking form HTML"""
    try:
        with open("form.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Error: form.html not found</h1>", status_code=404)

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Chat with the lead generation chatbot"""
    try:
        # Invoke the pure ReAct agent
        response = agent_executor.invoke({"input": request.message})
        
        # Get the agent's response (already cleaned by the agent)
        bot_response = response["output"]
        
        print(f"Final bot response: {bot_response}")  # Debug print
        
        return ChatResponse(response=bot_response, available_slots=None)
    
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")  # Debug print
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

@app.post("/book", response_model=BookingResponse)
async def book_meeting_endpoint(request: BookingRequest):
    """Book a meeting slot"""
    try:
        # Invoke agent with booking request
        response = agent_executor.invoke({"input": f"Book slot {request.slot} for {request.client_name}"})
        
        booking_result = response["output"]
        
        # Check if booking was successful
        success = "Booked" in booking_result and "Confirmation sent" in booking_result
        
        return BookingResponse(message=booking_result, success=success)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error booking meeting: {str(e)}")

@app.get("/calendar")
async def get_calendar():
    """Get current calendar state"""
    return calendar

def save_to_csv(form_data: FormData):
    """Save form data to CSV file"""
    csv_file = "meeting_bookings.csv"
    file_exists = os.path.exists(csv_file)
    
    with open(csv_file, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        
        # Write header if file doesn't exist
        if not file_exists:
            writer.writerow(['Timestamp', 'Name', 'Email', 'Phone', 'Company', 'Selected Slot', 'Message'])
        
        # Write data
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            form_data.name,
            form_data.email,
            form_data.phone,
            form_data.company,
            form_data.selected_slot,
            form_data.message
        ])
    
    return True

@app.post("/save-form")
async def save_form_data(form_data: FormData):
    """Save form data to CSV"""
    try:
        save_to_csv(form_data)
        
        # Also update the calendar to mark the slot as booked
        try:
            date, time = form_data.selected_slot.split(" ", 1)
            if date in calendar and time in calendar[date]:
                calendar[date][time] = form_data.name
        except:
            pass  # If calendar update fails, don't fail the form submission
        
        return {"success": True, "message": "Form data saved successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving form data: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Lead Generation Chatbot API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)