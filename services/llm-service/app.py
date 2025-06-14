from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import T5Tokenizer, T5ForConditionalGeneration
import torch
import logging
import uvicorn
import uuid
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="LLM Service", description="A service for running FLAN-T5-Large model")

# In-memory conversation store
conversations: Dict[str, List[str]] = {}

# Initialize model and tokenizer
logger.info("Loading model and tokenizer...")
tokenizer = T5Tokenizer.from_pretrained("google/flan-t5-large")
model_result = T5ForConditionalGeneration.from_pretrained("google/flan-t5-large")
# Handle the case where the model might be returned as a tuple
model = model_result[0] if isinstance(model_result, tuple) else model_result
logger.info("Model and tokenizer loaded successfully!")

class GenerationRequest(BaseModel):
    prompt: str
    max_length: int = 100
    temperature: float = 0.7
    top_p: float = 0.9
    conversation_id: Optional[str] = None

class GenerationResponse(BaseModel):
    generated_text: str
    conversation_id: str

@app.post("/generate", response_model=GenerationResponse)
async def generate_text(request: GenerationRequest):
    try:
        logger.info(f"Incoming request: {request}")

        # Generate or use existing conversation ID
        conv_id = request.conversation_id or str(uuid.uuid4())

        # Initialize conversation if new
        if conv_id not in conversations:
            conversations[conv_id] = []
            logger.info(f"Created new conversation {conv_id}")

        # Add user prompt to conversation history
        conversations[conv_id].append(request.prompt)

        # For context-aware responses, we could use the conversation history
        # Here we're just using the current prompt for simplicity
        input_ids = tokenizer(request.prompt, return_tensors="pt").input_ids

        # Generate text
        outputs = model.generate(
            input_ids,
            max_length=request.max_length,
            temperature=request.temperature,
            top_p=request.top_p,
            do_sample=True
        )

        # Decode and return
        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        logger.info(f"Generated response: {generated_text}")

        # Add response to conversation history
        conversations[conv_id].append(generated_text)

        return GenerationResponse(generated_text=generated_text, conversation_id=conv_id)

    except Exception as e:
        logger.error(f"Error during text generation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/")
async def root():
    return {"message": "Welcome to the LLM Service"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
