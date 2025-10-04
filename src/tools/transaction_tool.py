from typing import Any, Optional

from google.adk.tools import BaseTool, ToolContext
from google.genai import types
from pydantic import BaseModel, Field


class TransactionToolSchema(BaseModel):
    date: str = Field(description="date of the transaction")
    account_id: str = Field(description="name of the account")


class Transaction(BaseModel):
    txn_id: str = Field(description="Transaction ID")
    amount: float = Field(description="Transaction amount")
    currency: str = Field(description="currency code")
    timestamp: str = Field(description="iso datetime, when transaction occurred")
    account_id: str = Field(description="linked account")


class TransactionTool(BaseTool):
    """A tool that wraps a user-defined Python function."""

    def __init__(self):
        self.name: str = "TransactionTool"
        self.description: str = "A tool to find transactions by using a date and an account id."

        self.function_declaration = types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters_json_schema=TransactionToolSchema,
            response_json_schema=Transaction
        )

        super().__init__(name=self.name, description=self.description)

    def _get_declaration(self) -> Optional[types.FunctionDeclaration]:
        return self.function_declaration

    async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
        some = "assignment"
        print()
        return [
            {
                "txn_id": "TX1001",
                "amount": 2500.75,
                "currency": "USD",
                "timestamp": "2025-10-02T14:21Z",
                "account_id": "ACC-001"
            },
            {
                "txn_id": "TX1002",
                "amount": 9000.00,
                "currency": "USD",
                "timestamp": "2025-10-02T17:45Z",
                "account_id": "ACC-001"
            }
        ]
