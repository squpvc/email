"""
AI services for Project Phoenix.
"""
import os
import logging
import json
import importlib
from enum import Enum
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union, Literal, Type
from dataclasses import dataclass, field

# Import OpenAI errors
try:
    from openai import RateLimitError, APITimeoutError, APIError
except ImportError:
    # Define dummy classes if openai is not available
    class RateLimitError(Exception):
        pass
    
    class APITimeoutError(Exception):
        pass
    
    class APIError(Exception):
        pass

# Configure logging
logger = logging.getLogger(__name__)

# Lazy imports
class LazyImport:
    def __init__(self, module_name: str, package: str = None):
        self.module_name = module_name
        self.package = package
        self._module = None
        
    def __getattr__(self, name):
        if self._module is None:
            try:
                self._module = importlib.import_module(self.module_name, self.package)
                logger.info(f"Lazy-loaded module: {self.module_name}")
            except ImportError as e:
                logger.warning(f"Failed to import {self.module_name}: {str(e)}")
                raise
        return getattr(self._module, name)

# Try to import AI dependencies lazily
try:
    # Initialize NLP model with lazy loading
    nlp = None
    embedding_model = None
    chroma_client = None
    openai_client = None
    collection = None
    
    # Set AI availability
    AI_AVAILABLE = True
    
    # We'll initialize these only when needed
    spacy_import = LazyImport("spacy")
    sentence_transformers_import = LazyImport("sentence_transformers")
    chromadb_import = LazyImport("chromadb")
    openai_import = LazyImport("openai")
    numpy_import = LazyImport("numpy")
    
    # Create dummy classes and functions when AI is not available
    class DummyModel:
        def __call__(self, *args, **kwargs):
            raise ImportError("AI features are not available. Please install required dependencies.")
    
    nlp = DummyModel()
    embedding_model = DummyModel()
    chroma_client = None
    openai_client = None
    collection = None
    
    # Initialize these when first used
    def _init_nlp():
        try:
            nlp = spacy_import.load("en_core_web_sm")
            logger.info("Loaded spaCy model successfully")
            return nlp
        except Exception as e:
            logger.warning(f"Failed to load spaCy model: {str(e)}")
            return DummyModel()
    
    def _init_embedding_model():
        try:
            model = sentence_transformers_import.SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Loaded sentence transformer model successfully")
            return model
        except Exception as e:
            logger.warning(f"Failed to load sentence transformer: {str(e)}")
            return DummyModel()
    
    def _init_chroma():
        try:
            client = chromadb_import.Client()
            collection = client.create_collection("emails")
            logger.info("Initialized ChromaDB client and collection")
            return client, collection
        except Exception as e:
            logger.warning(f"Failed to initialize ChromaDB: {str(e)}")
            return None, None
    
    def _init_openai():
        try:
            client = openai_import.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            logger.info("Initialized OpenAI client")
            return client
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI client: {str(e)}")
            return None

except ImportError as e:
    logger.warning(f"AI dependencies not available: {str(e)}")
    AI_AVAILABLE = False
    
    # Create dummy classes and functions when AI is not available
    class DummyModel:
        def __call__(self, *args, **kwargs):
            raise ImportError("AI features are not available. Please install required dependencies.")
    
    nlp = DummyModel()
    embedding_model = DummyModel()
    chroma_client = None
    openai_client = None
    collection = None

class EmailCategory(str, Enum):
    """Categories for email classification."""
    PRIMARY = "primary"
    SOCIAL = "social"
    PROMOTIONS = "promotions"
    UPDATES = "updates"
    FORUMS = "forums"
    IMPORTANT = "important"
    STARRED = "starred"
    SCHEDULED = "scheduled"
    SPAM = "spam"
    TRASH = "trash"
    
class EmailPriority(int, Enum):
    """Priority levels for emails."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

@dataclass
class EmailSummary:
    """Represents a summarized email with additional metadata."""
    summary: str
    key_points: List[str]
    sentiment: str
    category: Optional[EmailCategory] = None
    priority: Optional[EmailPriority] = None
    suggested_actions: List[str] = field(default_factory=list)
    
@dataclass
class EmailSearchResult:
    """Represents an email search result with enhanced metadata."""
    id: str
    subject: str
    sender: str
    date: str
    snippet: str
    score: float
    category: Optional[EmailCategory] = None
    priority: Optional[EmailPriority] = None
    has_attachments: bool = False
    is_read: bool = False
    
@dataclass
class EmailClassification:
    """Represents email classification results."""
    category: EmailCategory
    priority: EmailPriority
    tags: List[str]
    confidence: float
    sentiment: str
    
@dataclass
class ActionItem:
    """Represents an action item extracted from an email."""
    id: str
    description: str
    due_date: Optional[datetime] = None
    priority: EmailPriority = EmailPriority.NORMAL
    assignee: Optional[str] = None
    status: str = "pending"
    source_email_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

class AIService:
    """Service class for AI operations with enhanced features and error handling."""
    
    # Cache for expensive operations
    _nlp_cache = {}
    _embedding_cache = {}
    
    def __init__(self):
        """Initialize the AI service with lazy loading of models and clients."""
        self._nlp = None
        self._embedding_model = None
        self._chroma = None
        self._openai = None
        self._collection = None
        self._available = AI_AVAILABLE
        logger.info("AI service initialized (lazy loading enabled)")
    
    @property
    def available(self) -> bool:
        """Check if AI services are available."""
        return self._available
    
    @property
    def nlp(self):
        """Lazy load the NLP model."""
        if self._nlp is None and AI_AVAILABLE:
            self._nlp = _init_nlp()
        return self._nlp
    
    @property
    def embedding_model(self):
        """Lazy load the embedding model."""
        if self._embedding_model is None and AI_AVAILABLE:
            self._embedding_model = _init_embedding_model()
        return self._embedding_model
    
    @property
    def chroma(self):
        """Lazy load the ChromaDB client."""
        if self._chroma is None and AI_AVAILABLE:
            self._chroma, self._collection = _init_chroma()
        return self._chroma
    
    @property
    def collection(self):
        """Lazy load the ChromaDB collection."""
        if self._collection is None and AI_AVAILABLE:
            self._chroma, self._collection = _init_chroma()
        return self._collection
    
    @property
    def openai(self):
        """Lazy load the OpenAI client."""
        if self._openai is None and AI_AVAILABLE:
            self._openai = _init_openai()
        return self._openai
    
    def _get_cached_embedding(self, text: str) -> List[float]:
        """Get cached embedding or compute if not in cache."""
        if not text.strip():
            return [0.0] * 384  # Default dimension for all-MiniLM-L6-v2
            
        if text not in self._embedding_cache:
            self._embedding_cache[text] = self.embedding_model.encode(text).tolist()
        return self._embedding_cache[text]
    
    def _call_openai(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Wrapper for OpenAI API calls with retry logic and error handling."""
        if not self.available:
            raise RuntimeError("AI features are not available")
            
        default_kwargs = {
            "model": "gpt-3.5-turbo",
            "temperature": 0.3,
            "max_tokens": 1000,
            "timeout": 30,
        }
        default_kwargs.update(kwargs)
        
        try:
            response = self.openai.chat.completions.create(
                messages=messages,
                **default_kwargs
            )
            return response.choices[0].message.content
            
        except RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {str(e)}")
            raise RuntimeError("Rate limit exceeded. Please try again later.")
        except APITimeoutError as e:
            logger.error(f"OpenAI API timeout: {str(e)}")
            raise RuntimeError("Request timed out. Please check your connection and try again.")
        except APIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise RuntimeError(f"AI service error: {str(e)}")
    
    def is_available(self) -> bool:
        """Check if AI services are available."""
        return self.available
    
    def _init_collections(self) -> bool:
        """Initialize ChromaDB collections."""
        if not self.available:
            return False
            
        try:
            self.collection = self.chroma.get_or_create_collection(
                name="emails",
                metadata={"hnsw:space": "cosine"},
                embedding_function=self.embedding_model.encode
            )
            logger.info("Initialized ChromaDB collection successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB collection: {str(e)}", exc_info=True)
            self.available = False
            return False
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for the given text."""
        if not AI_AVAILABLE or not text.strip():
            return [0.0] * 384  # Return zero vector if AI is not available
            
        try:
            embedding = self.embedding_model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logging.error(f"Error generating embedding: {e}")
            return [0.0] * 384
    
    def index_email(
        self,
        email_id: str,
        subject: str,
        body: str,
        sender: str,
        date: str,
        recipients: Optional[List[str]] = None,
        labels: Optional[List[str]] = None,
        has_attachments: bool = False,
        is_read: bool = False,
        thread_id: Optional[str] = None
    ) -> bool:
        """
        Index an email for semantic search with enhanced metadata.
        
        Args:
            email_id: Unique identifier for the email
            subject: Email subject
            body: Email body text
            sender: Sender's email address
            date: Email date in ISO format
            recipients: List of recipient email addresses
            labels: List of labels/categories for the email
            has_attachments: Whether the email has attachments
            is_read: Whether the email has been read
            thread_id: ID of the email thread
            
        Returns:
            bool: True if indexing was successful, False otherwise
        """
        if not self.available:
            logger.warning("AI features not available for indexing")
            return False
            
        try:
            # Generate document embedding from subject and body
            doc_text = f"Subject: {subject}\n\n{body}"
            
            # Classify the email
            classification = self.classify_email(subject, body, sender, recipients=recipients)
            
            # Prepare metadata
            metadata = {
                "subject": subject,
                "sender": sender,
                "date": date,
                "snippet": f"{body[:200]}..." if len(body) > 200 else body,
                "has_attachments": has_attachments,
                "is_read": is_read,
                "category": classification.category.value,
                "priority": classification.priority.value,
                "sentiment": classification.sentiment,
                "labels": json.dumps(labels or []),
                "recipients": json.dumps(recipients or []),
                "thread_id": thread_id or "",
                "indexed_at": datetime.utcnow().isoformat()
            }
            
            # Add to ChromaDB
            self.collection.upsert(
                ids=[email_id],
                embeddings=[self._get_cached_embedding(doc_text)],
                metadatas=[metadata],
                documents=[doc_text]
            )
            
            logger.debug(f"Indexed email: {email_id} - {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Error indexing email {email_id}: {str(e)}", exc_info=True)
            return False
    
    def search_emails(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        n_results: int = 10,
        min_score: float = 0.3
    ) -> List[EmailSearchResult]:
        """
        Search emails using semantic search with filtering.
        
        Args:
            query: The search query in natural language
            filters: Optional filters to apply (e.g., {'sender': 'example@email.com'})
            n_results: Maximum number of results to return
            min_score: Minimum similarity score (0-1) for results
            
        Returns:
            List of EmailSearchResult objects matching the query
        """
        if not self.available:
            logger.warning("AI features not available for search")
            return []
            
        try:
            # Get query embedding
            query_embedding = self._get_cached_embedding(query)
            
            # Prepare filters for ChromaDB
            where_clause = {}
            if filters:
                where_clause = {
                    "$and": [
                        {key: {"$eq": value}} 
                        for key, value in filters.items() 
                        if value is not None
                    ]
                } if any(filters.values()) else {}
            
            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_clause or None,
                include=["metadatas", "documents", "distances"]
            )
            
            # Process results
            search_results = []
            for i, doc_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i]
                score = 1.0 - distance  # Convert distance to similarity score
                
                if score < min_score:
                    continue
                    
                search_results.append(
                    EmailSearchResult(
                        id=doc_id,
                        subject=metadata.get("subject", "No subject"),
                        sender=metadata.get("sender", "Unknown"),
                        date=metadata.get("date", ""),
                        snippet=metadata.get("snippet", ""),
                        score=score,
                        category=EmailCategory(metadata.get("category", "primary")),
                        priority=EmailPriority(metadata.get("priority", 2)),
                        has_attachments=metadata.get("has_attachments", False),
                        is_read=metadata.get("is_read", False)
                    )
                )
            
            # Sort by score in descending order
            search_results.sort(key=lambda x: x.score, reverse=True)
            return search_results
            
        except Exception as e:
            logger.error(f"Error in search_emails: {str(e)}", exc_info=True)
            return []
    
    def suggest_reply(
        self,
        email_subject: str,
        email_body: str,
        style: str = "professional",
        tone: str = "neutral",
        length: str = "similar"
    ) -> str:
        """
        Generate a suggested reply to an email with customizable style and tone.
        
        Args:
            email_subject: The subject of the email being replied to
            email_body: The body of the email being replied to
            style: The writing style (e.g., 'professional', 'friendly', 'concise')
            tone: The tone of the reply (e.g., 'neutral', 'appreciative', 'apologetic')
            length: The desired length of the reply ('short', 'similar', 'detailed')
            
        Returns:
            A suggested reply as a string
        """
        if not self.available:
            raise RuntimeError("AI features are not available")
            
        try:
            # Prepare the prompt
            prompt = f"""
            Please draft a {style} email reply with a {tone} tone.
            The reply should be {length} in length to the original email.
            
            Email Subject: {email_subject}
            
            Email Content:
            {email_body}
            """
            
            messages = [
                {
                    "role": "system",
                    "content": """You are a helpful email assistant that drafts professional email replies.
                    Your responses should be well-structured and appropriate for the given style and tone.
                    Include a proper greeting and closing."""
                },
                {"role": "user", "content": prompt}
            ]
            
            # Call the AI with appropriate parameters
            reply = self._call_openai(
                messages,
                temperature=0.7,  # More creative responses
                max_tokens=1000
            )
            
            return reply.strip()
            
        except Exception as e:
            logger.error(f"Error in suggest_reply: {str(e)}", exc_info=True)
            raise RuntimeError("Failed to generate a reply. Please try again later.")
    
    def extract_action_items(
        self,
        email_subject: str,
        email_body: str,
        thread_context: Optional[List[Dict]] = None,
        current_user: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract action items from an email or thread.
        
        Args:
            email_subject: The subject of the email
            email_body: The body of the email
            thread_context: Previous messages in the thread
            current_user: Email of the current user to identify assigned actions
            
        Returns:
            List of action items with details
        """
        if not self.available:
            logger.warning("AI features not available for action item extraction")
            return []
            
        try:
            # Build context from thread if available
            context = ""
            if thread_context:
                context = "\n\nPrevious messages in thread:\n"
                for msg in thread_context[-2:]:  # Last 2 messages for context
                    context += f"From: {msg.get('sender', 'Unknown')}\n"
                    context += f"Subject: {msg.get('subject', 'No subject')}\n"
                    context += f"{msg.get('body', '')[:200]}...\n\n"
            
            # Prepare prompt
            prompt = f"""
            Analyze the following email and extract any action items or tasks.
            For each action item, identify:
            1. The action to be taken
            2. Who it's assigned to (if mentioned)
            3. Any mentioned deadlines
            4. Priority (high, medium, low)
            
            Email Subject: {email_subject}
            
            Email Body:
            {email_body}
            
            {context}
            
            Format your response as a JSON array of objects with these keys:
            - action: string (required)
            - assignee: string (email or name, empty if not specified)
            - due_date: string (ISO format, empty if not specified)
            - priority: string (high, medium, low)
            - status: string (pending, in_progress, completed)
            """
            
            messages = [
                {"role": "system", "content": "You are a helpful assistant that extracts action items from emails."},
                {"role": "user", "content": prompt}
            ]
            
            response = self._call_openai(
                messages,
                response_format={"type": "json_object"},
                temperature=0.1  # More deterministic output
            )
            
            # Parse the response
            try:
                result = json.loads(response)
                actions = result.get("actions", []) if isinstance(result, dict) else []
                
                # Process and validate actions
                valid_actions = []
                for action in actions:
                    if not isinstance(action, dict) or "action" not in action:
                        continue
                        
                    # Set default values
                    action_item = {
                        "action": action.get("action", ""),
                        "assignee": action.get("assignee", ""),
                        "due_date": action.get("due_date", ""),
                        "priority": action.get("priority", "medium").lower(),
                        "status": action.get("status", "pending").lower(),
                        "source": "email",
                        "created_at": datetime.utcnow().isoformat()
                    }
                    
                    # Validate priority
                    if action_item["priority"] not in ["high", "medium", "low"]:
                        action_item["priority"] = "medium"
                        
                    # Validate status
                    if action_item["status"] not in ["pending", "in_progress", "completed"]:
                        action_item["status"] = "pending"
                    
                    valid_actions.append(action_item)
                
                return valid_actions
                
            except (json.JSONDecodeError, AttributeError) as e:
                logger.error(f"Failed to parse action items: {str(e)}")
                return []
                
        except Exception as e:
            logger.error(f"Error in extract_action_items: {str(e)}", exc_info=True)
            return []
    
    def summarize_email(
        self,
        subject: str,
        body: str,
        thread_context: Optional[List[Dict]] = None,
        style: Literal["concise", "detailed", "bullets"] = "concise"
    ) -> EmailSummary:
        """
        Generate a comprehensive summary of an email with key points and analysis.
        
        Args:
            subject: Email subject
            body: Email body text
            thread_context: Optional list of previous messages in the thread
            style: Summary style - 'concise', 'detailed', or 'bullets'
            
        Returns:
            EmailSummary object with the summary and analysis
        """
        if not self.available:
            raise RuntimeError("AI features are not available")
            
        try:
            # Build context from thread if available
            context = ""
            if thread_context:
                context = "\n\nPrevious messages in thread:\n"
                for msg in thread_context[-3:]:  # Last 3 messages for context
                    context += f"From: {msg.get('sender', 'Unknown')}\n"
                    context += f"Subject: {msg.get('subject', 'No subject')}\n"
                    context += f"{msg.get('body', '')[:500]}...\n\n"
            
            # Generate summary with different styles
            prompt = f"""
            Please summarize the following email with a {style} style.
            Include the key points and any action items.
            
            Email Subject: {subject}
            
            Email Body:
            {body}
            
            {context}
            """
            
            messages = [
                {"role": "system", "content": "You are a helpful assistant that summarizes emails."},
                {"role": "user", "content": prompt}
            ]
            
            # Get the JSON response from the AI
            response = self._call_openai(messages, temperature=0.2)
            
            try:
                # Parse the JSON response
                response_data = json.loads(response)
                summary = response_data.get("summary", "")
                key_sentences = response_data.get("key_points", [])
                
                # If no key points in response, extract them from the body
                if not key_sentences:
                    doc = self.nlp(body)
                    # Get named entities and important sentences
                    entities = [ent.text for ent in doc.ents if ent.label_ in ["PERSON", "ORG", "GPE", "PRODUCT"]]
                    
                    # Get sentences with important keywords
                    important_keywords = ["important", "urgent", "action", "required", "deadline", "meeting"]
                    for sent in doc.sents:
                        if any(keyword in sent.text.lower() for keyword in important_keywords):
                            key_sentences.append(sent.text)
                        if len(key_sentences) >= 3:  # Limit to top 3 key points
                            break
                    
                    # If no key sentences found, use first few sentences
                    if not key_sentences:
                        key_sentences = [sent.text for sent in list(doc.sents)[:3]]
            except json.JSONDecodeError:
                # If parsing fails, use the raw response as summary
                summary = response
                key_sentences = []
            
            # Simple sentiment analysis
            sentiment = "neutral"
            positive_words = ["great", "thanks", "good", "excellent", "appreciate"]
            negative_words = ["urgent", "problem", "issue", "concern", "disappointed"]
            
            if any(word in body.lower() for word in positive_words):
                sentiment = "positive"
            elif any(word in body.lower() for word in negative_words):
                sentiment = "negative"
            
            # Classify the email
            classification = self.classify_email(subject, body, None, thread_context)
            
            return EmailSummary(
                summary=summary,
                key_points=key_sentences,
                sentiment=sentiment,
                category=classification.category,
                priority=classification.priority,
                suggested_actions=[f"Consider replying within 24h" if sentiment == "positive" else "Review carefully"]
            )
            
        except Exception as e:
            logger.error(f"Error in summarize_email: {str(e)}", exc_info=True)
            # Fallback to simple summary
            return EmailSummary(
                summary=f"Subject: {subject}\n\n{body[:300]}..." if len(body) > 300 else body,
                key_points=[],
                sentiment="neutral",
                category=EmailCategory.PRIMARY,
                priority=EmailPriority.NORMAL
            )
    
    def classify_email(
        self,
        subject: str,
        body: str,
        sender: Optional[str] = None,
        thread_context: Optional[List[Dict]] = None,
        recipients: Optional[List[str]] = None
    ) -> EmailClassification:
        """
        Classify an email into categories and determine priority.
        
        Args:
            subject: Email subject
            body: Email body
            sender: Sender's email address
            thread_context: Previous messages in the thread
            recipients: List of recipient email addresses
            
        Returns:
            EmailClassification object with category, priority, etc.
        """
        if not self.available:
            return EmailClassification(
                category=EmailCategory.PRIMARY,
                priority=EmailPriority.NORMAL,
                tags=[],
                confidence=0.0,
                sentiment="neutral"
            )
            
        try:
            # Build context from thread if available
            context = ""
            if thread_context:
                context = "\n\nThread context:\n"
                for msg in thread_context[-2:]:  # Last 2 messages for context
                    context += f"From: {msg.get('sender', 'Unknown')}\n"
                    context += f"Subject: {msg.get('subject', 'No subject')}\n"
                    context += f"{msg.get('body', '')[:200]}...\n\n"
            
            # Prepare prompt for classification
            prompt = f"""
            Analyze the following email and classify it based on the content, sender, and recipients.
            
            Sender: {sender or 'Unknown'}
            Recipients: {', '.join(recipients or ['Unknown'])}
            Subject: {subject}
            
            Email Body:
            {body}
            
            {context}
            
            Please provide:
            1. Category (primary, social, promotions, updates, forums, important, spam)
            2. Priority (1-4, where 1 is lowest and 4 is highest)
            3. Tags (comma-separated)
            4. Sentiment (positive, negative, neutral)
            5. Confidence (0.0-1.0)
            
            Respond in JSON format with these keys: category, priority, tags, sentiment, confidence
            """
            
            messages = [
                {"role": "system", "content": "You are an email classification assistant."},
                {"role": "user", "content": prompt}
            ]
            
            response = self._call_openai(
                messages,
                response_format={"type": "json_object"},
                temperature=0.1  # More deterministic output
            )
            
            # Parse response
            try:
                result = json.loads(response)
                return EmailClassification(
                    category=EmailCategory(result.get("category", "primary").lower()),
                    priority=EmailPriority(int(result.get("priority", 2))),
                    tags=[tag.strip() for tag in result.get("tags", "").split(",") if tag.strip()],
                    confidence=float(result.get("confidence", 0.8)),
                    sentiment=result.get("sentiment", "neutral").lower()
                )
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                logger.warning(f"Failed to parse classification result: {str(e)}")
                # Fallback to basic classification
                return self._basic_classification(subject, body, sender)
                
        except Exception as e:
            logger.error(f"Error in classify_email: {str(e)}", exc_info=True)
            # Fallback to basic classification
            return self._basic_classification(subject, body, sender)
    
    def _basic_classification(
        self,
        subject: str,
        body: str,
        sender: Optional[str] = None
    ) -> EmailClassification:
        """
        Basic rule-based classification when AI is not available or fails.
        
        Args:
            subject: Email subject
            body: Email body
            sender: Sender's email address
            
        Returns:
            Basic EmailClassification
        """
        # Simple rule-based classification
        text = f"{subject} {body}".lower()
        
        # Check for common spam indicators
        spam_indicators = [
            "win", "free", "congratulations", "limited time", "act now",
            "click here", "unsubscribe", "earn money", "make money", "$$$"
        ]
        
        if any(indicator in text for indicator in spam_indicators):
            return EmailClassification(
                category=EmailCategory.SPAM,
                priority=EmailPriority.LOW,
                tags=["spam"],
                confidence=0.8,
                sentiment="neutral"
            )
        
        # Check for social indicators
        social_domains = ["facebook", "twitter", "linkedin", "instagram", "social"]
        if sender and any(domain in sender.lower() for domain in social_domains):
            return EmailClassification(
                category=EmailCategory.SOCIAL,
                priority=EmailPriority.LOW,
                tags=["social"],
                confidence=0.7,
                sentiment="neutral"
            )
        
        # Default to primary
        return EmailClassification(
            category=EmailCategory.PRIMARY,
            priority=EmailPriority.NORMAL,
            tags=[],
            confidence=0.6,
            sentiment="neutral"
        )
    
    def suggest_reply(self, email_subject: str, email_body: str) -> str:
        """Generate a suggested reply to an email."""
        if not AI_AVAILABLE:
            return "AI features are not available. Please install required dependencies."
            
        try:
            messages: List[ChatCompletionMessageParam] = [
                {"role": "system", "content": "You are a helpful email assistant that drafts professional email replies."},
                {"role": "user", "content": f"Email subject: {email_subject}\n\nEmail content:\n{email_body}\n\nPlease draft a professional and concise reply."}
            ]
            
            response = self.openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content or "I'm sorry, I couldn't generate a reply at this time."
            
        except Exception as e:
            logging.error(f"Error generating reply suggestion: {e}")
            return f"Error generating reply: {str(e)}"

# Global instance - will be initialized on first use
ai_service = None

def get_ai_service():
    """Get the AI service instance, initializing it if necessary."""
    global ai_service
    if ai_service is None:
        try:
            ai_service = AIService()
            if not ai_service.available:
                logger.warning("AI service initialized but not available")
        except Exception as e:
            logger.error(f"Failed to initialize AI service: {str(e)}", exc_info=True)
            ai_service = None
    return ai_service
