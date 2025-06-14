from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import T5Tokenizer, T5ForConditionalGeneration
import torch
import logging
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="LLM Service", description="A service for running FLAN-T5-Large model")

# Initialize model and tokenizer
logger.info("Loading model and tokenizer...")
tokenizer = T5Tokenizer.from_pretrained("google/flan-t5-large")
model = T5ForConditionalGeneration.from_pretrained("google/flan-t5-large")
logger.info("Model and tokenizer loaded successfully!")

class GenerationRequest(BaseModel):
    prompt: str
    max_length: int = 100
    temperature: float = 0.7
    top_p: float = 0.9

class GenerationResponse(BaseModel):
    generated_text: str

@app.post("/generate", response_model=GenerationResponse)
async def generate_text(request: GenerationRequest):
    try:
        logger.info(f"Incoming request: {request}")
        # Tokenize input
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
        return GenerationResponse(generated_text=generated_text)

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