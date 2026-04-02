from pydantic import BaseModel, ConfigDict, Field


class SimulationTriggerRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"scenario": "afternoon_thunderstorm", "time_compression": 10}
        }
    )

    scenario: str
    time_compression: int = Field(default=10, ge=1, le=100)


class SimulationResetResponse(BaseModel):
    status: str
    detail: str
