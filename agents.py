# agents.py

import os
from dotenv import load_dotenv
from openai import OpenAI
import logging

# Import the web search tool
from tools import web_search

# Set up logging
logger = logging.getLogger('btmodel-web')

# Load environment variables from .env
load_dotenv()

# Instantiate the OpenAI client using the API key from .env
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Helper function to remove quotation marks from facilitator messages
def clean_quotation_marks(text):
    """
    Remove surrounding quotation marks from a string.
    Also handles cases where there are multiple quotation segments.
    """
    if not text:
        return text
        
    # Remove quotes at the beginning and end
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    
    # Handle cases with separate quoted segments
    # e.g. "Let's begin our analysis of Company." "What do you think about..."
    text = text.replace('" "', ' ')
    
    # Check again after joining segments
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
        
    return text

# ---------------------------
# Base Agent Class
# ---------------------------
class BaseBTAgent:
    def __init__(self, agent_name, personality, instructions):
        self.agent_name = agent_name  
        self.personality = personality
        # Update instructions to encourage a concise, conversational style
        self.instructions = instructions + (
            " Respond in a friendly, conversational tone as if you're speaking in a roundtable discussion with colleagues. "
            "Keep your response concise (maximum 3-4 short paragraphs) and avoid using bullet points or numbered lists. "
            "Use natural language and avoid formal academic style. Focus on 1-2 key insights rather than being comprehensive. "
            "Your answer should sound like something a human expert would say in a casual professional conversation."
        )

    def get_response(self, input_text):
        try:
            logger.info(f"Getting response from {self.agent_name}")
            response = client.chat.completions.create(
                model="gpt-4o",  # Using gpt-4o for better responses
                messages=[
                    {"role": "system", "content": self.instructions},
                    {"role": "user", "content": input_text}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error getting response from {self.agent_name}: {str(e)}")
            return f"[Error generating response from {self.agent_name}: {str(e)}]"

# ---------------------------
# Specialized Agents
# ---------------------------
class BusinessStrategist(BaseBTAgent):
    def __init__(self):
        agent_name = "Business Strategist"
        personality = "Focused on overall business value, strategic insights, and market positioning."
        instructions = (
            "You are a Business Strategist following the Business Technology Standard. "
            "Share your insights about overall business strategy, market dynamics, and value creation. "
            "Express your opinions in a thoughtful, human-like way."
        )
        super().__init__(agent_name, personality, instructions)

class ProductManager(BaseBTAgent):
    def __init__(self):
        agent_name = "Product Manager"
        personality = "Focused on product development, user experience, and service planning."
        instructions = (
            "You are a Product Manager following the Business Technology Standard. "
            "Discuss product development, service design, and ways to enhance user experience. "
            "Give detailed opinions in a conversational style, as if you're discussing ideas with a colleague."
        )
        super().__init__(agent_name, personality, instructions)

class TechnologyOfficer(BaseBTAgent):
    def __init__(self):
        agent_name = "Technology Officer"
        personality = "Focused on technical feasibility, IT governance, and operational technology."
        instructions = (
            "You are a Technology Officer following the Business Technology Standard. "
            "Talk about technical challenges, IT governance, and operational technology aspects in an approachable and natural manner."
        )
        super().__init__(agent_name, personality, instructions)

class InnovationAnalyst(BaseBTAgent):
    def __init__(self):
        agent_name = "Innovation Analyst"
        personality = "Focused on innovation management, data trends, and emerging technology opportunities."
        instructions = (
            "You are an Innovation Analyst following the Business Technology Standard. "
            "Share your thoughts on innovation processes, data trends, and future technology opportunities with warmth and clarity."
        )
        super().__init__(agent_name, personality, instructions)

# ---------------------------
# Research Agent
# ---------------------------
class ResearchAgent:
    def __init__(self):
        pass

    def run(self, company_name):
        try:
            logger.info(f"Researching {company_name}")
            
            # Use web search tool to get information
            web_results = web_search(company_name)
            
            if not web_results or "Error retrieving search results" in web_results:
                logger.warning(f"Web search for {company_name} returned no/error results")
                # Fallback message if web search fails
                return f"Research data for {company_name} could not be retrieved due to a web search error. This is a technology company providing various services and products to customers worldwide."
            
            # Build a prompt with the search results
            prompt = (
                f"Using the following web search results, provide a concise, well-structured summary about '{company_name}':\n\n"
                f"{web_results}\n\n"
                "Focus on their business model, products/services, market position, technology stack if available, and recent developments."
            )
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a research assistant. Create a clear, comprehensive business summary."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            research_data = response.choices[0].message.content.strip()
            logger.info(f"Research completed for {company_name}")
            return research_data
            
        except Exception as e:
            logger.error(f"Error in ResearchAgent: {str(e)}")
            # Fallback to a generic response in case of error
            return f"Research data for {company_name} could not be retrieved due to an error: {str(e)}. Please try again later."

# ---------------------------
# Summarization Agent
# ---------------------------
class SummarizationAgent:
    def __init__(self):
        self.instructions = (
            "You are a summarization expert. Create a comprehensive executive summary that synthesizes the research data "
            "and expert discussion into key insights and recommendations. Format as a business brief with appropriate headings and structure."
        )

    def summarize(self, research_data, conversation_transcript):
        try:
            logger.info("Generating summary")
            
            input_text = (
                f"Research Data:\n{research_data}\n\n"
                f"Expert Discussion Transcript:\n{conversation_transcript}\n\n"
                "Please provide a comprehensive executive summary with the following sections:\n"
                "1. Overview\n"
                "2. Key Business Insights\n"
                "3. Technology Considerations\n"
                "4. Recommendations\n"
                "5. Conclusion"
            )
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": self.instructions},
                    {"role": "user", "content": input_text}
                ],
                temperature=0.7
            )
            
            logger.info("Summary generation completed")
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error in SummarizationAgent: {str(e)}")
            return f"Summary generation failed: {str(e)}. Please review the research data and expert discussion directly."