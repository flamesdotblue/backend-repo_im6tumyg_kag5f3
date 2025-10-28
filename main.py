import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message")


class ChatResponse(BaseModel):
    reply: str
    allowed: bool
    reasons: List[str] = []


def is_waste_management_question(text: str) -> tuple[bool, List[str]]:
    t = text.lower()

    waste_keywords = [
        # Core domain
        "waste", "garbage", "trash", "refuse", "rubbish", "litter",
        "recycle", "recycling", "compost", "composting", "landfill",
        "incineration", "waste segregation", "segregation", "bin", "bins",
        "collection", "pickup", "solid waste", "hazardous waste", "ewaste",
        "e-waste", "medical waste", "organic waste", "plastic", "paper",
        "glass", "metal", "battery", "electronics disposal", "zero waste",
        "circular economy", "resource recovery", "material recovery",
        "mrf", "msw", "municipal waste", "biodegradable", "non-biodegradable",
        "sanitary waste", "waste audit", "dumpster", "transfer station",
        "compactor", "leachate", "methane", "anaerobic digestion",
        "extended producer responsibility", "epr",
        # Services and rules
        "collection schedule", "pickup schedule", "bulk waste",
        "drop-off", "recycling center", "recycling centre", "clean-up",
        "sorting", "guidelines", "contamination", "blue bin", "green bin",
        "brown bin"
    ]

    banned_keywords = [
        # Finance/business topics to exclude
        "stock", "stocks", "share", "shares", "crypto", "bitcoin",
        "ethereum", "forex", "currency", "currencies", "dividend",
        "portfolio", "valuation", "budget", "loan", "mortgage", "interest",
        "roi", "return on investment", "revenue", "profit", "loss",
        "accounting", "tax", "taxes", "irs", "gst", "balance sheet",
        "income statement", "inflation", "economy", "economic", "finance",
        "financial", "bank", "banking", "trading", "hedge", "fund",
    ]

    reasons: List[str] = []

    banned_hit = any(word in t for word in banned_keywords)
    waste_hit = any(word in t for word in waste_keywords)

    if banned_hit and not waste_hit:
        reasons.append("Question appears to be about finance/business, which is out of scope.")
        return False, reasons

    if waste_hit:
        reasons.append("Detected waste-management related keywords.")
        return True, reasons

    # No direct waste keywords, try simple semantic hints
    context_hints = ["bin day", "pickup day", "how to dispose", "can i throw"]
    if any(h in t for h in context_hints):
        reasons.append("Detected disposal/pickup context.")
        return True, reasons

    reasons.append("Could not match the topic to waste management.")
    return False, reasons


@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        # Try to import database module
        from database import db

        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    allowed, reasons = is_waste_management_question(req.message)

    if not allowed:
        return ChatResponse(
            reply=(
                "I'm here to help with waste management topics only. "
                "Please ask about recycling, disposal guidelines, pickup schedules, composting, etc."
            ),
            allowed=False,
            reasons=reasons,
        )

    # Very lightweight rule-based guidance to keep responses useful
    t = req.message.lower()
    reply = None

    faqs = [
        ("plastic", "Clean and dry plastics with numbers 1-5 are typically recyclable. Film/plastic bags usually are not curbside—use store drop-offs if available."),
        ("battery", "Batteries should not go in regular bins. Use designated e-waste or hazardous waste drop-offs in your city."),
        ("compost", "Compost accepts food scraps, coffee grounds, yard waste, and uncoated paper. Avoid meat, dairy, and oily foods if your local guidelines restrict them."),
        ("glass", "Rinse glass containers and remove caps. Some areas separate by color; check local rules."),
        ("electronics", "Electronics are e-waste. Use certified e-waste collection points for safe recycling."),
        ("pickup", "Curbside pickup days vary by location. Please check your local collection schedule or provide your area for specific guidance."),
        ("hazard", "Hazardous waste (paint, chemicals, solvents) requires special drop-offs—never place in regular bins."),
        ("landfill", "Items that are contaminated, mixed materials, or non-recyclable plastics often go to landfill. Consider reuse first."),
    ]

    for key, ans in faqs:
        if key in t:
            reply = ans
            break

    if reply is None:
        reply = (
            "This appears related to waste management. Could you share your city/area if you need local rules, or specify the material/item you're disposing of?"
        )

    return ChatResponse(reply=reply, allowed=True, reasons=reasons)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
