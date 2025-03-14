BTModel Web - AI Multi-Agent Business Analysis
 * A web application that uses OpenAI-powered agents to analyze companies from multiple perspectives.

Overview
This application simulates a collaborative discussion between AI agents representing different business roles:

  * Business Strategist: Focuses on market positioning and competitive advantage
  * Product Manager: Analyzes product opportunities and user experience
  * Technology Officer: Examines technical feasibility and implementation challenges
  * Innovation Analyst: Explores emerging technology trends and innovation opportunities

  The application first researches a company using web search, then conducts a two-round discussion between the agents, and finally generates an executive summary.

File Structure

  * app.py: Main Flask application with routes and SocketIO events
  * agents.py: AI agent classes that interact with OpenAI API
  * tools.py: Web search functionality using DuckDuckGo
  * templates/: HTML templates for the web interface
  * requirements.txt: Project dependencies
  * .env.example: Example environment variables file

Getting Started

  * Clone the repository
  * Create a virtual environment and install dependencies:
  * Copypython -m venv venv
  * source venv/bin/activate  # On Windows: venv\Scripts\activate
  * pip install -r requirements.txt

  Create a .env file based on .env.example and add your OpenAI API key:
  * OPENAI_API_KEY=your_key_here
  * SECRET_KEY=random_string_here

  Run the application:
  * python app.py

  Open your browser and navigate to http://localhost:5000

Features

  * Real-time updates via WebSockets
  * Web-based research of companies
  * Multi-agent discussion with different perspectives
  * Executive summary generation
  * Progress tracking UI

Technologies Used

  * Flask: Python web framework
  * Flask-SocketIO: Real-time communication
  * OpenAI API: AI agent responses (GPT-4o)
  * DuckDuckGo Search: Web research capability
  * TailwindCSS: UI styling

Notes
  This is an MVP implementation and has several limitations:

 *  Error handling is basic
  * No authentication or user management
 *  Session data is stored in memory (not persistent)
  * Limited scalability
