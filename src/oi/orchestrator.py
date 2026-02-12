"""Stub module: oi.orchestrator (auto-generated for TDD)."""

from .llm import chat
from .chatlog import log_exchange
from .efforts import open_new_effort, add_assistant_confirmation_to_effort
import yaml

def process_turn(session_dir, user_message):
    """Process a single turn: get LLM response and log the exchange."""
    # Get LLM response
    messages = [{"role": "user", "content": user_message}]
    assistant_response = chat(messages)
    
    # Check if this is an effort opening
    if assistant_response.startswith("Opening effort: "):
        # Extract effort ID from the assistant response
        effort_id = assistant_response.split("Opening effort: ")[1].split("\n")[0].strip()
        # Open the effort and log the exchange to the effort log
        open_new_effort(session_dir, effort_id, user_message)
        add_assistant_confirmation_to_effort(session_dir, effort_id, assistant_response)
        # Do not log to ambient
        return assistant_response
    elif assistant_response.startswith("Concluding effort: "):
        # Extract effort ID from the assistant response
        effort_id = assistant_response.split("Concluding effort: ")[1].split("\n")[0].strip()
        # Extract summary from the response
        summary = ""
        if "Summary:" in assistant_response:
            summary_part = assistant_response.split("Summary:")[1].split("\n\n")[0].strip()
            summary = summary_part
        
        # Log the exchange to the effort log
        from .storage import save_to_effort_log
        save_to_effort_log(effort_id, session_dir, "user", user_message)
        save_to_effort_log(effort_id, session_dir, "assistant", assistant_response)
        
        # Update manifest to conclude the effort
        from .storage import conclude_effort
        conclude_effort(effort_id, session_dir, summary)
        
        return assistant_response
    else:
        # Check if there are open efforts
        manifest_path = session_dir / "manifest.yaml"
        if manifest_path.exists():
            manifest = yaml.safe_load(manifest_path.read_text())
            open_efforts = [e for e in manifest.get("efforts", []) if e.get("status") == "open"]
            if open_efforts:
                # Check if the user message is related to the open effort
                effort_id = open_efforts[0]["id"]
                # Convert effort_id to lower case and split by hyphens to get keywords
                effort_keywords = effort_id.lower().replace('-', ' ').split()
                user_message_lower = user_message.lower()
                # Check if any of the effort keywords are in the user message
                if any(keyword in user_message_lower for keyword in effort_keywords):
                    # Route to effort
                    from .storage import save_to_effort_log
                    save_to_effort_log(effort_id, session_dir, "user", user_message)
                    save_to_effort_log(effort_id, session_dir, "assistant", assistant_response)
                    return assistant_response
        
        # Otherwise log as ambient
        log_exchange(session_dir, "ambient", "user", user_message, "assistant", assistant_response)
        return assistant_response

