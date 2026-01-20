# agentic_ai

Our goal is to create an Agentic AI application 

**Agentic AI Application Design Plan**

**Overview:**
  Building an Agentic AI system that generates structured reports based on user intent using 
multi-agent orchestration.

**Architecture:**

  The system is designed using a layered architecture to ensure clear separation of 
responsibilities. 
**Streamlit:** 
  The Streamlit user interface allows users to enter a report topic, upload 
supporting documents (PDF/DOCX), and download the generated document. 

**FastAPI:** 
  FastAPI acts as the backend layer that receives requests and sends them to the 
AI system.

**CrewAI:** 
  CrewAI is used as the agent orchestration layer, which identifies the user’s 
intent and coordinates the execution of multiple agents. 

  The agent layer consists of a Research Agent, Analysis Agent, Structuring Agent, and 
Writing Agent. These agents work together to collect information, analyze it, organize it, 
and convert it into a final report.

  The Document Generation layer uses tools such as python-docx and ReportLab to 
generate the final PDF or Word document for the user.

  Each agent is connected to specific tools and APIs based on its responsibility. The 
Research Agent uses web search and document retrieval tools, the Analysis Agent uses 
The LLM for reasoning and summarization, the Structuring and Writing Agents use the LLM
to organize and generate content, and the Document Generation layer uses python-docx 
and ReportLab APIs to convert the final text into PDF or Word documents.

**Workflow:**
   *  The user enters a report topic in the Streamlit interface. The request is sent to the FastAPI 
backend through the post/chat API. FastAPI forwards the request to CrewAI, which 
identifies the required task and activates the appropriate agents.
  *  The Research Agent collects information from the internet. The Analysis Agent processes 
and summarizes the collected data. The Structuring Agent organizes the content into 
sections, and the Writing Agent converts it into a readable report.
  * Finally, the Document Generator creates a PDF or Word file and sends it back to the user through the Streamlit 
interface.

**Agents and Their Roles:**

* Research Agent – Collects relevant information from online sources.
* Analysis Agent – Interprets and filters the collected data.
* Structuring Agent – Organizes the content into a logical format.
* Writing Agent – Generates the final readable report.
* Agent Router (CrewAI) – Controls the execution flow between all agents.

**Tools & Technologies:**
  
* Streamlit – User Interface 
* FastAPI – Backend API 
* CrewAI – Agent Orchestration 
* python-docx – Word document generation 
* ReportLab – PDF generation
  
**Use Case:**


  This system allows users to generate professional reports on any topic by simply providing 
a subject, reducing the time and effort required for manual research, analysis, and 
document creation.

**Future Scope:**

  The system can be extended in the future by adding more AI agents such as OCR, data 
analysis, and visualization tools to support more advanced document and intelligence 
capabilities.

**FLOW DIAGRAM:**
<img width="553" height="284" alt="image (1)" src="https://github.com/user-attachments/assets/b428595a-2d7f-4147-a25f-401249f6c516" />
