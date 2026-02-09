"""Conclusion detection - determines if user response indicates resolution."""

import os
from litellm import completion


DEFAULT_MODEL = os.environ.get("OI_MODEL", "deepseek/deepseek-chat")

# Patterns that indicate disagreement (keep thread open)
DISAGREEMENT_PATTERNS = [
    "no,", "no ", "nope", "not quite", "not really",
    "that's wrong", "that's not", "that doesn't",
    "i don't think", "i disagree",
    "but what about", "what about", "what if",
    "are you sure", "actually,", "actually ",
    "i already tried", "already checked", "already tried",
    "doesn't work", "didn't work", "not working", "still not",
    "that's incorrect", "incorrect",
    "but i ", "but it ", "but the ",
]

# Patterns that indicate acceptance/resolution
ACCEPTANCE_PATTERNS = [
    "thanks", "thank you", "got it", "makes sense", "make sense",
    "you're right", "youre right", "that fixed it", "that worked",
    "perfect", "great", "awesome", "excellent",
]


def is_disagreement_simple(user_message: str) -> bool:
    """Simple pattern-based disagreement detection.

    Returns True if the message looks like disagreement.
    """
    lower = user_message.lower().strip()

    for pattern in DISAGREEMENT_PATTERNS:
        if pattern in lower:
            return True

    return False


def is_disagreement_llm(user_message: str, context: str = "", model: str = DEFAULT_MODEL) -> bool:
    """LLM-based disagreement detection for ambiguous cases.

    Args:
        user_message: The user's response to check
        context: Recent conversation context for better understanding
        model: Model to use for detection

    Returns:
        True if the message indicates disagreement/pushback
    """
    prompt = f"""Analyze this user message and determine if they are DISAGREEING with or PUSHING BACK on a previous answer.

User message: "{user_message}"

Respond with only "DISAGREE" or "ACCEPT".
- DISAGREE: User is questioning, challenging, or rejecting the answer
- ACCEPT: User is accepting, thanking, moving on, or asking something new"""

    messages = [
        {"role": "system", "content": "You classify user responses. Respond with only DISAGREE or ACCEPT."},
        {"role": "user", "content": prompt}
    ]

    response = completion(model=model, messages=messages)
    result = response.choices[0].message.content.strip().upper()

    return "DISAGREE" in result


def is_disagreement(user_message: str, use_llm: bool = False, model: str = DEFAULT_MODEL) -> bool:
    """Detect if user message indicates disagreement.

    Args:
        user_message: The user's response
        use_llm: Whether to use LLM for ambiguous cases
        model: Model to use if LLM detection is enabled

    Returns:
        True if user is disagreeing (thread should stay open)
    """
    # First try simple pattern matching
    if is_disagreement_simple(user_message):
        return True

    # For short accepting messages, don't bother with LLM
    lower = user_message.lower().strip()
    accepting_phrases = ["thanks", "thank you", "got it", "makes sense", "ok", "okay", "perfect", "great"]
    if any(phrase in lower for phrase in accepting_phrases):
        return False

    # Use LLM for ambiguous cases if enabled
    if use_llm:
        return is_disagreement_llm(user_message, model=model)

    # Default: not disagreement (will trigger conclusion)
    return False


class ResolutionDetector:
    """Detects when user messages indicate resolution or disagreement.

    Used to determine when to extract artifacts from conversations.
    """

    def __init__(self, model: str = DEFAULT_MODEL):
        """Initialize detector with optional model override."""
        self.model = model

    def is_resolution(self, message: str, context=None) -> bool:
        """Check if message indicates resolution/acceptance.

        Args:
            message: User message to check
            context: Optional conversation context (dict or str)

        Returns:
            True if message indicates resolution
        """
        if not message or not message.strip():
            return False

        # Check for disagreement first - disagreement blocks resolution
        if self.is_disagreement(message, context):
            return False

        # Check for explicit acceptance patterns
        if self.is_explicit_resolution(message):
            return True

        # Check for implicit resolution (topic change)
        if context and self.is_implicit_resolution(message, context):
            return True

        return False

    def is_disagreement(self, message: str, context=None) -> bool:
        """Check if message indicates disagreement.

        Args:
            message: User message to check
            context: Optional conversation context (ignored in basic implementation)

        Returns:
            True if message indicates disagreement
        """
        return is_disagreement_simple(message)

    def confidence(self, message: str) -> float:
        """Calculate confidence score for resolution/disagreement detection.

        Args:
            message: User message to score

        Returns:
            Float between 0.0 and 1.0 indicating confidence
        """
        if not message or not message.strip():
            return 0.0

        lower = message.lower().strip()

        # Very clear acceptance phrases
        strong_acceptance = [
            "thanks!", "thank you!", "got it!", "perfect!",
            "that makes sense", "you're right", "that fixed it",
            "that worked"
        ]
        for phrase in strong_acceptance:
            if phrase in lower:
                return 0.9

        # Clear disagreement phrases
        strong_disagreement = [
            "no, that's not", "that's wrong", "that doesn't work",
            "i don't think so", "that's incorrect"
        ]
        for phrase in strong_disagreement:
            if phrase in lower:
                return 0.9

        # Moderate acceptance
        moderate_acceptance = ["thanks", "thank you", "got it", "makes sense", "perfect"]
        for phrase in moderate_acceptance:
            if phrase in lower:
                # Check for contradictory signals
                if "but" in lower or "however" in lower:
                    return 0.6
                return 0.85

        # Moderate disagreement
        moderate_disagreement = ["not quite", "are you sure", "but what about"]
        for phrase in moderate_disagreement:
            if phrase in lower:
                return 0.8

        # Ambiguous short responses
        ambiguous = ["ok", "okay", "hmm", "hm", "sure"]
        if lower in ambiguous:
            return 0.5

        # Default: low confidence
        return 0.3

    def is_topic_change(self, message: str, context) -> bool:
        """Check if message represents a topic change.

        Args:
            message: New user message
            context: Previous conversation context (str or dict)

        Returns:
            True if message is about a different topic
        """
        if not context:
            return False

        # Extract context string
        if isinstance(context, dict):
            context_str = context.get("topic", "") or context.get("last_ai_message", "")
        else:
            context_str = str(context)

        if not context_str:
            return False

        lower_msg = message.lower()
        lower_ctx = context_str.lower()

        # Simple keyword-based topic detection
        # If message introduces completely new domain words, likely topic change

        # Auth-related keywords
        auth_keywords = ["auth", "login", "token", "password", "permission", "credential"]
        # Database keywords
        db_keywords = ["database", "query", "index", "indexing", "sql", "table", "db"]
        # Deployment/CI/CD keywords
        deploy_keywords = ["deploy", "aws", "cloud", "server", "production", "ci/cd", "ci", "cd", "pipeline"]
        # API keywords
        api_keywords = ["api", "endpoint", "request", "response"]

        keyword_sets = [auth_keywords, db_keywords, deploy_keywords, api_keywords]

        # Find which topics are in context
        ctx_topics = set()
        for i, keywords in enumerate(keyword_sets):
            if any(kw in lower_ctx for kw in keywords):
                ctx_topics.add(i)

        # Find which topics are in message
        msg_topics = set()
        for i, keywords in enumerate(keyword_sets):
            if any(kw in lower_msg for kw in keywords):
                msg_topics.add(i)

        # If message has topics that aren't in context, it's a topic change
        if msg_topics and not msg_topics.intersection(ctx_topics):
            return True

        return False

    def is_implicit_resolution(self, message: str, context) -> bool:
        """Check if message implies resolution through topic change.

        Args:
            message: User message
            context: Previous conversation context

        Returns:
            True if topic change implies previous topic was resolved
        """
        return self.is_topic_change(message, context)

    def is_explicit_resolution(self, message: str) -> bool:
        """Check if message contains explicit acceptance phrases.

        Args:
            message: User message to check

        Returns:
            True if message explicitly accepts/resolves
        """
        if not message or not message.strip():
            return False

        lower = message.lower().strip()

        # Check for sarcasm patterns first
        sarcasm_patterns = ["for nothing", "oh great", "yeah right"]
        for pattern in sarcasm_patterns:
            if pattern in lower:
                return False

        # Check acceptance patterns
        for pattern in ACCEPTANCE_PATTERNS:
            if pattern in lower:
                return True

        return False


# --- TDD Stubs (auto-generated, implement these) ---

def detect_effort_conclusion(state, user_message):
    """Detect if user message concludes an open effort.
    
    Args:
        state: ConversationState with artifacts
        user_message: User message to check
        
    Returns:
        Effort ID if message concludes an open effort, None otherwise
    """
    open_efforts = state.get_open_efforts()
    if not open_efforts:
        return None
    
    lower_message = user_message.lower()
    
    # Check for "X is done" pattern
    for effort in open_efforts:
        # Simple pattern: "auth bug is done" matches effort with id "auth-bug"
        # We'll check if the effort id appears in the message with "is done" or similar
        effort_id_lower = effort.id.lower()
        effort_name_variations = [
            effort_id_lower,
            effort_id_lower.replace('-', ' '),  # "auth-bug" -> "auth bug"
        ]
        
        for name in effort_name_variations:
            if name in lower_message:
                # Check for conclusion phrases
                conclusion_phrases = [
                    f"{name} is done",
                    f"{name} is finished",
                    f"{name} is resolved",
                    f"{name} is complete",
                    f"{name} is fixed",
                    f"done with {name}",
                    f"finished with {name}",
                    f"resolved {name}",
                    f"fixed {name}",
                ]
                
                for phrase in conclusion_phrases:
                    if phrase in lower_message:
                        return effort.id
    
    return None


# --- TDD Stubs (auto-generated, implement these) ---

def detect_effort_start_phrase(message):
    raise NotImplementedError('detect_effort_start_phrase')


# --- TDD Stubs (auto-generated, implement these) ---

def detect_effort_opening(message):
    raise NotImplementedError('detect_effort_opening')

def extract_effort_opening(message):
    """Extract effort name from a user message that opens a new effort.
    
    Args:
        message: User message like "Let's work on auth-bug - users are getting 401s"
        
    Returns:
        The extracted effort name (e.g., "auth-bug")
    """
    import re
    
    # Patterns for effort opening - capture the effort name (full phrase after the pattern)
    patterns = [
        r"i want to work on\s+(.+)",
        r"let's work on\s+(.+)",
        r"lets work on\s+(.+)",
        r"can we work on\s+(.+)",
        r"work on\s+(.+)",
        r"let's debug\s+(.+)",
        r"lets debug\s+(.+)",
    ]
    
    lower_message = message.lower()
    
    for pattern in patterns:
        match = re.search(pattern, lower_message)
        if match:
            effort_name = match.group(1).strip()
            # Clean up the effort name: remove leading "the ", trailing punctuation
            effort_name = re.sub(r'^the\s+', '', effort_name)
            effort_name = effort_name.rstrip('?.!')
            # Split on common separators like hyphens with spaces, colons, etc.
            for separator in [' - ', ': ', '; ', ', ']:
                if separator in effort_name:
                    effort_name = effort_name.split(separator)[0]
            return effort_name
    
    return None

def extract_effort_name_from_llm_response(response_text):
    import re
    
    # Pattern 1: Extract text in single quotes
    single_quote_pattern = r"'([^']+)'"
    match = re.search(single_quote_pattern, response_text)
    if match:
        return match.group(1)
    
    # Pattern 2: Extract text in double quotes  
    double_quote_pattern = r'"([^"]+)"'
    match = re.search(double_quote_pattern, response_text)
    if match:
        return match.group(1)
    
    # Pattern 3: Extract after "Let's work on the " or similar patterns
    patterns = [
        r"Let's work on the (.+?)(?:\.| together|$)",
        r"Opening effort (.+?) now",
        r"I see you want to work on (.+?)\."
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response_text, re.IGNORECASE)
        if match:
            effort_name = match.group(1).strip()
            # Remove common trailing words
            effort_name = re.sub(r'\s+together$', '', effort_name, flags=re.IGNORECASE)
            effort_name = effort_name.rstrip(' .')
            return effort_name
    
    return None
