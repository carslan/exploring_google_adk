from typing import Any, Optional

from google.adk.tools import BaseTool, ToolContext
from google.genai import types
from pydantic import BaseModel, Field

from src.tools.transaction_tool import Transaction


class AnomalyToolSchema(BaseModel):
    transactions: list[Transaction] = Field(description="List of the transactions to examine", default_factory=list)


class Anomaly(BaseModel):
    txn_id: str = Field(description="transaction id")
    is_anomaly: bool = Field(description="whether this transaction is anomaly")
    score: float = Field(description="the score of the anomaly")
    reason: str = Field(description="the reason the transaction is anomaly")


class AnomalyToolResponse(BaseModel):
    status: str = Field(description="success | error")
    results: list[Anomaly] = Field(description="list of anomaly results", default_factory=list)


class AnomalyTool(BaseTool):
    def __init__(self):
        self.name = "DetectAnomalyTool"
        self.description = "Detects anomalies by using the transactions"

        self.function_declaration = types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters_json_schema=AnomalyToolSchema,
            response_json_schema=AnomalyToolResponse
        )

        super().__init__(name=self.name, description=self.description)

    def _get_declaration(self) -> Optional[types.FunctionDeclaration]:
        return self.function_declaration

    async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
        some = "assignment"
        print()
        return [
            {
                "status": "success",
                "results": [
                    {
                        "txn_id": "TX1002",
                        "is_anomaly": True,
                        "score": 0.92,
                        "reason": "Amount exceeds daily threshold of 5000 USD"
                    }
                ]
            }
        ]
