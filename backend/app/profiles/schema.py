from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    name: str
    description: str
    is_write_operation: bool = False
    requires_authorization: bool = False


class BehavioralContract(BaseModel):
    principles: List[str] = Field(default_factory=list)
    prohibited_actions: List[str] = Field(default_factory=list)
    escalation_path: Optional[str] = None


try:
    from nat.data_models.agent import AgentBaseConfig
except ImportError:
    AgentBaseConfig = None


class AgentProfileSchema(BaseModel):
    name: str
    display_name: str
    version: str = "1.0.0"
    role: str
    description: str
    ethos_reference: str = "ETHOS.md"
    max_execution_timeout_ms: int = 5000
    allowed_tools: List[str] = Field(default_factory=list)
    behavioral_contract: BehavioralContract = Field(default_factory=BehavioralContract)
    required_context: List[str] = Field(default_factory=list)
    routing_triggers: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    raw_yaml: Optional[str] = None

    def to_nat_agent_config(self, llm_name: str = "gemini-2.5-flash") -> Optional[Any]:
        if AgentBaseConfig is None:
            return None
        return AgentBaseConfig(
            name=self.name,
            description=f"[{self.role}] {self.description}",
            llm_name=llm_name,
            verbose=False,
        )

