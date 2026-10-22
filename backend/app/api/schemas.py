"""HTTP contract (request/response) and the agent's structured Verdict.

Mirrored in frontend/src/lib/types.ts — change both together.
"""

from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class ScamType(str, Enum):
    fake_parcel = "fake_parcel"
    fake_bank_or_loan = "fake_bank_or_loan"
    investment = "investment"
    romance = "romance"
    job_task = "job_task"
    phishing_link = "phishing_link"
    gov_impersonation = "gov_impersonation"
    prize_lottery = "prize_lottery"
    gambling = "gambling"
    legit = "legit"
    other = "other"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    unknown = "unknown"  # not enough information to judge


class Channel(str, Enum):
    sms = "sms"
    line = "line"
    email = "email"
    other = "other"


class RedFlag(BaseModel):
    text: str
    # Exact substring of the user's message (the UI highlights it). The service drops quotes
    # that don't appear verbatim — semantic validation the schema alone can't express.
    quote: str | None = None


class Action(BaseModel):
    text: str
    note: str | None = None
    phone: str | None = None  # a hotline, shown large with a tel: button


class Citation(BaseModel):
    title: str
    source: str  # e.g. "ธปท.", "ตำรวจไซเบอร์"
    url: str


class Verdict(BaseModel):
    scam_type: ScamType
    risk_level: RiskLevel
    summary: str
    red_flags: list[RedFlag] = Field(default_factory=list)
    recommended_actions: list[Action] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)  # filled by code from the trail

    @field_validator("red_flags", "recommended_actions", mode="before")
    @classmethod
    def _wrap_strings(cls, v):
        # Small models often return ["..."] instead of [{"text": "..."}] — accept both.
        if isinstance(v, list):
            return [{"text": x} if isinstance(x, str) else x for x in v]
        return v

    @model_validator(mode="after")
    def _type_matches_risk(self):
        # A genuine message can't be risky, and a named scam can't be low risk. Raising here
        # sends the model back through the repair loop instead of shipping a contradiction.
        if self.scam_type is ScamType.legit and self.risk_level in (RiskLevel.medium, RiskLevel.high):
            raise ValueError("scam_type 'legit' requires risk_level 'low' or 'unknown'")
        if self.scam_type is not ScamType.legit and self.risk_level is RiskLevel.low:
            raise ValueError(
                f"scam_type '{self.scam_type.value}' is a scam, so risk_level must be medium or high"
                " (use 'legit' if the message is genuine)"
            )
        if self.risk_level in (RiskLevel.medium, RiskLevel.high) and not self.red_flags:
            raise ValueError(
                "risk_level medium/high needs at least one concrete red flag;"
                " if there is none, the message is legit with risk_level low"
            )
        return self


class ScanRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    channel: Channel | None = None


class ExtractTextRequest(BaseModel):
    # data:image/(png|jpeg|webp);base64,... — the frontend downsizes screenshots before sending.
    image: str = Field(min_length=32, max_length=7_000_000)


class ExtractTextResponse(BaseModel):
    text: str  # may be "" when the image has no readable text
