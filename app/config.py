from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.models.models import AggregationResult, IssueFindings, IssueLLMOutput, LLMDeduplicationResults, LLMDiagnosticsOutput, QueryJudgement, TicketOutput

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env file.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    #LLM
    model_choice: str = "gpt-4o-mini"

settings = Settings()

#List of allowed commands for the LLM
ALLOWED_COMMANDS = {"ls", "cat", "grep", "tail"}

#List of shell operators. The LLM may not use these.
SHELL_OPERATORS = {"|", ">", ">>", "<", "&&", "||", ";", "`", "$"}

def get_llm() -> ChatOpenAI:
    """
    Factory function to create the base LLM for the ticketing app, which can be extended with structured outputs and retry logic as needed for different nodes.
    """
    return ChatOpenAI(
        model=settings.model_choice,
        temperature=0,
    )

def dedupe_llm():
    """Factory function to create the LLM for deduplication, which includes structured output parsing and retry logic."""
    return(get_llm()
           .with_structured_output(LLMDeduplicationResults)
           .with_retry(stop_after_attempt=3))

def writer_llm():
    """Factory function to create the writer LLM, which includes structured output parsing and retry logic."""
    return(get_llm()
           .with_structured_output(TicketOutput)
           .with_retry(stop_after_attempt=3))

def parse_llm():
    """Factory function to create the parse LLM, which includes structured output parsing and retry logic."""
    return(get_llm()
           .with_structured_output(QueryJudgement)
           .with_retry(stop_after_attempt=3))

def issue_llm():
    """Factory function to create the issue LLM, which includes structured output parsing and retry logic."""
    return(get_llm()
           .with_structured_output(IssueLLMOutput)
           .with_retry(stop_after_attempt=3))

def issue_extractor_llm():
    """Factory function to create the issue LLM, which includes structured output parsing and retry logic."""
    return(get_llm()
           #Function calling method forces model to emit a single discrete tool call rather than free-form JSON content
           #Eliminates possibility of multiple responses being concatenated before Pydantic sees them.
           .with_structured_output(IssueFindings, method="function_calling")
           .with_retry(stop_after_attempt=3))

def evaluate_server_llm():
    """Factory function to create the evaluate server LLM, which includes structured output parsing and retry logic."""
    return(get_llm()
           .with_structured_output(LLMDiagnosticsOutput)
           .with_retry(stop_after_attempt=3))

def aggregate_llm():
    """Factory function to create the aggregate LLM, which includes structured output parsing and retry logic."""
    return(get_llm()
           .with_structured_output(AggregationResult)
           .with_retry(stop_after_attempt=3))