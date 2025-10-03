# AorySoft Lead Generation Chatbot

A sophisticated AI-powered lead generation chatbot built with FastAPI and Google's Gemini AI. This application helps AorySoft engage with potential clients, understand their business challenges, and seamlessly schedule meetings through an interactive calendar interface.

## 🚀 Features

- **AI-Powered Conversations**: Uses Google Gemini AI for natural, intelligent conversations
- **Lead Qualification**: Automatically identifies and qualifies potential leads
- **Interactive Calendar**: Beautiful, responsive calendar widget for meeting scheduling
- **Real-time Chat Interface**: Modern, mobile-friendly chat UI
- **Meeting Management**: Automated booking system with CSV data storage
- **ReAct Agent**: Advanced reasoning and action-taking capabilities

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python)
- **AI/LLM**: Google Gemini 1.5 Flash via LangChain
- **Frontend**: HTML5, CSS3, JavaScript
- **Data Storage**: CSV files for meeting bookings
- **Deployment**: Uvicorn ASGI server

## 📋 Prerequisites

- Python 3.8+
- Google API Key for Gemini AI
- pip (Python package manager)

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd LG
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables
Create a `.env` file in the root directory:
```env
GOOGLE_API_KEY=your_google_api_key_here
```

Or set the environment variable directly:
```bash
# On Windows
set GOOGLE_API_KEY=your_google_api_key_here

# On macOS/Linux
export GOOGLE_API_KEY=your_google_api_key_here
```

### 5. Run the Application
```bash
python main.py
```

The application will be available at `http://localhost:8001`

## 📁 Project Structure

```
LG/
├── main.py                 # FastAPI application and AI agent
├── requirements.txt        # Python dependencies
├── index.html             # Main chat interface
├── form.html              # Booking form page
├── meeting_bookings.csv   # Meeting data storage
├── templates/             # Jinja2 templates directory
├── venv/                  # Virtual environment
└── README.md              # This file
```

## 🔧 API Endpoints

### Chat Interface
- `GET /` - Main chat interface
- `POST /chat` - Send message to AI chatbot
- `GET /form` - Booking form page

### Meeting Management
- `POST /book` - Book a meeting slot
- `POST /save-form` - Save form data to CSV
- `GET /calendar` - Get current calendar state

### Utility
- `GET /health` - Health check endpoint

## 🤖 How It Works

### 1. Lead Generation Process
1. User visits the chat interface
2. AI assistant greets and asks about business challenges
3. AI uses ReAct reasoning to understand user needs
4. When appropriate, AI suggests scheduling a meeting
5. Interactive calendar widget is displayed
6. User selects time slot and fills booking form
7. Meeting is automatically booked and data saved

### 2. AI Agent Capabilities
- **Natural Conversation**: Engages users with professional, helpful responses
- **Lead Qualification**: Asks targeted questions to understand business needs
- **Meeting Scheduling**: Automatically suggests meetings when appropriate
- **Tool Usage**: Uses available tools for calendar management and booking

### 3. Calendar System
- Pre-configured available time slots
- Real-time availability checking
- Automatic slot booking and updates
- Beautiful, responsive calendar widget

## 🎨 Customization

### Adding New Time Slots
Edit the `calendar` dictionary in `main.py`:
```python
calendar: Dict[str, Dict[str, Optional[str]]] = {
    "2025-08-20": {"10:00 AM": None, "11:00 AM": None},
    "2025-08-21": {"2:00 PM": None, "3:00 PM": None},
    # Add more dates and times as needed
}
```

### Modifying AI Behavior
Update the system prompt in `main.py` to change the AI's personality and responses:
```python
system_message = SystemMessage(content="""Your custom prompt here...""")
```

### Styling the Interface
Modify the CSS in `index.html` and `form.html` to match your brand colors and styling.

## 📊 Data Storage

Meeting bookings are automatically saved to `meeting_bookings.csv` with the following columns:
- Timestamp
- Name
- Email
- Phone
- Company
- Selected Slot
- Message

## 🔒 Security Notes

- **API Key Security**: Never commit your Google API key to version control
- **Environment Variables**: Use environment variables for sensitive data
- **Input Validation**: All form inputs are validated using Pydantic models
- **CSRF Protection**: Consider adding CSRF protection for production use

## 🚀 Deployment

### Local Development
```bash
python main.py
```

### Production Deployment
1. Set up a production WSGI server (e.g., Gunicorn with Uvicorn workers)
2. Configure reverse proxy (e.g., Nginx)
3. Set up SSL certificates
4. Configure environment variables securely
5. Set up monitoring and logging

### Docker Deployment (Optional)
Create a `Dockerfile`:
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8001
CMD ["python", "main.py"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation

## 🔄 Version History

- **v1.0.0** - Initial release with basic chat and booking functionality
- **v1.1.0** - Added interactive calendar widget
- **v1.2.0** - Implemented ReAct agent for better reasoning

---

**Built with ❤️ by AorySoft Team**
