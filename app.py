from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import os
import uuid
import logging
import time
import threading
from dotenv import load_dotenv
from openai import OpenAI

# Import agent-related modules
from agents import BusinessStrategist, ProductManager, TechnologyOfficer, InnovationAnalyst, SummarizationAgent, ResearchAgent, clean_quotation_marks

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('btmodel-web')

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "dev-secret-key")

# Enhanced SocketIO configuration
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    ping_timeout=60,
    ping_interval=25,
    async_mode='threading'
)

# Dictionary to store ongoing analysis sessions
active_sessions = {}

# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_analysis', methods=['POST'])
def start_analysis():
    try:
        company_name = request.form.get('company_name')
        if not company_name:
            return jsonify({"error": "Company name is required"}), 400
        
        logger.info(f"Starting analysis for company: {company_name}")
        
        # Generate a unique session ID
        session_id = str(uuid.uuid4())
        
        # Initialize session data
        active_sessions[session_id] = {
            "company_name": company_name,
            "status": "initialized",
            "research_data": "",
            "transcript": [],
            "summary": "",
            "started_at": time.time()
        }
        
        # Start the analysis in a background thread
        analysis_thread = threading.Thread(target=run_analysis, args=(session_id, company_name))
        analysis_thread.daemon = True
        analysis_thread.start()
        
        return jsonify({"session_id": session_id})
    
    except Exception as e:
        logger.error(f"Error starting analysis: {str(e)}")
        return jsonify({"error": "Failed to start analysis. Please try again."}), 500

@app.route('/results/<session_id>')
def results(session_id):
    # Check if session exists
    if session_id not in active_sessions:
        logger.warning(f"Requested nonexistent session: {session_id}")
        return render_template('index.html', error="Analysis session not found or expired.")
    
    return render_template('results.html', session_id=session_id)

@app.route('/check_session/<session_id>')
def check_session(session_id):
    """
    API endpoint to check the status of an analysis session.
    This provides a fallback for clients when WebSocket updates fail.
    """
    try:
        if session_id in active_sessions:
            # Return a simplified version of the session data
            session_data = {
                "status": active_sessions[session_id]["status"],
                "company_name": active_sessions[session_id]["company_name"]
            }
            
            # If analysis is complete, include the summary
            if active_sessions[session_id]["status"] == "complete":
                session_data["summary"] = active_sessions[session_id]["summary"]
            
            return jsonify(session_data)
        else:
            logger.warning(f"Requested status for nonexistent session: {session_id}")
            return jsonify({"error": "Session not found", "status": "error"}), 404
    except Exception as e:
        logger.error(f"Error checking session status: {str(e)}")
        return jsonify({"error": "Failed to check session status", "status": "error"}), 500

@app.route('/debug/sessions')
def debug_sessions():
    """DEBUG ONLY: View active sessions - REMOVE IN PRODUCTION"""
    # Only allow this in debug mode
    if not app.debug:
        return jsonify({"error": "Debug endpoints only available in debug mode"}), 403
        
    # Return a sanitized view of active sessions
    safe_sessions = {}
    for session_id, data in active_sessions.items():
        # Create a copy without potentially sensitive info
        safe_sessions[session_id] = {
            "company_name": data.get("company_name", ""),
            "status": data.get("status", ""),
            "started_at": data.get("started_at", ""),
            "has_research": bool(data.get("research_data")),
            "has_transcript": bool(data.get("transcript")),
            "has_summary": bool(data.get("summary")),
        }
    
    return jsonify({
        "active_sessions_count": len(active_sessions),
        "sessions": safe_sessions
    })

# ----------------------------------------------------------------------
# WebSocket Events
# ----------------------------------------------------------------------

@socketio.on('get_session_data')
def get_session_data(data):
    try:
        session_id = data.get('session_id')
        if session_id in active_sessions:
            logger.info(f"Sending session data for {session_id}")
            emit('session_data', active_sessions[session_id])
        else:
            logger.warning(f"Requested data for nonexistent session: {session_id}")
            emit('error', {'error': 'Session not found or expired'})
    except Exception as e:
        logger.error(f"Error sending session data: {str(e)}")
        emit('error', {'error': 'Failed to retrieve session data'})

@socketio.on('connect')
def handle_connect():
    logger.info(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")

# ----------------------------------------------------------------------
# Analysis Process
# ----------------------------------------------------------------------

def run_analysis(session_id, company_name):
    """Run the multi-agent analysis process"""
    try:
        logger.info(f"Starting analysis for {company_name} (session: {session_id})")
        
        # Initialize conversation state tracking
        state = {
            "current_speaker": None,
            "current_speaking_to": None,
            "current_question": None,
            "last_response": None,
            "next_speaker": None
        }
        
        # Update the session status 
        active_sessions[session_id]["status"] = "research"
        
        # Step 1: Research
        socketio.emit('status_update', {
            'session_id': session_id,
            'status': 'research',
            'message': f"Researching {company_name}..."
        })
        
        try:
            # Use the ResearchAgent to get data from web search
            research_agent = ResearchAgent()
            research_data = research_agent.run(company_name)
            
            # Update session and notify client
            active_sessions[session_id]["research_data"] = research_data
            active_sessions[session_id]["status"] = "discussion"
            
            socketio.emit('research_complete', {
                'session_id': session_id,
                'research_data': research_data,
                'company_name': company_name
            })
        except Exception as e:
            error_message = f"Research phase failed: {str(e)}"
            logger.error(error_message)
            raise Exception(error_message)
        
        # Step 2: Agent Discussion
        socketio.emit('status_update', {
            'session_id': session_id,
            'status': 'discussion',
            'message': "Starting expert discussion..."
        })
        
        try:
            # Initialize all the agents
            agents = {
                "Business Strategist": BusinessStrategist(),
                "Product Manager": ProductManager(),
                "Technology Officer": TechnologyOfficer(),
                "Innovation Analyst": InnovationAnalyst()
            }
            
            # Initialize transcript
            transcript = []
            
            # Initialize OpenAI client up front so it's available for the entire function
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            
            # First analyze the research to determine which agent should start
            facilitator_analysis_prompt = f"""
            You are a discussion facilitator for a business technology analysis roundtable.
            
            Research about {company_name}:
            
            {research_data}
            
            Based on this research data about {company_name}, analyze the key themes and determine:
            1. Which expert should begin our discussion (choose from: Business Strategist, Product Manager, Technology Officer, or Innovation Analyst)
            2. A natural, conversational opening question that references a key insight from the research
            3. Explain in 1-2 sentences why you've chosen this expert to begin
            
            Your opening question should be framed in a conversational way that references something specific from the research, such as:
            The research shows that {company_name} is aiming to be a market leader in the Nordics. What do you think about this positioning in light of the data?
            
            Make the question sound natural, as if you're having a real conversation rather than an interview.
            DO NOT include quotation marks around your question.
            
            Reply in this format exactly:
            CHOSEN_EXPERT: [expert name]
            QUESTION: [your conversational opening question that references the research - no quotation marks]
            REASONING: [1-2 sentence explanation of your choice]
            """
            
            # Use OpenAI to determine starting agent
            try:
                facilitator_response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": facilitator_analysis_prompt}
                    ],
                    temperature=0.7
                )
                facilitator_choice = facilitator_response.choices[0].message.content.strip()
                
                # Extract chosen expert and question
                chosen_expert = None
                opening_question = None
                reasoning = None
                
                for line in facilitator_choice.split('\n'):
                    if line.startswith('CHOSEN_EXPERT:'):
                        chosen_expert = line.replace('CHOSEN_EXPERT:', '').strip()
                    elif line.startswith('QUESTION:'):
                        opening_question = line.replace('QUESTION:', '').strip()
                        # Clean any quotation marks that might have been included
                        opening_question = clean_quotation_marks(opening_question)
                    elif line.startswith('REASONING:'):
                        reasoning = line.replace('REASONING:', '').strip()
                
                # Fallback if parsing failed
                if not chosen_expert or chosen_expert not in agents:
                    chosen_expert = "Business Strategist"
                    opening_question = f"The research shows that {company_name} is positioning itself as a leader in business technology transformation in the Nordics. What do you think about this positioning based on the data we have?"
                    reasoning = "Business strategy provides a foundational perspective to start our discussion."
                
            except Exception as e:
                logger.error(f"Error in facilitator choice: {str(e)}")
                chosen_expert = "Business Strategist"
                opening_question = f"The research shows that {company_name} is positioning itself in the market. What are your thoughts on their business strategy based on what we've learned?"
                reasoning = "Starting with business strategy as a foundation for our discussion."
            
            # Round 1 header
            round_header = "\n=== Expert Discussion - Round 1 ==="
            logger.info(round_header)
            transcript.append(round_header)
            
            socketio.emit('round_update', {
                'session_id': session_id,
                'round': 1,
                'message': round_header
            })
            
            # Function to generate a natural follow-up question
            def generate_follow_up_question(current_agent, current_response, next_agent):
                prompt = f"""
                You are a skilled facilitator running a business technology roundtable discussion about {company_name}.
                
                The {current_agent} just said:
                
                "{current_response}"
                
                Now you need to ask the {next_agent} a follow-up question that:
                1. Naturally builds on a specific insight from {current_agent}'s response
                2. Is tailored to the {next_agent}'s specific expertise and perspective
                3. Maintains conversation flow like in a real roundtable discussion
                
                Structure your question like a natural conversation, for example:
                - That's an interesting point about [specific insight]. From your perspective as {next_agent}, how would this affect...?
                - {current_agent} mentioned [specific insight]. How does this align with what you've seen in terms of...?
                - Building on what we just heard about [specific insight], what's your take on how this impacts...?
                
                IMPORTANT: DO NOT use quotation marks in your response.
                Write ONLY the question you would ask the {next_agent} - nothing else, no preamble, no quotation marks.
                The ideal length is 1-2 sentences, maximum 30 words.
                """
                
                try:
                    follow_up_response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": "You are a skilled discussion facilitator."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7,
                        max_tokens=100  # Keep it concise
                    )
                    follow_up = follow_up_response.choices[0].message.content.strip()
                    
                    # Clean any quotation marks that might have been included
                    follow_up = clean_quotation_marks(follow_up)
                    
                    # Ensure it ends with a question mark
                    if not follow_up.endswith('?'):
                        follow_up += '?'
                        
                    return follow_up
                except Exception as e:
                    logger.error(f"Error generating follow-up question: {str(e)}")
                    # Fallback to a generic follow-up
                    return f"Based on what we just heard, what's your perspective as a {next_agent}?"
            
            # First round discussion order - start with chosen expert, then go through remaining ones
            remaining_agents = list(agents.keys())
            remaining_agents.remove(chosen_expert)
            round_one_order = [chosen_expert] + remaining_agents
            
            # Store agent responses for reference
            agent_responses = {}
            
            # First round of discussion
            for i, agent_name in enumerate(round_one_order):
                agent = agents[agent_name]
                
                # First agent gets the opening question
                if i == 0:
                    # Opening statement from facilitator with reasoning
                    opening_statement = f"Let's begin our analysis of {company_name}. {opening_question}"
                    facilitator_text = f"Facilitator (to {agent_name}): {opening_statement}"
                    question = opening_question
                else:
                    # For subsequent agents, generate a natural follow-up based on previous response
                    prev_agent = round_one_order[i-1]
                    prev_response = agent_responses.get(prev_agent, "")
                    
                    # Generate follow-up question
                    question = generate_follow_up_question(prev_agent, prev_response, agent_name)
                    facilitator_text = f"Facilitator (to {agent_name}): {question}"
                
                logger.info(facilitator_text)
                transcript.append(facilitator_text)
                
                # Update state tracking
                state["current_speaker"] = "Facilitator"
                state["current_speaking_to"] = agent_name
                state["current_question"] = question
                state["next_speaker"] = agent_name
                
                # Emit facilitator message
                socketio.emit('message', {
                    'session_id': session_id,
                    'speaker': 'Facilitator',
                    'to': agent_name,
                    'message': question,
                    'conversation_state': state
                })
                time.sleep(1)  # Short delay for UI
                
                # Get agent response
                agent_input = f"""
                Research about {company_name}:
                
                {research_data}
                
                Previous discussion (if any):
                {transcript_text if 'transcript_text' in locals() else 'This is the start of our discussion.'}
                
                Question: {question}
                """
                response = agent.get_response(agent_input)
                
                # Store response
                agent_responses[agent_name] = response
                
                # Add to transcript
                agent_text = f"{agent_name}: {response}"
                logger.info(f"Generated response for {agent_name}")
                transcript.append(agent_text)
                transcript.append("")  # Empty line for spacing
                
                # Update state tracking
                state["current_speaker"] = agent_name
                state["current_speaking_to"] = None
                state["last_response"] = response[:100] + "..." if len(response) > 100 else response
                
                # Calculate who's next in the order
                if i < len(round_one_order) - 1:
                    state["next_speaker"] = round_one_order[i+1]
                else:
                    state["next_speaker"] = None
                
                # Emit agent message
                socketio.emit('message', {
                    'session_id': session_id,
                    'speaker': agent_name,
                    'message': response,
                    'conversation_state': state
                })
                time.sleep(2)  # Delay to allow reading
                
                # Store response for generating future questions
                agent_responses[agent_name] = response
            
            # Join transcript to provide context for round 2
            transcript_text = "\n".join(transcript)
            
            # Round 2 header
            round_header = "\n=== Expert Discussion - Round 2 ==="
            logger.info(round_header)
            transcript.append(round_header)
            
            socketio.emit('round_update', {
                'session_id': session_id,
                'round': 2,
                'message': round_header
            })
            
            # Generate focused round 2 order and questions using OpenAI
            round_two_prompt = f"""
            Based on the first round of discussion about {company_name}:
            
            {transcript_text}
            
            As a facilitator, determine:
            1. Which expert should lead the second round (may be different from round 1)
            2. A specific follow-up theme or question that builds on the first round
            3. A suggested order for the remaining experts that creates a natural flow
            
            DO NOT use quotation marks in your responses.
            
            Reply in this format exactly:
            LEAD_EXPERT: [expert name]
            THEME: [concise theme or question for round 2 - no quotation marks]
            ORDER: [comma-separated list of the remaining experts in suggested order]
            """
            
            try:
                facilitator_response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": round_two_prompt}
                    ],
                    temperature=0.7
                )
                round_two_plan = facilitator_response.choices[0].message.content.strip()
                
                # Parse the response
                lead_expert = None
                theme = None
                expert_order = []
                
                for line in round_two_plan.split('\n'):
                    if line.startswith('LEAD_EXPERT:'):
                        lead_expert = line.replace('LEAD_EXPERT:', '').strip()
                    elif line.startswith('THEME:'):
                        theme = line.replace('THEME:', '').strip()
                        # Clean any quotation marks
                        theme = clean_quotation_marks(theme)
                    elif line.startswith('ORDER:'):
                        order_str = line.replace('ORDER:', '').strip()
                        expert_order = [name.strip() for name in order_str.split(',') if name.strip() in agents]
                
                # Fallback if parsing failed
                if not lead_expert or lead_expert not in agents or not theme:
                    lead_expert = list(agents.keys())[0]
                    theme = f"Let's focus on implementation challenges and opportunities for {company_name}."
                    expert_order = [name for name in agents.keys() if name != lead_expert]
                
                # Ensure the order has all remaining experts
                for name in agents.keys():
                    if name != lead_expert and name not in expert_order:
                        expert_order.append(name)
                
            except Exception as e:
                logger.error(f"Error in round two planning: {str(e)}")
                # Fallback order
                lead_expert = "Technology Officer"
                theme = f"Let's explore implementation challenges and opportunities for {company_name}."
                expert_order = [name for name in agents.keys() if name != lead_expert]
            
            # Second round discussion with dynamic questions
            round_two_order = [lead_expert] + expert_order
            
            for i, agent_name in enumerate(round_two_order):
                agent = agents[agent_name]
                
                # Formulate a conversational question
                if i == 0:
                    # Make sure theme has no quotation marks
                    theme = clean_quotation_marks(theme)
                    facilitator_text = f"Facilitator (to {agent_name}): Moving to our second round of discussion. {theme} What's your perspective on this?"
                    question = f"{theme} What's your perspective on this?"
                else:
                    # Generate follow-up based on previous response
                    prev_agent = round_two_order[i-1]
                    prev_response = agent_responses.get(prev_agent, "")
                    
                    # Generate follow-up question
                    question = generate_follow_up_question(prev_agent, prev_response, agent_name)
                    facilitator_text = f"Facilitator (to {agent_name}): {question}"
                
                logger.info(facilitator_text)
                transcript.append(facilitator_text)
                
                # Update state tracking
                state["current_speaker"] = "Facilitator"
                state["current_speaking_to"] = agent_name
                state["current_question"] = question
                state["next_speaker"] = agent_name
                
                # Emit facilitator message
                socketio.emit('message', {
                    'session_id': session_id,
                    'speaker': 'Facilitator',
                    'to': agent_name,
                    'message': question,
                    'conversation_state': state
                })
                time.sleep(1)  # Short delay for UI
                
                # Get agent response with full context
                agent_input = f"""
                Research about {company_name}:
                
                {research_data}
                
                Previous discussion:
                
                {transcript_text}
                
                Question: {question}
                
                Your previous response in round 1:
                {agent_responses.get(agent_name, "You haven't spoken yet in this discussion.")}
                
                Please build on the discussion rather than repeating points. Respond directly to the question.
                """
                response = agent.get_response(agent_input)
                
                # Add to transcript
                agent_text = f"{agent_name}: {response}"
                logger.info(f"Generated response for {agent_name}")
                transcript.append(agent_text)
                transcript.append("")  # Empty line for spacing
                
                # Update state tracking
                state["current_speaker"] = agent_name
                state["current_speaking_to"] = None
                state["last_response"] = response[:100] + "..." if len(response) > 100 else response
                
                # Calculate who's next in the order
                if i < len(round_two_order) - 1:
                    state["next_speaker"] = round_two_order[i+1]
                else:
                    state["next_speaker"] = None
                
                # Emit agent message
                socketio.emit('message', {
                    'session_id': session_id,
                    'speaker': agent_name,
                    'message': response,
                    'conversation_state': state
                })
                time.sleep(2)  # Delay to allow reading
                
                # Store response for generating future questions
                agent_responses[agent_name] = response
            
            # Update session with transcript
            active_sessions[session_id]["transcript"] = transcript
            active_sessions[session_id]["status"] = "summarizing"
            
        except Exception as e:
            error_message = f"Discussion phase failed: {str(e)}"
            logger.error(error_message)
            raise Exception(error_message)
        
        # Step 3: Generate Summary
        socketio.emit('status_update', {
            'session_id': session_id,
            'status': 'summarizing',
            'message': "Creating executive summary..."
        })
        
        try:
            # Join transcript for summarization
            transcript_text = "\n".join(transcript)
            
            # Generate summary
            summarizer = SummarizationAgent()
            summary = summarizer.summarize(research_data, transcript_text)
            
            # Update session data
            active_sessions[session_id]["summary"] = summary
            active_sessions[session_id]["status"] = "complete"
            
            # Emit completion events
            logger.info(f"Analysis complete, emitting completion events for session {session_id}")
            
            # First notification
            socketio.emit('status_update', {
                'session_id': session_id,
                'status': 'complete',
                'message': "Analysis complete. Preparing results..."
            })
            
            # Main completion event
            socketio.emit('analysis_complete', {
                'session_id': session_id,
                'summary': summary
            })
            
            # Sleep briefly
            time.sleep(1)
            
            # Backup notification in case the first wasn't received
            socketio.emit('analysis_complete', {
                'session_id': session_id,
                'summary': summary
            })
            
            logger.info(f"Analysis successfully completed for session {session_id}")
            
        except Exception as e:
            error_message = f"Summary generation failed: {str(e)}"
            logger.error(error_message)
            raise Exception(error_message)
            
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error during analysis: {error_message}")
        
        # Update session with error
        if session_id in active_sessions:
            active_sessions[session_id]["status"] = "error"
            active_sessions[session_id]["error"] = error_message
        
        # Emit error to client - try multiple approaches for reliability
        try:
            # Direct emit
            socketio.emit('error', {
                'session_id': session_id,
                'error': error_message
            })
            
            # Also emit a status update
            socketio.emit('status_update', {
                'session_id': session_id,
                'status': 'error',
                'message': f"Error: {error_message}"
            })
            
            # Even if there's an error, we might still want to redirect to results
            socketio.emit('analysis_complete', {
                'session_id': session_id,
                'error': error_message,
                'status': 'error'
            })
        except Exception as emit_error:
            logger.critical(f"Failed to emit error event: {str(emit_error)}")

if __name__ == '__main__':
    try:
        # Use parameters compatible with your Flask-SocketIO version
        logger.info("Starting BTModel Web - MVP with AI Agents")
        socketio.run(app, debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        logger.critical(f"Failed to start application: {str(e)}")