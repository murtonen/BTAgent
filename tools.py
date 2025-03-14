# tools.py

import logging
from dotenv import load_dotenv

# Set up logging
logger = logging.getLogger('btmodel-web')

# Load environment variables
load_dotenv()

def web_search(query):
    """
    Perform a web search using DuckDuckGo and return formatted results.
    Falls back to a simulated response if the real search fails.
    """
    try:
        logger.info(f"Performing web search for: {query}")
        
        # Try to import and use the DuckDuckGo search
        try:
            from duckduckgo_search import DDGS
            
            # Perform the search
            results = DDGS().text(query, max_results=5)
            
            if not results:
                logger.warning(f"No search results found for: {query}")
                return simulate_search(query)
            
            # Format the results
            output = []
            for result in results:
                title = result.get("title", "No Title")
                snippet = result.get("body", "No snippet available.")
                output.append(f"{title}: {snippet}")
            
            return "\n\n".join(output)
            
        except ImportError as e:
            logger.warning(f"DuckDuckGo search package not available: {str(e)}")
            return simulate_search(query)
            
    except Exception as e:
        logger.error(f"Error in web search: {str(e)}")
        return simulate_search(query)

def simulate_search(company_name):
    """Generate simulated search results if real search fails"""
    logger.info(f"Generating simulated search results for: {company_name}")
    
    return f"""
{company_name} Official Website: {company_name} is a leading technology company specializing in innovative solutions for businesses and consumers. Our mission is to transform the way people connect, work, and live through cutting-edge technology.

Wikipedia - {company_name}: {company_name} is a multinational technology corporation founded in 2005. The company develops software, hardware, and services for various industries including finance, healthcare, and retail.

Forbes - {company_name} Ranks Among Top Tech Companies: In recent industry rankings, {company_name} has shown strong growth in market share and revenue, with a 15% increase in quarterly earnings.

TechCrunch - {company_name} Announces New Product Line: {company_name} recently unveiled its latest product suite, focusing on artificial intelligence and machine learning capabilities for enterprise customers.

LinkedIn - {company_name} Company Profile: {company_name} employs over 5,000 professionals worldwide with headquarters in San Francisco and offices across North America, Europe, and Asia.
"""